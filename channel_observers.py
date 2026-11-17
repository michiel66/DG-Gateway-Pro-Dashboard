"""Optional multi-channel RX/TX observer pool for DG Gateway Pro.

One EXTRA muted TeamSpeak viewer is required per occupied channel to detect
voice activity with the normal TS3 protocol when ServerQuery -voice is not
authorised. Never create these clients silently: the user explicitly enables
the mode, and the server must permit it. Each monitor consumes a normal
TeamSpeak slot, and each actual channel connection is visible to admins.

PCM samples are discarded in the same patched WebSpeak3 connector as the
main dashboard. No audio output, recording, microphone, PTT or chat commands.
There is a hard safety cap and a cooldown for failed channel joins.
"""
from __future__ import annotations

import threading
import time
from direct_client import DirectViewer

MAX_OBSERVERS = 8
CONNECT_INTERVAL_SEC = 5
JOIN_TIMEOUT_SEC = 25
FAILED_RETRY_SEC = 180


class ChannelObserver:
    def __init__(self, pool, channel_id: int):
        self.pool = pool
        self.channel_id = channel_id
        self.viewer = DirectViewer(self, identity_scope=f"channel-{channel_id}")
        self.started = time.monotonic()
        self.own_id = 0
        self.join_requested = False
        self.join_started = 0.0
        self.ready = False
        self.failed = False
        self.error = ""
        self.talking: set[str] = set()

    def start(self):
        # Main and observers are always visibly identified, not impersonating users.
        self.viewer.start(f"C{self.channel_id}"[:16])

    def stop(self):
        self.viewer.stop()

    def handle_client_event(self, viewer, event):
        if viewer is not self.viewer or self.pool.stopping.is_set():
            return
        kind = event.get("type")
        move_to = 0
        changed = False
        with self.pool.lock:
            if self.pool.observers.get(self.channel_id) is not self:
                return
            if kind == "channels":
                self.own_id = int(event.get("own_client_id") or 0)
                own_channel = 0
                for person in event.get("clients") or []:
                    if isinstance(person, dict) and int(person.get("id") or 0) == self.own_id:
                        own_channel = int(person.get("channel") or 0)
                        break
                if own_channel == self.channel_id:
                    if not self.ready:
                        self.ready = True
                        changed = True
                    self.error = ""
                elif own_channel and not self.join_requested:
                    self.join_requested = True
                    self.join_started = time.monotonic()
                    move_to = self.channel_id
            elif kind == "talkers" and self.ready:
                active = {
                    str(uid) for uid in (event.get("clients") or [])[:250]
                    if type(uid) is int and uid > 0 and uid != self.own_id
                }
                if active != self.talking:
                    self.talking = active
                    changed = True
            elif kind in {"error", "disconnected"}:
                self.failed = True
                self.ready = False
                self.talking.clear()
                self.error = str(event.get("message") or event.get("reason")
                                 or "Observer kon kanaal niet openen.")[:160]
                changed = True

        if move_to:
            try:
                self.viewer.send(f"switch {move_to}")
            except (RuntimeError, ValueError) as exc:
                with self.pool.lock:
                    self.failed = True
                    self.error = str(exc)[:160]
        if changed:
            self.pool.notify()


class ChannelObservers:
    def __init__(self, state):
        self.state = state
        self.lock = threading.RLock()
        self.stopping = threading.Event()
        self.thread = None
        self.observers: dict[int, ChannelObserver] = {}
        self.fail_until: dict[int, float] = {}
        self.fail_messages: dict[int, str] = {}
        self.last_start = 0.0
        self.enabled = False
        self.limit = 4

    def configure(self, enabled: bool, limit: int = 4):
        if limit < 1 or limit > MAX_OBSERVERS:
            raise ValueError(f"Kies maximaal {MAX_OBSERVERS} extra kanaalbewakers.")
        self.stop()
        if not enabled:
            return
        self.stopping = threading.Event()
        with self.lock:
            self.enabled = True
            self.limit = limit
            self.last_start = 0.0
            self.fail_until = {}
            self.fail_messages = {}
        self.thread = threading.Thread(
            target=self._run, args=(self.stopping,),
            daemon=True, name="dg-channel-observers"
        )
        self.thread.start()

    def stop(self):
        self.stopping.set()
        with self.lock:
            viewers = list(self.observers.values())
            self.observers.clear()
            self.enabled = False
        for observer in viewers:
            observer.stop()
        # Thread exits via event; do not block the GUI / connected client.

    def _targets(self):
        # Collect a FULL snapshot of which visible channels contain real people.
        # Avoid observers in empty channels and the selected channel of the main client.
        with self.state.lock:
            if self.state.mode != "client" or not self.state.connected:
                return [], 0
            # When the authorised server Query provides full voice data,
            # do not consume unnecessary TeamSpeak voice-client slots.
            if (self.state.global_monitor_active and
                    time.time() - self.state.global_monitor_updated_at < 8):
                return [], self.state.client_channel
            own_channel = self.state.client_channel
            channels = {int(ch["id"]) for ch in self.state.channels}
            occupancy = {}
            for person in self.state.users:
                channel = int(person.get("channel_id") or 0)
                if channel in channels and channel != own_channel:
                    occupancy[channel] = occupancy.get(channel, 0) + 1
        # Stable priority: most people first, then lowest channel number.
        return sorted(occupancy, key=lambda cid: (-occupancy[cid], cid)), own_channel

    def _run(self, stop):
        while not stop.is_set():
            targets, own = self._targets()
            desired = set(targets[:self.limit])
            to_stop = []
            to_start = None
            now = time.monotonic()
            with self.lock:
                if not self.enabled:
                    break
                for cid, observer in list(self.observers.items()):
                    expired = (not observer.ready and now - observer.started > JOIN_TIMEOUT_SEC)
                    if cid not in desired or observer.failed or expired or cid == own:
                        if observer.failed or expired:
                            self.fail_until[cid] = now + FAILED_RETRY_SEC
                            self.fail_messages[cid] = observer.error or "Kan kanaal niet betreden."
                        self.observers.pop(cid, None)
                        to_stop.append(observer)
                if now - self.last_start >= CONNECT_INTERVAL_SEC:
                    for cid in targets[:self.limit]:
                        if cid not in self.observers and now >= self.fail_until.get(cid, 0):
                            to_start = ChannelObserver(self, cid)
                            self.observers[cid] = to_start
                            self.last_start = now
                            break

            for observer in to_stop:
                observer.stop()
            if to_start:
                try:
                    to_start.start()
                except (RuntimeError, OSError, ValueError) as exc:
                    with self.lock:
                        self.observers.pop(to_start.channel_id, None)
                        self.fail_until[to_start.channel_id] = now + FAILED_RETRY_SEC
                        self.fail_messages[to_start.channel_id] = str(exc)[:160]
                    to_start.stop()
            if to_stop or to_start:
                self.notify()
            stop.wait(1.0)

    def collect(self):
        with self.lock:
            ready = {cid for cid, obs in self.observers.items() if obs.ready}
            talking = {
                uid for obs in self.observers.values() if obs.ready
                for uid in obs.talking
            }
            status = {
                "enabled": self.enabled,
                "active_channels": len(ready),
                "channels": sorted(ready),
                "limit": self.limit,
                "failed_channels": sorted(self.fail_messages),
                "error": next(iter(self.fail_messages.values()), ""),
            }
        return talking, status

    def notify(self):
        # Do not hold pool.lock when acquiring state.lock: state->pool lock
        # order is used in snapshot and event updates.
        self.state.observer_updated(self)
