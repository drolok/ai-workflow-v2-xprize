import json
import tempfile
import time
import unittest
from pathlib import Path

from server import Store, Watcher

PROOF = '{"event_type":"verification","captured_by":"claude","actor":null,"summary":"Prueba de verificacion en vivo por Claude, sin refrescar la pagina","status":"success","occurred_at":"2026-07-23T18:30:00Z","source":"claude-live-check"}\n'


class WorkEventFeedTest(unittest.TestCase):
    def test_sparse_work_event_is_visible_in_sse_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = Store()
            watcher = Watcher(store, root)
            proof = root / "proof.react.jsonl"
            proof.write_text(PROOF, encoding="utf-8")
            watcher.read_jsonl(proof)
            snapshot = store.snapshot()
            self.assertEqual(snapshot["events"][0]["event_type"], "verification")
            self.assertEqual(snapshot["events"][0]["action"], "Prueba de verificacion en vivo por Claude, sin refrescar la pagina")
            self.assertEqual(snapshot["events"][0]["outcome"], "success")
            self.assertEqual(snapshot["analytics"]["success_by_type"][0]["count"], 1)
            client = __import__("queue").Queue()
            store.clients.append(client)
            store.add({**snapshot["events"][0], "event_id": "second-event"})
            self.assertIn("events", json.loads(client.get_nowait()))


if __name__ == "__main__":
    unittest.main()
