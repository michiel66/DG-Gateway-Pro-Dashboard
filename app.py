"""DG Gateway Pro Windows dashboard. No audio, no microphone, no TeamSpeak voice client.

The standalone monitor uses optional authorised TeamSpeak 3 ServerQuery (read-only).
The TLS pairing receiver is ready for a FUTURE Android companion; Android 2.0.2
does NOT implement it yet. No paired status is simulated.
"""
from __future__ import annotations

import base64
from collections import deque
from datetime import datetime, timedelta, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import ipaddress
import json
import os
from pathlib import Path
import re
import secrets
import socket
import ssl
import sys
import tempfile
import threading
import time
from direct_client import DirectViewer, display_nickname
from urllib.parse import urlparse, parse_qs


SERVER = "heerlen.mijnts3.nl"
APP_TITLE = "DG Gateway Pro — Windows Dashboard"
REGIONS = {
    100: "Noord-Holland", 101: "Utrecht", 102: "Zeeland",
    103: "Zuid-Holland", 104: "Noord-Brabant", 105: "Limburg",
    106: "Gelderland", 107: "Overijssel", 108: "Drenthe",
    109: "Groningen", 110: "Friesland", 111: "Flevoland",
}
LABEL_RE = re.compile(r"^DG-(\d{3})(?:\s+|$)", re.I)
MAX_JSON = 65536
HERE = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
STATIC = HERE / "ui"


def region_for(name: str) -> int:
    m = LABEL_RE.match(name.strip())
    if m:
        num = int(m.group(1))
        if num in REGIONS:
            return num
    return 999


def clean_text(value, maxlen=100) -> str:
    return re.sub(r"[\x00-\x1f\x7f]", " ", str(value or ""))[:maxlen].strip()


def ts_escape(s: str) -> str:
    """ServerQuery protocol escaping; credentials are never printed or logged."""
    return (str(s).replace("\\", "\\\\").replace("/", "\\/")
            .replace(" ", "\\s").replace("|", "\\p")
            .replace("\n", "\\n").replace("\r", "\\r")
            .replace("\t", "\\t"))


def ts_unescape(s: str) -> str:
    table = {"s": " ", "p": "|", "/": "/", "\\": "\\", "n": "\n", "r": "\r", "t": "\t"}
    return re.sub(r"\\(.)", lambda m: table.get(m.group(1), m.group(1)), s)


def ts_parse(line: str) -> list[dict]:
    output = []
    for segment in line.strip().split("|"):
        if not segment.strip():
            continue
        entry = {}
        for atom in segment.split(" "):
            if "=" not in atom:
                continue
            k, v = atom.split("=", 1)
            entry[k] = ts_unescape(v)
        output.append(entry)
    return output


class QueryError(Exception):
    pass


def query_voice_status(rows: list[dict]) -> tuple[set[str], bool]:
    """True talking flags from TS3 ServerQuery, never mic-enabled or 'is_talker'.

    Some servers omit this flag or permission-scope the result. In that case
    return available=False instead of showing made-up network-wide TX.
    """
    real = [r for r in rows if r.get("client_type") == "0"
            and not str(r.get("client_nickname", "")).lower().startswith("dashboardview/")]
    available = bool(real) and all("client_flag_talking" in row for row in real)
    talkers = {str(row["clid"]) for row in real if row.get("client_flag_talking") == "1"
               and "clid" in row} if available else set()
    return talkers, available


def ts_query(host: str, query_port: int, voice_port: int, login: str, password: str,
             include_channels: bool = True) -> dict:
    """Read users/voice flags from server; no audio transferred or microphone opened.

    client_flag_talking from clientlist -voice can represent speakers in all
    channels the query account is allowed to inspect. Never infer actual
    talking from client_input_muted or client_is_talker.
    """
    with socket.create_connection((host, query_port), timeout=8.0) as sock:
        sock.settimeout(8.0)
        stream = sock.makefile("rwb", buffering=0)
        def ask(command: str) -> list[dict]:
            stream.write((command + "\n").encode("utf-8"))
            lines = []
            for _ in range(500):
                raw = stream.readline()
                if not raw:
                    raise QueryError("ServerQuery heeft de verbinding gesloten.")
                line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
                if line.startswith("error "):
                    item = ts_parse(line)[0]
                    if item.get("id", "0") != "0":
                        raise QueryError("ServerQuery: " + item.get("msg", "toegang geweigerd"))
                    return [part for ln in lines for part in ts_parse(ln)]
                if line.startswith("TS3") or line.startswith("Welcome to the TeamSpeak"):
                    continue
                if line and not line.startswith("error "):
                    lines.append(line)
            raise QueryError("Ongeldig antwoord van de ServerQuery-server.")

        if login and password:
            ask("login " + ts_escape(login) + " " + ts_escape(password))
        # ServerQuery cannot represent a normal logged-in TeamSpeak voice client.
        ask("use port=" + str(voice_port))
        # The all-channel voice monitor needs only clientlist. Don't require
        # unrelated channellist permissions when using a restricted read account.
        chans = ask("channellist") if include_channels else []
        users = ask("clientlist -voice")
        return {"channels": chans, "users": users}


