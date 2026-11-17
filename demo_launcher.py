"""DG Gateway Pro — offline demo launcher.

Opens ONLY static local files on 127.0.0.1. Does not load TeamSpeak,
open a microphone, poll an API, or simulate a real connection.
"""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
import threading


def demo_directory():
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)) / "demo"


class QuietHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(demo_directory()), **kwargs)

    def log_message(self, format, *args):
        pass

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        super().end_headers()


def run():
    root = demo_directory()
    if not (root / "index.html").exists():
        raise RuntimeError("Demo-HTML ontbreekt. Gebruik de complete ZIP/EXE.")
    server = ThreadingHTTPServer(("127.0.0.1", 0), QuietHandler)
    thread = threading.Thread(target=server.serve_forever, name="dg-demo-local", daemon=True)
    thread.start()
    try:
        import webview
        webview.create_window(
            "DG Gateway Pro — KAART DEMO (geen TeamSpeak)",
            f"http://127.0.0.1:{server.server_address[1]}/index.html",
            width=1600, height=900, min_size=(900, 600),
            resizable=True, fullscreen=True,
            background_color="#020d1c",
        )
        webview.start(debug=False)
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    run()
