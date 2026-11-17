"""A true TeamSpeak 3 viewer connection using the PINNED WebSpeak3 native connector.

No installed TeamSpeak 3 client, ServerQuery credentials, audio playback device,
microphone, or PTT. Incoming audio is consumed only inside the Rust connector
for real talker status, never sent to a sound device or the dashboard.
The connector is pinned to WebSpeak3 commit c2b52b3 (MIT).
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
import time

DEFAULT_SERVER = "heerlen.mijnts3.nl"
IDENTITY_FILE = "dashboard-identity.json"
CALLSIGN_RE = re.compile(r"^[^\x00-\x1f\x7f]{1,16}$")


def display_nickname(user_name: str) -> str:
    """Always identify the view-only client as such; cannot impersonate a DG member."""
    raw = str(user_name or "")
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in raw):
        raise ValueError("Gebruikersnaam bevat ongeldige tekens.")
    name = " ".join(raw.strip().split())
    if not CALLSIGN_RE.fullmatch(name):
        raise ValueError("Vul een gebruikersnaam van 1 tot 16 tekens in.")
    if any(c in name for c in "\\\n\r"):
        raise ValueError("Ongeldige gebruikersnaam.")
    return "DashboardView/" + name


def connector_path() -> Path:
    binary = "ts-connector.exe" if os.name == "nt" else "ts-connector"
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    choices = [root / binary, Path(sys.executable).resolve().parent / binary]
    return next((c for c in choices if c.is_file()), choices[0])


def identity_path() -> Path:
    """App-private profile, not a GitHub secret or any server-side credential."""
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    else:
        base = Path.home() / ".local" / "share"
    return base / "DG-Gateway-Pro-Dashboard" / IDENTITY_FILE


def load_identity() -> str:
    try:
        value = json.loads(identity_path().read_text(encoding="utf-8"))
        token = value.get("identity", "")
        return token if isinstance(token, str) and len(token) < 20000 else ""
    except (OSError, ValueError, TypeError):
        return ""


def store_identity(token: str):
    if not isinstance(token, str) or not token or len(token) > 20000:
        return
    p = identity_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    temp = p.with_suffix(".tmp")
    temp.write_text(json.dumps({"identity": token}), encoding="utf-8")
    try:
        temp.chmod(0o600)
    except OSError:
        pass
    temp.replace(p)


class DirectViewer:
    """Owns one muted voice-protocol connection, never any microphone/speaker."""

    def __init__(self, state, server: str = DEFAULT_SERVER):
        self.state = state
        self.server = server
        self.stopping = threading.Event()
        self.process = None
        self.write_lock = threading.Lock()
        self.thread = None

    def start(self, nickname: str):
        nickname = display_nickname(nickname)
        exe = connector_path()
        if not exe.is_file():
            raise RuntimeError("TeamSpeak-viewerconnector ontbreekt in deze Windows-build.")
        self.thread = threading.Thread(target=self._run, args=(exe, nickname),
                                       daemon=True, name="dg-ts3-viewer")
        self.thread.start()

    def send(self, command: str):
        """Only view-only commands are allowed: switch channel or disconnect."""
        if command != "disconnect" and not re.fullmatch(r"switch [1-9]\d{0,18}", command):
            raise ValueError("Deze kijkverbinding accepteert geen zenden of PTT-opdrachten.")
        with self.write_lock:
            proc = self.process
            if proc is None or proc.poll() is not None or proc.stdin is None:
                raise RuntimeError("TeamSpeak is niet verbonden.")
            try:
                proc.stdin.write(command + "\n")
                proc.stdin.flush()
            except (OSError, ValueError, BrokenPipeError) as exc:
                raise RuntimeError("TeamSpeak-verbinding is gesloten.") from exc

    def stop(self):
        self.stopping.set()
        with self.write_lock:
            proc = self.process
        if proc and proc.poll() is None:
            try:
                self.send("disconnect")
            except (RuntimeError, OSError):
                pass
            threading.Thread(target=self._kill_after_timeout,
                             args=(proc,), daemon=True).start()

    def _kill_after_timeout(self, proc):
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            try:
                proc.kill()
            except OSError:
                pass

    def _run(self, exe: Path, nickname: str):
        env = os.environ.copy()
        identity = load_identity()
        if identity:
            env["TS_IDENTITY"] = identity
        opts = {
            "args": [str(exe), "--address", self.server, "--nickname", nickname],
            "stdin": subprocess.PIPE, "stdout": subprocess.PIPE, "stderr": subprocess.DEVNULL,
            "text": True, "encoding": "utf-8", "errors": "replace", "bufsize": 1, "env": env,
        }
        if os.name == "nt":
            opts["creationflags"] = subprocess.CREATE_NO_WINDOW
        try:
            with subprocess.Popen(**opts) as proc:
                with self.write_lock:
                    self.process = proc
                for line in proc.stdout:
                    if self.stopping.is_set():
                        break
                    if len(line) > 2_000_000:
                        continue
                    try:
                        event = json.loads(line)
                    except (ValueError, TypeError):
                        continue
                    if not isinstance(event, dict):
                        continue
                    if event.get("type") == "connected":
                        # Native engine sends the initial identity; persist on disk for TS rights.
                        store_identity(event.get("identity", ""))
                        # Force a muted TS3 identity in addition to not opening a mic.
                        # Do not mute output in TS protocol: incoming packets carry
                        # speaking activity, but PCM is discarded inside Rust.
                        with self.write_lock:
                            if proc.stdin and proc.poll() is None:
                                proc.stdin.write("muteinput 1\n")
                                proc.stdin.flush()
                    if event.get("type") == "audioOut":
                        # Defensive: even when running a non-patched connector, never
                        # forward any audio data to the dashboard or a sound device.
                        continue
                    self.state.handle_client_event(self, event)
                if proc.poll() is None:
                    try:
                        proc.terminate()
                        proc.wait(timeout=2)
                    except (OSError, subprocess.TimeoutExpired):
                        proc.kill()
        except (OSError, RuntimeError) as exc:
            if not self.stopping.is_set():
                self.state.handle_client_event(self, {
                    "type": "error", "message": "Kan TeamSpeak-viewer niet starten: " + str(exc),
                })
        finally:
            with self.write_lock:
                self.process = None
            if not self.stopping.is_set():
                self.state.handle_client_event(self, {
                    "type": "disconnected", "reason": "De TeamSpeak-verbinding is gestopt.",
                })