def demo_data() -> dict:
    people = [
        ("Michiel", 103, 1), ("Ruud", 103, 1), ("Nico", 103, 1),
        ("Marcel", 104, 2), ("Peter", 105, 2), ("Henk", 106, 3),
        ("Kees", 100, 1), ("Sandra", 101, 3), ("Theo", 102, 1),
        ("Arie", 107, 2), ("Jan", 108, 3), ("Wim", 109, 1),
        ("Ron", 110, 3), ("Bert", 111, 2), ("Patrick", 103, 1),
        ("Bas", 106, 3), ("Gerard", 105, 2), ("Gast", 999, 1),
    ]
    users = [
        {"id": str(i + 1), "name": f"DG-{code} {name}" if code != 999 else name,
         "channel_id": channel, "region": code, "speaking": i == 0}
        for i, (name, code, channel) in enumerate(people)
    ]
    now = datetime.now().astimezone()
    heard = [
        {"name": "DG-103 Michiel", "region": 103, "time": now.strftime("%H:%M:%S"), "duration": "00:12"},
        {"name": "DG-104 Marcel", "region": 104, "time": (now-timedelta(minutes=4)).strftime("%H:%M:%S"), "duration": "00:08"},
        {"name": "DG-106 Henk", "region": 106, "time": (now-timedelta(minutes=9)).strftime("%H:%M:%S"), "duration": "00:15"},
    ]
    return {
        "users": users,
        "channels": [
            {"id": 1, "name": "DG Gateway Gesprekken"},
            {"id": 2, "name": "Regio Netwerk"},
            {"id": 3, "name": "Algemeen"},
        ],
        "heard": heard, "speaker_data": True,
    }


