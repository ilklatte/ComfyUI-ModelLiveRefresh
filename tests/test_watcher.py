import importlib.util
from pathlib import Path
import sys
import tempfile
import time
import types
import unittest

PLUGIN = Path(__file__).resolve().parents[1] / "watcher.py"


class ModelWatcherTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.sent = []
        self.folder_paths = types.ModuleType("folder_paths")
        self.folder_paths.folder_names_and_paths = {
            "loras": ([str(self.root)], {".safetensors"}),
            "custom_nodes": ([str(self.root)], set()),
        }
        self.folder_paths.filename_list_cache = {"loras": ["old.safetensors"]}
        server = types.ModuleType("server")
        server.PromptServer = types.SimpleNamespace(instance=types.SimpleNamespace(
            send_sync=lambda *args: self.sent.append(args)))
        self.old_modules = {name: sys.modules.get(name) for name in ("folder_paths", "server")}
        sys.modules["folder_paths"] = self.folder_paths
        sys.modules["server"] = server
        self.addCleanup(self.restore_modules)
        spec = importlib.util.spec_from_file_location("model_live_refresh_watcher_test", PLUGIN)
        self.mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.mod)
        from watchdog.observers.polling import PollingObserver
        self.watcher = self.mod.Watcher(PollingObserver(timeout=0.1))
        self.watcher.sync_roots()
        self.watcher.observer.start()
        self.addCleanup(self.watcher.observer.stop)
        self.addCleanup(self.watcher.observer.join, 3)

    def restore_modules(self):
        for name, value in self.old_modules.items():
            if value is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = value

    def test_add_and_rename_notifies_and_clears_cache(self):
        first = self.root / "first.safetensors"
        second = self.root / "second.safetensors"
        first.touch()
        first.rename(second)
        deadline = time.monotonic() + 4
        while not self.watcher.pending and time.monotonic() < deadline:
            time.sleep(0.05)
        self.assertEqual(self.watcher.pending, {"loras"})
        self.watcher.last_change -= 2
        self.assertEqual(self.watcher.flush(), {"loras"})
        self.assertNotIn("loras", self.folder_paths.filename_list_cache)
        self.assertEqual(self.sent, [(self.mod.EVENT, {"categories": ["loras"]})])

    def test_content_update_does_not_notify(self):
        file = self.root / "model.safetensors"
        file.touch()
        time.sleep(0.2)
        with self.watcher.lock:
            self.watcher.pending.clear()
        file.write_bytes(b"changed")
        time.sleep(0.5)
        self.assertFalse(self.watcher.pending)


if __name__ == "__main__":
    unittest.main()
