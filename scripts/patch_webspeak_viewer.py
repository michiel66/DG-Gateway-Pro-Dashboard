"""Apply a minimal *read-only viewer* adaptation to PINNED WebSpeak3.

TS-Heerlen-pc itself builds this exact connector from WebSpeak3; this build
uses the same known-good protocol implementation instead of ServerQuery.
The receiver may need incoming audio packet timing to detect talkers, but
base64 audio samples are NEVER emitted, played, recorded or sent to Python.
NO PTT or microphone interface is available in the Python dashboard.
"""
from pathlib import Path

source = Path("upstream/connector/src/main.rs")
s = source.read_text(encoding="utf-8")
before = '''fn emit(event: &Event) {
\tprintln!("{}", serde_json::to_string(event).unwrap());
}'''
after = '''fn emit(event: &Event) {
\t// DG Viewer: incoming audio is analysed only to find active speaker IDs.
\t// Never forward PCM to the desktop UI, a sound device or storage.
\tif matches!(event, Event::AudioOut { .. }) {
\t\treturn;
\t}
\tprintln!("{}", serde_json::to_string(event).unwrap());
}'''
assert s.count(before) == 1, "WebSpeak3 connector version differs: refusing patch"
s = s.replace(before, after, 1)
assert 'Event::Talkers { clients:' in s, "Missing real speaking-status events"
assert 'Event::Channels {' in s, "Missing normal TS3 client/user/channel events"
assert '\"muteinput \"' in s or 'muteinput ' in s, "Microphone disable command missing"
source.write_text(s, encoding="utf-8")
print("WebSpeak3 native TeamSpeak client ready: audio samples blocked; speaker events retained.")