class DashboardState:
    def __init__(self):
        self.lock = threading.RLock()
        self.mode = "demo"
        self.connected = False
        self.error = ""
        self.display_name = ""
        self.users = []
        self.channels = []
        self.heard = []
        self.speaker_data = False
        self.updated_at = 0.0
        self.channel_filter = 0
        self.query_thread = None
        self.query_stop = threading.Event()
        self.generation = 0
        self.pair_code = f"{secrets.randbelow(1000000):06d}"
        self.pair_token = None
        self.pair_created = time.monotonic()
        self.pair_attempts = {}
        self.paired_device = ""
        self.speaking_started = {}
        self.pair_host = ""
        self.pair_port = 0
        self.pair_fingerprint = ""
        self.pair_qr = ""
        self.pair_error = ""
        self.query_config = None
        self.client_viewer = None
        self.client_talking = set()
        self.client_own_id = 0
        self.client_channel = 0
        self.global_monitor_thread = None
        self.global_monitor_stop = threading.Event()
        self.global_monitor_epoch = 0
        self.global_monitor_config = None
        self.global_monitor_enabled = False
        self.global_monitor_active = False
        self.global_monitor_updated_at = 0.0
        self.global_monitor_error = ""
        self.global_talking = set()
        self.global_monitor_count = 0

    def stop_client(self):
        with self.lock:
            viewer = self.client_viewer
            self.client_viewer = None
        if viewer is not None:
            viewer.stop()

    def set_mode(self, mode: str):
        if mode not in {"demo", "query", "android", "client"}:
            raise ValueError("Onbekende verbindingsmethode.")
        self.stop_query()
        self.stop_global_monitor()
        self.stop_client()
        with self.lock:
            self.mode = mode
            self.users = []
            self.channels = []
            self.heard = []
            self.speaker_data = False
            self.updated_at = 0
            self.connected = False
            self.error = ""
            self.channel_filter = 0
            self.client_talking = set()
            self.client_own_id = 0
            self.client_channel = 0
            self.speaking_started = {}
            self.global_monitor_active = False
            self.global_monitor_enabled = False
            self.global_monitor_error = ""
            self.global_talking = set()

    def stop_global_monitor(self):
        self.global_monitor_stop.set()
        with self.lock:
            self.global_monitor_epoch += 1
            self.global_monitor_config = None
            self.global_monitor_active = False
            self.global_talking = set()
            self.global_monitor_updated_at = 0.0

    def _record_speakers_locked(self, talking_ids: set[str]):
        """Apply only real talking observations and record completed transmissions.

        Caller holds self.lock. IDs are source-scoped TS3 client IDs (not
        nicknames), and only clients actually visible in self.users count.
        """
        visible = {str(user["id"]): user for user in self.users}
        talking_ids = set(talking_ids) & visible.keys()
        old_ids = set(self.speaking_started)
        now = time.monotonic()
        stamp = datetime.now().astimezone().strftime("%H:%M:%S")
        for uid in old_ids - talking_ids:
            old = self.speaking_started.pop(uid, None)
            if old:
                name, started = old
                secs = max(0, int(now - started))
                self.heard.insert(0, {
                    "name": name, "region": region_for(name),
                    "time": stamp, "duration": f"{secs//60:02d}:{secs%60:02d}",
                })
        for uid in talking_ids - old_ids:
            self.speaking_started[uid] = (visible[uid]["name"], now)
        for user in self.users:
            user["speaking"] = str(user["id"]) in talking_ids
        self.heard = self.heard[:40]

    def stop_query(self):
        self.query_stop.set()
        with self.lock:
            self.query_config = None
            self.generation += 1

    def connect_query(self, payload: dict):
        self.stop_global_monitor()
        self.stop_client()
        host = clean_text(payload.get("host") or SERVER, 200)
        if not re.fullmatch(r"[a-zA-Z0-9.:_-]{1,200}", host):
            raise ValueError("Ongeldig serveradres.")
        query_port = int(payload.get("query_port") or 10011)
        voice_port = int(payload.get("voice_port") or 9987)
        if not (1 <= query_port <= 65535 and 1 <= voice_port <= 65535):
            raise ValueError("Ongeldige poort.")
        login = clean_text(payload.get("login"), 120)
        password = str(payload.get("password") or "")
        with self.lock:
            self.generation += 1
            gen = self.generation
            self.mode = "query"
            self.connected = False
            self.error = "Verbinden met ServerQuery..."
            self.users = []
            self.channels = []
            self.heard = []
            self.speaker_data = False
            self.display_name = clean_text(payload.get("display_name") or "", 40)
            self.query_config = (host, query_port, voice_port, login, password)
        self.query_stop.set()
        self.query_stop = threading.Event()
        stop = self.query_stop

        def loop():
            while not stop.is_set():
                try:
                    result = ts_query(*self.query_config) if self.query_config else None
                    if result is None:
                        return
                    users = []
                    for row in result["users"]:
                        if row.get("client_type") != "0":
                            continue
                        name = clean_text(row.get("client_nickname"), 90)
                        users.append({
                            "id": clean_text(row.get("clid"), 20),
                            "name": name,
                            "region": region_for(name),
                            "channel_id": int(row.get("cid") or 0),
                            "speaking": None,  # Filled only after valid -voice flags are verified.
                        })
                    channels = [
                        {"id": int(row.get("cid") or 0), "name": clean_text(row.get("channel_name"), 80)}
                        for row in result["channels"] if row.get("cid", "").isdigit()
                    ]
                    talking, valid_flags = query_voice_status(result["users"])
                    with self.lock:
                        if gen != self.generation or self.mode != "query":
                            return
                        self.users = users
                        self.channels = channels
                        self.speaker_data = valid_flags
                        if valid_flags:
                            self._record_speakers_locked(talking)
                        else:
                            self.speaking_started.clear()
                        self.connected = True
                        self.updated_at = time.time()
                        self.error = "" if valid_flags else "ServerQuery: deze server geeft geen spreekstatus (-voice) terug."

                except Exception as exc:
                    with self.lock:
                        if gen != self.generation:
                            return
                        self.connected = False
                        self.error = clean_text(exc, 200)
                stop.wait(2.0)

        self.query_thread = threading.Thread(target=loop, daemon=True, name="serverquery-reader")
        self.query_thread.start()



    def start_global_monitor(self, payload: dict):
        """Supplement normal TeamSpeak client with authorised server-wide voice flags.

        Try anonymous ServerQuery on the same Heerlen server first. The
        server's read-only permissions determine whether all channels can be
        monitored. Credentials are optional and held only in RAM.
        """
        enabled = payload.get("global_monitor", True) is not False
        port = int(payload.get("query_port") or 10011)
        voice_port = int(payload.get("voice_port") or 9987)
        if not (1 <= port <= 65535 and 1 <= voice_port <= 65535):
            raise ValueError("Ongeldige ServerQuery- of voicepoort.")
        login = clean_text(payload.get("login"), 100)
        password = str(payload.get("password") or "")
        if bool(login) != bool(password):
            raise ValueError("Vul zowel de ServerQuery-login als het wachtwoord in, of laat beide leeg.")
        self.stop_global_monitor()
        with self.lock:
            if self.mode != "client":
                raise ValueError("Serverbrede monitoring werkt in TeamSpeak direct.")
            epoch = self.global_monitor_epoch
            self.global_monitor_enabled = enabled
            self.global_monitor_error = (
                "Serverbrede RX/TX is uitgeschakeld." if not enabled
                else "Verbinding met ServerQuery wordt gecontroleerd..."
            )
            self.global_monitor_count = 0
            if not enabled:
                self._record_speakers_locked({str(uid) for uid in self.client_talking})
                return
            self.global_monitor_config = (SERVER, port, voice_port, login, password)
            stop = threading.Event()
            self.global_monitor_stop = stop

        def monitor():
            while not stop.is_set():
                try:
                    result = ts_query(SERVER, port, voice_port, login, password,
                                      include_channels=False)
                    talking, flag_available = query_voice_status(result["users"])
                    if not flag_available:
                        raise QueryError(
                            "ServerQuery -voice geeft geen client_flag_talking terug. "
                            "Vraag een leesaccount met toegang tot alle kanalen."
                        )
                    with self.lock:
                        if (self.mode != "client" or self.global_monitor_epoch != epoch
                                or not self.global_monitor_enabled):
                            return
                        self.global_monitor_active = True
                        self.global_monitor_updated_at = time.time()
                        self.global_monitor_count = sum(
                            1 for row in result["users"] if row.get("client_type") == "0"
                            and not str(row.get("client_nickname", "")).lower().startswith("dashboardview/")
                        )
                        self.global_talking = talking
                        self.global_monitor_error = ""
                        self._record_speakers_locked(talking)
                except (OSError, QueryError, ValueError, TimeoutError) as exc:
                    with self.lock:
                        if self.mode != "client" or self.global_monitor_epoch != epoch:
                            return
                        self.global_monitor_active = False
                        self.global_talking.clear()
                        self.global_monitor_error = (
                            "Geen toegang tot de serverbrede spreekstatus: "
                            + clean_text(exc, 180)
                            + " (alleen eigen kanaal blijft beschikbaar)"
                        )
                        self._record_speakers_locked({str(uid) for uid in self.client_talking})
                stop.wait(2.0 if self.global_monitor_active else 6.0)

        self.global_monitor_thread = threading.Thread(
            target=monitor, daemon=True, name="dg-server-wide-voice-flags"
        )
        self.global_monitor_thread.start()

    def connect_client(self, payload: dict):
        """A real, muted TS3 client; no TeamSpeak installation or ServerQuery password."""
        name = clean_text(payload.get("display_name"), 16)
        display_nickname(name)  # Validate before changing the existing state.
        port = int(payload.get("query_port") or 10011)
        voice_port = int(payload.get("voice_port") or 9987)
        if not (1 <= port <= 65535 and 1 <= voice_port <= 65535):
            raise ValueError("Ongeldige ServerQuery- of voicepoort.")
        if bool(clean_text(payload.get("login"))) != bool(str(payload.get("password") or "")):
            raise ValueError("Vul zowel de optionele lees-login als het wachtwoord in, of laat beide leeg.")
        viewer = DirectViewer(self, SERVER)
        # Confirm the native viewer exists BEFORE dropping any existing connection.
        if not viewer_available():
            raise ValueError("De TeamSpeak-connector ontbreekt. Download de nieuwste Windows-build.")
        self.set_mode("client")
        with self.lock:
            self.client_viewer = viewer
            self.display_name = name
            self.error = "TeamSpeak-verbinding wordt gestart..."
            self.query_config = None
        try:
            viewer.start(name)
            self.start_global_monitor(payload)
        except (RuntimeError, OSError, ValueError):
            viewer.stop()  # Never leak an active TS client if monitor setup fails.
            with self.lock:
                self.client_viewer = None
            raise

    def handle_client_event(self, viewer, event: dict):
        """Validated TeamSpeak connector events. No user-generated sample data."""
        with self.lock:
            if self.mode != "client" or self.client_viewer is not viewer:
                return
            kind = event.get("type")
            if kind == "connected":
                self.error = ""
                self.updated_at = time.time()
            elif kind == "channels":
                self.client_own_id = int(event.get("own_client_id") or 0)
                raw_clients = event.get("clients") or []
                self.client_channel = 0
                clients = []
                for client in raw_clients[:300]:
                    if not isinstance(client, dict):
                        continue
                    uid = int(client.get("id") or 0)
                    if uid == self.client_own_id:
                        self.client_channel = int(client.get("channel") or 0)
                        continue
                    if client.get("is_query"):
                        continue
                    nickname = clean_text(client.get("name"), 90)
                    # Other Windows viewers should not appear among ordinary DG-999 users.
                    if not nickname or nickname.lower().startswith("dashboardview/"):
                        continue
                    clients.append({
                        "id": str(uid), "name": nickname,
                        "region": region_for(nickname),
                        "channel_id": int(client.get("channel") or 0),
                        "speaking": str(uid) in (self.global_talking if self.global_monitor_active
                                                else {str(x) for x in self.client_talking}),
                    })
                self.users = clients
                self.channels = [
                    {"id": int(ch.get("id") or 0), "name": clean_text(ch.get("name"), 80)}
                    for ch in (event.get("channels") or [])[:300] if isinstance(ch, dict)
                ]
                self.connected = True
                self.speaker_data = True
                self._record_speakers_locked(
                    self.global_talking if self.global_monitor_active
                    else {str(uid) for uid in self.client_talking}
                )
                self.updated_at = time.time()
                self.error = ""
            elif kind == "talkers":
                # Direct TS client only knows actual speakers it can hear in
                # its channel; don't let that narrow status overwrite server-
                # wide flags when an authorised Query monitor is active.
                self.client_talking = {
                    int(uid) for uid in (event.get("clients") or [])[:300] if isinstance(uid, int)
                }
                self.client_talking.discard(self.client_own_id)
                if not self.global_monitor_active:
                    self._record_speakers_locked({str(uid) for uid in self.client_talking})
                self.updated_at = time.time()
            elif kind == "reconnecting":
                self.connected = False
                self.speaker_data = False
                self.error = "TeamSpeak herverbindt..."
            elif kind == "reconnected":
                self.error = ""
            elif kind == "disconnected":
                self.global_monitor_stop.set()
                self.global_monitor_epoch += 1
                self.global_monitor_enabled = False
                self.global_monitor_active = False
                self.global_talking.clear()
                self.connected = False
                self.speaker_data = False
                self.users = []
                self.channels = []
                self.client_talking = set()
                self.speaking_started = {}
                self.error = clean_text(event.get("reason") or "TeamSpeak is verbroken.", 160)
            elif kind == "error":
                self.error = clean_text(event.get("message") or "TeamSpeak-fout.", 170)

    def join_client_channel(self, cid: int):
        with self.lock:
            viewer = self.client_viewer
            allowed = self.mode == "client" and self.connected and cid in [c["id"] for c in self.channels]
        if not allowed or viewer is None:
            raise ValueError("Maak eerst verbinding en selecteer een geldig TeamSpeak-kanaal.")
        viewer.send("switch " + str(cid))


    def ingest_android(self, payload: dict):
        users = []
        talking = set()
        for person in (payload.get("users") or [])[:250]:
            if not isinstance(person, dict):
                continue
            name = clean_text(person.get("name"), 90)
            if not name:
                continue
            uid = clean_text(person.get("id") or name, 60)
            speaking = bool(person.get("speaking"))
            users.append({
                "id": uid, "name": name, "channel_id": int(person.get("channel_id") or 0),
                "region": region_for(name), "speaking": speaking,
            })
            if speaking:
                talking.add(uid)
        now = time.monotonic()
        now_iso = datetime.now().astimezone()
        with self.lock:
            for uid, (name, started) in list(self.speaking_started.items()):
                if uid not in talking:
                    dur = max(0, int(now-started))
                    self.heard.insert(0, {
                        "name": name, "region": region_for(name),
                        "time": now_iso.strftime("%H:%M:%S"), "duration": f"{dur//60:02d}:{dur%60:02d}",
                    })
                    self.speaking_started.pop(uid, None)
            for person in users:
                if person["id"] in talking and person["id"] not in self.speaking_started:
                    self.speaking_started[person["id"]] = (person["name"], now)
            self.heard = self.heard[:40]
            self.users = users
            self.channels = [
                {"id": int(ch.get("id") or 0), "name": clean_text(ch.get("name"), 80)}
                for ch in (payload.get("channels") or [])[:200] if isinstance(ch, dict)
            ]
            self.mode = "android"
            self.connected = True
            self.speaker_data = True
            self.updated_at = time.time()
            self.error = ""

    def snapshot(self) -> dict:
        with self.lock:
            mode = self.mode
            demo = demo_data() if mode == "demo" else None
            users = demo["users"] if demo else [dict(user) for user in self.users]
            channels = demo["channels"] if demo else list(self.channels)
            heard = demo["heard"] if demo else list(self.heard)
            talk_data = demo["speaker_data"] if demo else self.speaker_data
            monitor_live = (mode == "client" and self.global_monitor_active
                            and time.time() - self.global_monitor_updated_at < 8.0)
            if mode == "client" and not monitor_live:
                local = {str(uid) for uid in self.client_talking}
                for user in users:
                    user["speaking"] = str(user["id"]) in local

            selected = self.channel_filter
            shown = [u for u in users if selected == 0 or u.get("channel_id") == selected]
            groups = [{"code": num, "name": name, "count": sum(1 for p in users if p["region"] == num),
                       "active": talk_data and any(p["region"] == num and p.get("speaking") is True for p in users)}
                      for num, name in list(REGIONS.items()) + [(999, "Overige gebruikers")]]
            active = [u for u in users if u.get("speaking") is True] if talk_data else []
            info = {
                "mode": mode, "connected": mode == "demo" or self.connected,
                "demo": mode == "demo", "error": self.error, "server": SERVER,
                "users": shown, "all_users_count": len(users), "channels": channels,
                "selected_channel": self.client_channel if mode == "client" else selected,
                "groups": groups,
                "heard": heard if talk_data else [], "speaker_data": talk_data,
                "active_users": active, "updated_at": self.updated_at,
                "talk_scope": ("voorbeeld" if mode == "demo"
                               else "hele_server" if mode == "query" and talk_data
                               else "gedeeltelijk" if monitor_live and self.global_monitor_count < len(users)
                               else "hele_server" if monitor_live
                               else "eigen_kanaal" if mode == "client"
                               else "onbekend"),
                "monitor": {
                    "enabled": self.global_monitor_enabled if mode == "client" else False,
                    "live": monitor_live,
                    "query_users": self.global_monitor_count if monitor_live else 0,
                    "visible_users": len(users),
                    "error": self.global_monitor_error if mode == "client" else "",
                    "last_update": self.global_monitor_updated_at if monitor_live else 0,
                    "source": "ServerQuery -voice" if monitor_live else "TeamSpeak client",
                },
                "pair": {
                    "code": self.pair_code if time.monotonic() - self.pair_created < 300 and not self.pair_token else "",
                    "qr": self.pair_qr if not self.pair_token else "",
                    "host": self.pair_host, "port": self.pair_port,
                    "paired": bool(self.pair_token),
                    "device": self.paired_device, "error": self.pair_error,
                    "android_companion_ready": False,  # Android 2.0.2 has no pairing feature.
                },
                "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
            }
            return info


