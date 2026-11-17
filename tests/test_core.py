"""Unit tests: valid region labels, TS3 parsing, actual query protocol and safe pairing."""
import socketserver
import tempfile
from pathlib import Path
import threading
import time
import unittest
from unittest.mock import patch

import app
from channel_observers import ChannelObserver, ChannelObservers, MAX_OBSERVERS
from direct_client import identity_path


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

    def test_serverquery_voice_flags_all_channels(self):
        rows = [
            {"clid": "5", "cid": "7", "client_nickname": "DG-103 Michiel",
             "client_type": "0", "client_flag_talking": "0"},
            {"clid": "6", "cid": "8", "client_nickname": "DG-104 Marcel",
             "client_type": "0", "client_flag_talking": "1"},
            {"clid": "99", "cid": "7", "client_nickname": "DashboardView/Test",
             "client_type": "0", "client_flag_talking": "0"},
            {"clid": "10", "cid": "8", "client_nickname": "QueryBot",
             "client_type": "1", "client_flag_talking": "1"},
        ]
        talking, available = app.query_voice_status(rows)
        self.assertTrue(available)
        self.assertEqual(talking, {"6"})  # Includes a user in OTHER channel
        self.assertEqual(app.query_voice_status([
            {"clid": "6", "client_type": "0", "client_nickname": "Marcel",
             "client_input_muted": "0", "client_is_talker": "1"}
        ]), (set(), False))  # No inference from mic/talk-permission

    def test_normal_client_plus_global_server_monitor(self):
        dashboard = app.DashboardState()
        dashboard.mode = "client"
        dashboard.client_viewer = object()
        dashboard.connected = True
        dashboard.speaker_data = True
        dashboard.users = [
            {"id": "3", "name": "DG-103 Ruud", "region": 103, "channel_id": 7, "speaking": False},
            {"id": "4", "name": "DG-104 Marcel", "region": 104, "channel_id": 8, "speaking": False},
        ]
        dashboard.client_channel = 7
        response = {"channels": [], "users": [
            {"clid": "3", "cid": "7", "client_nickname": "DG-103 Ruud",
             "client_type": "0", "client_flag_talking": "0"},
            {"clid": "4", "cid": "8", "client_nickname": "DG-104 Marcel",
             "client_type": "0", "client_flag_talking": "1"},
        ]}
        def fake_query(*args, **kwargs):
            self.assertFalse(kwargs.get("include_channels", True))
            return response

        with patch.object(app, "ts_query", side_effect=fake_query):
            dashboard.start_global_monitor({"global_monitor": True})
            for _ in range(100):
                if dashboard.snapshot()["monitor"]["live"]:
                    break
                time.sleep(0.02)
            got = dashboard.snapshot()
            self.assertTrue(got["monitor"]["live"])
            self.assertEqual(got["talk_scope"], "hele_server")
            self.assertEqual(got["active_users"][0]["name"], "DG-104 Marcel")
            self.assertTrue(next(g for g in got["groups"] if g["code"] == 104)["active"])
            # The ordinary same-channel TS3 event MUST NOT hide remote TX.
            dashboard.handle_client_event(dashboard.client_viewer, {
                "type": "talkers", "clients": [3],
            })
            self.assertEqual(dashboard.snapshot()["active_users"][0]["id"], "4")
            dashboard.stop_global_monitor()
            self.assertFalse(dashboard.snapshot()["monitor"]["live"])
            self.assertEqual(dashboard.snapshot()["talk_scope"], "eigen_kanaal")

        dashboard.global_monitor_count = 1
        dashboard.global_monitor_updated_at = time.time()
        dashboard.global_monitor_active = True
        self.assertEqual(dashboard.snapshot()["talk_scope"], "gedeeltelijk")

    def test_normal_team_speak_viewer_only(self):
        from direct_client import DirectViewer, display_nickname
        self.assertEqual(display_nickname("Michiel"), "DashboardView/Michiel")
        self.assertEqual(display_nickname(" Michiel "), "DashboardView/Michiel")
        for invalid in ("", "x" * 17, "Ab\nCd"):
            with self.assertRaises(ValueError):
                display_nickname(invalid)

        viewer = DirectViewer(app.DashboardState())
        for forbidden in ("ptt_on", "sendAudio test", "muteinput 0", "chat hello", "switch 0"):
            with self.assertRaises(ValueError):
                viewer.send(forbidden)

    def test_normal_ts3_events_drive_real_dg_markers(self):
        dashboard = app.DashboardState()
        dashboard.set_mode("client")
        viewer = object()
        dashboard.client_viewer = viewer
        dashboard.handle_client_event(viewer, {
            "type": "connected", "server_name": "Heerlen", "identity": "secret"
        })
        dashboard.handle_client_event(viewer, {
            "type": "channels",
            "own_client_id": 99,
            "channels": [{"id": 7, "name": "Kanaal 7"}, {"id": 8, "name": "Kanaal 8"}],
            "clients": [
                {"id": 99, "channel": 7, "name": "DashboardView/Michiel", "is_query": False},
                {"id": 3, "channel": 7, "name": "DG-103 Ruud", "is_query": False},
                {"id": 4, "channel": 8, "name": "DG-104 Marcel", "is_query": False},
                {"id": 5, "channel": 7, "name": "ServerQuery", "is_query": True},
            ],
        })
        first = dashboard.snapshot()
        self.assertTrue(first["connected"])
        self.assertTrue(first["speaker_data"])
        self.assertEqual(first["selected_channel"], 7)
        self.assertEqual(first["all_users_count"], 2)  # Viewer and query bot excluded
        self.assertEqual(first["active_users"], [])
        dashboard.handle_client_event(viewer, {"type": "talkers", "clients": [3, 99]})
        active = dashboard.snapshot()
        self.assertEqual(len(active["active_users"]), 1)
        self.assertEqual(active["active_users"][0]["name"], "DG-103 Ruud")
        self.assertTrue(next(g for g in active["groups"] if g["code"] == 103)["active"])
        self.assertFalse(next(g for g in active["groups"] if g["code"] == 104)["active"])
        dashboard.handle_client_event(viewer, {"type": "talkers", "clients": []})
        ended = dashboard.snapshot()
        self.assertEqual(ended["active_users"], [])
        self.assertEqual(ended["heard"][0]["name"], "DG-103 Ruud")
        dashboard.handle_client_event(viewer, {"type": "disconnected", "reason": "Test klaar"})
        self.assertFalse(dashboard.snapshot()["connected"])

    def test_explicit_observers_are_off_by_default(self):
        st=app.DashboardState()
        self.assertFalse(st.observers.enabled)
        self.assertFalse(st.snapshot()["observers"]["enabled"])
        self.assertEqual(MAX_OBSERVERS, 8)
        with self.assertRaises(ValueError):
            identity_path("../attack")
        self.assertNotEqual(identity_path(), identity_path("channel-7"))

    def test_multiple_real_channel_observers_switch_and_track_rx(self):
        state=app.DashboardState()
        state.mode="client"
        state.connected=True
        state.speaker_data=True
        state.client_viewer=object()
        state.client_channel=7
        state.channels=[{"id":7,"name":"Algemeen"},{"id":8,"name":"Regio Oost"}]
        state.users=[
            {"id":"3","name":"DG-103 Ruud","region":103,"channel_id":7,"speaking":False},
            {"id":"4","name":"DG-104 Marcel","region":104,"channel_id":8,"speaking":False},
        ]
        pool=state.observers
        obs=ChannelObserver(pool,8)
        sent=[]
        obs.viewer.send=lambda command: sent.append(command)
        with pool.lock:
            pool.enabled=True
            pool.observers[8]=obs
        self.assertEqual(pool._targets()[0],[8])
        # New viewer starts in the default TS channel, then moves to CID 8.
        obs.handle_client_event(obs.viewer,{"type":"channels","own_client_id":99,"clients":[
            {"id":99,"channel":7}
        ]})
        self.assertEqual(sent,["switch 8"])
        obs.handle_client_event(obs.viewer,{"type":"channels","own_client_id":99,"clients":[
            {"id":99,"channel":8}
        ]})
        obs.handle_client_event(obs.viewer,{"type":"talkers","clients":[4,99]})
        view=state.snapshot()
        self.assertTrue(view["observers"]["complete"])
        self.assertEqual(view["talk_scope"],"zichtbare_kanalen")
        self.assertEqual(len(view["active_users"]),1)
        self.assertEqual(view["active_users"][0]["name"],"DG-104 Marcel")
        self.assertTrue(next(g for g in view["groups"] if g["code"] == 104)["active"])
        obs.handle_client_event(obs.viewer,{"type":"talkers","clients":[]})
        ended=state.snapshot()
        self.assertEqual(ended["active_users"],[])
        self.assertEqual(ended["heard"][0]["name"],"DG-104 Marcel")
        # If a third occupied channel exists, coverage must say PARTIAL.
        state.channels.append({"id":9,"name":"Regio West"})
        state.users.append({"id":"5","name":"DG-100 Peter","region":100,
                            "channel_id":9,"speaking":False})
        self.assertEqual(state.snapshot()["talk_scope"],"gedeeltelijk")
        with pool.lock:
            pool.observers.clear()
            pool.enabled=False

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
                        self.wfile.write(b"clid=5 cid=7 client_nickname=DG-103\sMichiel client_type=0 client_flag_talking=0|clid=6 cid=7 client_nickname=Query client_type=1 client_flag_talking=0|clid=7 cid=8 client_nickname=DG-104\sMarcel client_type=0 client_flag_talking=1\nerror id=0 msg=ok\n")
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
            self.assertEqual(app.query_voice_status(result["users"]), ({"7"}, True))
            server.shutdown()


if __name__ == "__main__":
    unittest.main()
