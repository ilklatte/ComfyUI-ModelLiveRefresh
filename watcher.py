"""Watch registered model paths and notify browser clients after name changes."""

import logging
import os
import threading
import time

import folder_paths
from server import PromptServer
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

LOG = logging.getLogger(__name__)
EVENT = "model_live_refresh.changed"
SKIP_CATEGORIES = {"custom_nodes", "datasets"}
DEBOUNCE_SECONDS = 1.0


def registered_roots():
    """Read the live registry, including extra_model_paths.yaml and custom categories."""
    roots = {}
    for category, (paths, extensions) in list(folder_paths.folder_names_and_paths.items()):
        if category in SKIP_CATEGORIES or not extensions:
            continue
        for path in paths:
            root = os.path.realpath(path)
            if os.path.isdir(root):
                roots.setdefault(root, set()).add(category)
    return roots


def affected_categories(path, roots):
    path = os.path.realpath(path)
    affected = set()
    for root, categories in roots.items():
        try:
            if os.path.commonpath((root, path)) == root:
                affected.update(categories)
        except ValueError:
            pass
    return affected


class ModelEvents(FileSystemEventHandler):
    def __init__(self, mark):
        self.mark = mark

    def on_any_event(self, event):
        if event.event_type not in {"created", "deleted", "moved"}:
            return
        paths = [event.src_path]
        if event.event_type == "moved":
            paths.append(event.dest_path)
        self.mark(*paths)


class Watcher:
    def __init__(self, observer=None):
        self.observer = observer or Observer()
        self.lock = threading.Lock()
        self.pending = set()
        self.last_change = 0.0
        self.roots = {}
        self.watches = {}
        self.stop = threading.Event()
        self.handler = ModelEvents(self.mark)

    def sync_roots(self):
        current = registered_roots()
        for root in set(self.watches) - set(current):
            self.observer.unschedule(self.watches.pop(root))
        for root in set(current) - set(self.watches):
            try:
                self.watches[root] = self.observer.schedule(self.handler, root, recursive=True)
            except OSError as exc:
                LOG.warning("ModelLiveRefresh: cannot watch %s: %s", root, exc)
        with self.lock:
            self.roots = current

    def mark(self, *paths):
        with self.lock:
            for path in paths:
                self.pending.update(affected_categories(path, self.roots))
            if self.pending:
                self.last_change = time.monotonic()

    def flush(self):
        with self.lock:
            if not self.pending or time.monotonic() - self.last_change < DEBOUNCE_SECONDS:
                return set()
            categories = self.pending
            self.pending = set()
        for category in categories:
            folder_paths.filename_list_cache.pop(category, None)
        PromptServer.instance.send_sync(EVENT, {"categories": sorted(categories)})
        LOG.info("ModelLiveRefresh: refreshed %s", ", ".join(sorted(categories)))
        return categories

    def run(self):
        self.sync_roots()
        self.observer.start()
        LOG.info("ModelLiveRefresh: watching %d model directories", len(self.watches))
        next_sync = time.monotonic() + 10
        try:
            while not self.stop.wait(0.25):
                self.flush()
                # Pick up model categories registered by custom nodes after startup.
                if time.monotonic() >= next_sync:
                    self.sync_roots()
                    next_sync = time.monotonic() + 10
        finally:
            self.observer.stop()
            self.observer.join(timeout=5)


_started = False


def start_watcher():
    global _started
    if _started:
        return
    _started = True
    threading.Thread(target=Watcher().run, name="ModelLiveRefresh", daemon=True).start()