def viewer_available() -> bool:
    from direct_client import connector_path
    return connector_path().is_file()


STATE = DashboardState()


def read_json(handler: BaseHTTPRequestHandler):
    try:
        count = int(handler.headers.get("Content-Length") or 0)
    except ValueError:
        raise ValueError("Ongeldige berichtlengte.")
    if not (0 < count <= MAX_JSON):
        raise ValueError("Ongeldige of te grote gegevens.")
    obj = json.loads(handler.rfile.read(count).decode("utf-8"))
    if not isinstance(obj, dict):
        raise ValueError("JSON-object verwacht.")
    return obj


def json_reply(handler, code, data):
    payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("X-Content-Type-Options", "nosniff")
    handler.send_header("Content-Length", str(len(payload)))
    handler.end_headers()
    handler.wfile.write(payload)


class LocalHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        return

    def do_GET(self):
        p = urlparse(self.path).path
        if p in {"/api/status", "/api/snapshot"}:
            return json_reply(self, 200, STATE.snapshot())
        paths = {"/": "index.html", "/index.html": "index.html",
                 "/style.css": "style.css", "/app.js": "app.js"}
        if p not in paths:
            return json_reply(self, 404, {"error": "Niet gevonden"})
        path = STATIC / paths[p]
        try:
            body = path.read_bytes()
        except OSError:
            return json_reply(self, 500, {"error": "Ontbrekend dashboardbestand"})
        self.send_response(200)
        self.send_header("Content-Type", {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "text/javascript; charset=utf-8",
        }.get(path.suffix, "application/octet-stream"))
        self.send_header("Content-Security-Policy", "default-src 'self' data:; img-src 'self' data:; script-src 'self'; style-src 'self'; connect-src 'self'; object-src 'none'; frame-ancestors 'none'")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        origin = self.headers.get("Origin", "")
        if origin and not re.fullmatch(r"http://127\.0\.0\.1:\d+", origin):
            return json_reply(self, 403, {"error": "Alleen vanuit het lokale dashboard"})
        if self.headers.get("Content-Type", "").split(";")[0].strip() != "application/json":
            return json_reply(self, 415, {"error": "Alleen application/json"})
        try:
            data = read_json(self)
            p = urlparse(self.path).path
            if p == "/api/mode":
                STATE.set_mode(str(data.get("mode")))
            elif p == "/api/connect":
                STATE.connect_query(data)
            elif p == "/api/connect-client":
                STATE.connect_client(data)
            elif p == "/api/global-monitor":
                STATE.start_global_monitor(data)
            elif p == "/api/disconnect":
                STATE.set_mode("demo")
            elif p == "/api/channel":
                channel = int(data.get("id") or 0)
                if STATE.mode == "client":
                    STATE.join_client_channel(channel)
                else:
                    with STATE.lock:
                        if channel and channel not in [ch["id"] for ch in STATE.channels] and STATE.mode != "demo":
                            raise ValueError("Dit kanaal bestaat niet.")
                        STATE.channel_filter = channel
            else:
                return json_reply(self, 404, {"error": "Niet gevonden"})
            return json_reply(self, 200, {"ok": True})
        except (ValueError, TypeError, RuntimeError, json.JSONDecodeError) as exc:
            return json_reply(self, 400, {"error": clean_text(exc, 160)})


class LanHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        return

    def do_GET(self):
        if self.path != "/pair-info":
            return json_reply(self, 404, {"error": "Niet gevonden"})
        return json_reply(self, 200, {
            "product": "DG Gateway Pro Dashboard", "protocol": 1,
            "fingerprint_sha256": STATE.pair_fingerprint,
            "android_companion_ready": False,
        })

    def do_POST(self):
        if self.headers.get("Content-Type", "").split(";")[0].strip() != "application/json":
            return json_reply(self, 415, {"error": "Alleen application/json"})
        try:
            data = read_json(self)
        except (ValueError, json.JSONDecodeError) as exc:
            return json_reply(self, 400, {"error": clean_text(exc)})
        if self.path == "/pair":
            with STATE.lock:
                now = time.monotonic()
                ip = self.client_address[0]
                attempts = [t for t in STATE.pair_attempts.get(ip, []) if now-t < 300]
                if len(attempts) >= 5:
                    STATE.pair_attempts[ip] = attempts
                    return json_reply(self, 429, {"error": "Te veel pogingen"})
                attempts.append(now)
                STATE.pair_attempts[ip] = attempts
                if (STATE.pair_token is not None or now-STATE.pair_created > 300
                        or not secrets.compare_digest(str(data.get("code") or ""), STATE.pair_code)):
                    return json_reply(self, 403, {"error": "Koppelcode ongeldig of verlopen"})
                STATE.pair_token = secrets.token_urlsafe(32)
                STATE.paired_device = clean_text(data.get("device") or "Android", 50)
                STATE.mode = "android"
                STATE.connected = False  # Only true after actual authenticated telemetry arrives.
                STATE.speaker_data = False
                STATE.users = []
                STATE.channels = []
                return json_reply(self, 200, {"token": STATE.pair_token, "protocol": 1})
        if self.path == "/telemetry":
            value = self.headers.get("Authorization", "")
            with STATE.lock:
                token = STATE.pair_token
                valid = token is not None and secrets.compare_digest(value, "Bearer " + token)
            if not valid:
                return json_reply(self, 403, {"error": "Geen geldige koppeling"})
            try:
                STATE.ingest_android(data)
                return json_reply(self, 200, {"ok": True})
            except (ValueError, TypeError):
                return json_reply(self, 400, {"error": "Ongeldige telemetry"})
        return json_reply(self, 404, {"error": "Niet gevonden"})


