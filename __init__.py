"""Refresh ComfyUI model selectors when registered model directories change."""

from .watcher import start_watcher

NODE_CLASS_MAPPINGS = {}
WEB_DIRECTORY = "./web"

start_watcher()

__all__ = ["NODE_CLASS_MAPPINGS", "WEB_DIRECTORY"]
