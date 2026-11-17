"""Unit tests: valid region labels, TS3 parsing, actual query protocol and safe pairing."""
import socketserver
import tempfile
from pathlib import Path
import threading
import unittest

import app


class DGTests(unittest.TestCase):
    def test_all_regions(self):
        self.assertEqual(len(app.REGIONS), 12)
        for code in app.REGIONS:
            self.assertEqual(app.region_for(f"DG-{code} Iemand"), code)
            self.assertEqual(app.region_for(f"dg-{code} Michiel"), code)
        self.assertEqual(app.region_for("DG-103 Michiel"), 103)
        for s in ("Michiel", "TG-103 Michiel", "DG-999 Ruud", "DG-9999 Iemand", "DG-1034 Test"):
            self.assertEqual(app.region_for(s), 999)

    def test_query_escaping(self):
        samples = ["DG-103 Michiel", "test|plus=waardes", "a/b", r"a\b", "Hallo\nregel"]
        for raw in samples:
            self.assertEqual(app.ts_unescape(app.ts_escape(raw)), raw)
        self.assertEqual(app.ts_parse(r"clid=3 cid=1 client_nickname=DG-103\sMichiel client_type=0")[0]["client_nickname"], "DG-103 Michiel")
        self.assertEqual(len(app.ts_parse("clid=1 cid=1|clid=2 cid=3")), 2)

    def test_real_data_not_fabricated(self):
        dashboard=app.DashboardState()
        demo=dashboard.snapshot()
        self.assertEqual(demo["mode"], "demo")
        self.assertTrue(demo["demo"])
        self.assertEqual(demo["all_users_count"], 18)
        self.assertTrue(demo["speaker_data"])
        dashboard.set_mode("query")
        state=dashboard.snapshot()
        self.assertFalse(state["connected"])
        self.assertFalse(state["speaker_data"])
        self.assertEqual(state["heard"], [])
        self.assertEqual(state["all_users_count"], 0)

    def test_android_telemetry_and_last_heard(self):
        dashboard=app.DashboardState()
        dashboard.set_mode("android")
        dashboard.ingest_android({
            "users": [{"id": "42", "name": "DG-103 Michiel", "channel_id": 7, "speaking": True}],
            "channels": [{"id": 7, "name": "Radio"}]
        })
        live=dashboard.snapshot()
        self.assertTrue(live["connected"])
        self.assertTrue(live["speaker_data"])
        self.assertEqual(live["active_users"][0]["region"], 103)
        self.assertTrue(next(r for r in live["groups"] if r["code"] == 103)["active"])
        dashboard.ingest_android({
            "users": [{"id": "42", "name": "DG-103 Michiel", "channel_id": 7, "speaking": False}],
            "channels": [{"id": 7, "name": "Radio"}]
        })
        ended=dashboard.snapshot()
        self.assertEqual(len(ended["heard"]), 1)
        self.assertEqual(ended["heard"][0]["name"], "DG-103 Michiel")
        self.assertEqual(ended["active_users"], [])

    def test_tls_certificate_has_fingerprint(self):
        from cryptography import x509
        from cryptography.hazmat.primitives import serialization
        import hashlib
        with tempfile.TemporaryDirectory() as folder:
            cert_path,key_path,fingerprint=app.make_tls_certificate(Path(folder))
            self.assertTrue(cert_path.exists())
            self.assertTrue(key_path.exists())
            cert=x509.load_pem_x509_certificate(cert_path.read_bytes())
            der=cert.public_bytes(serialization.Encoding.DER)
            self.assertEqual(hashlib.sha256(der).hexdigest(),fingerprint)

    def test_query_connection_with_mock_server(self):
        class FakeServer(socketserver.StreamRequestHandler):
            def handle(self):
                self.wfile.write(b"TS3\nWelcome to the TeamSpeak 3 ServerQuery interface\n")
                self.wfile.flush()
                while True:
                    raw=self.rfile.readline()
                    if not raw:
                        return
                    cmd=raw.decode("utf-8").strip()
                    if cmd.startswith("login "):
                        self.wfile.write(b"error id=0 msg=ok\n")
                    elif cmd.startswith("use port="):
                        self.wfile.write(b"error id=0 msg=ok\n")
                    elif cmd == "channellist":
                        self.wfile.write(b"cid=7 channel_name=Radio\sKanaal|cid=8 channel_name=Algemeen\nerror id=0 msg=ok\n")
                    elif cmd == "clientlist -voice":
                        self.wfile.write(b"clid=5 cid=7 client_nickname=DG-103\sMichiel client_type=0|clid=6 cid=7 client_nickname=Query client_type=1\nerror id=0 msg=ok\n")
                    else:
                        self.wfile.write(b"error id=256 msg=command\snot\sfound\n")
                    self.wfile.flush()
        class Server(socketserver.ThreadingTCPServer):
            allow_reuse_address=True

        with Server(("127.0.0.1", 0), FakeServer) as server:
            threading.Thread(target=server.serve_forever,daemon=True).start()
            result=app.ts_query("127.0.0.1", server.server_address[1], 9987, "viewer", "test")
            self.assertEqual(result["channels"][0]["channel_name"], "Radio Kanaal")
            self.assertEqual(result["users"][0]["client_nickname"], "DG-103 Michiel")
            self.assertEqual(result["users"][1]["client_type"], "1")
            server.shutdown()


if __name__ == "__main__":
    unittest.main()