def get_lan_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("192.0.2.1", 1))
            ip = s.getsockname()[0]
            if not ip.startswith("127."):
                return ip
    except OSError:
        pass
    try:
        ip = socket.gethostbyname(socket.gethostname())
        if ip and not ip.startswith("127."):
            return ip
    except OSError:
        pass
    return ""


def make_tls_certificate(dirpath: Path):
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import NameOID

    key = ec.generate_private_key(ec.SECP256R1())
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "DG Gateway Pro lokale koppeling")])
    now = datetime.now(timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject).issuer_name(subject).public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now-timedelta(minutes=2))
        .not_valid_after(now+timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .sign(key, hashes.SHA256())
    )
    cert_path = dirpath / "cert.pem"
    key_path = dirpath / "key.pem"
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(key.private_bytes(serialization.Encoding.PEM,
                                          serialization.PrivateFormat.PKCS8,
                                          serialization.NoEncryption()))
    fingerprint = hashlib.sha256(cert.public_bytes(serialization.Encoding.DER)).hexdigest()
    return cert_path, key_path, fingerprint


def start_https_pair_server():
    import qrcode

    lan_ip = get_lan_ip()
    if not lan_ip:
        STATE.pair_error = "Geen lokaal netwerkadres gevonden (controleer wifi)."
        return None, None, None
    temp = tempfile.TemporaryDirectory(prefix="dg_pair_")
    folder = Path(temp.name)
    try:
        cert, key, fingerprint = make_tls_certificate(folder)
        server = ThreadingHTTPServer(("0.0.0.0", 0), LanHandler)
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        ctx.load_cert_chain(str(cert), str(key))
        server.socket = ctx.wrap_socket(server.socket, server_side=True)
        port = server.server_address[1]
        STATE.pair_host = lan_ip
        STATE.pair_port = port
        STATE.pair_fingerprint = fingerprint
        # Android companion must PIN this SHA256 fingerprint. Do not accept arbitrary TLS certs.
        content = json.dumps({
            "app": "dg-gateway-pro", "protocol": 1,
            "url": f"https://{lan_ip}:{port}", "code": STATE.pair_code,
            "certificate_sha256": fingerprint,
        }, separators=(",", ":"))
        image = qrcode.make(content)
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        STATE.pair_qr = "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()
        threading.Thread(target=server.serve_forever, daemon=True, name="dg-https-pair").start()
        return server, temp, threading.Thread(target=lan_discovery, daemon=True, name="dg-discovery")
    except Exception as exc:
        STATE.pair_error = f"LAN-koppeling niet gestart: {clean_text(exc, 120)}"
        temp.cleanup()
        return None, None, None


def lan_discovery():
    """UDP discovery supports typing just six digits in a FUTURE Android update."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("0.0.0.0", 45913))
        sock.settimeout(2.0)
    except OSError:
        return
    with sock:
        while True:
            try:
                msg, addr = sock.recvfrom(128)
                if msg != b"DG_GATEWAY_DISCOVER_1":
                    continue
                reply = json.dumps({
                    "product": "DG Gateway Pro", "v": 1, "url": f"https://{STATE.pair_host}:{STATE.pair_port}",
                    "certificate_sha256": STATE.pair_fingerprint,
                }).encode()
                sock.sendto(reply, addr)
            except socket.timeout:
                continue
            except OSError:
                return


def run():
    local = ThreadingHTTPServer(("127.0.0.1", 0), LocalHandler)
    local_port = local.server_address[1]
    threading.Thread(target=local.serve_forever, daemon=True, name="dg-local-ui").start()
    pair, temp, discovery = start_https_pair_server()
    if discovery is not None:
        discovery.start()
    try:
        import webview
        class WindowControl:
            def toggle_fullscreen(self):
                """Native pywebview fullscreen toggle; Esc also closes dialogs in the UI."""
                webview.windows[0].toggle_fullscreen()
                return True

        webview.create_window(APP_TITLE, f"http://127.0.0.1:{local_port}",
                              js_api=WindowControl(), width=1600, height=900,
                              min_size=(850, 560), resizable=True, fullscreen=True,
                              background_color="#030b17")
        webview.start(debug=False)
    finally:
        STATE.stop_query()
        STATE.stop_global_monitor()
        STATE.stop_client()
        local.shutdown()
        if pair:
            pair.shutdown()
        if temp:
            temp.cleanup()


if __name__ == "__main__":
    run()
