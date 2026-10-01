# ComfyUI Model Live Refresh

Automatically refreshes model choices on existing nodes when a model file or subfolder is added, removed, or renamed. Uses ComfyUI's native Refresh Node Definitions flow, including Nodes 2.0. No browser page reload is needed.

## Install

Copy this whole directory to `ComfyUI/custom_nodes/ComfyUI-ModelLiveRefresh`. In the same Python environment used to run ComfyUI, install `requirements.txt`, then restart ComfyUI once. On the next startup, look for `ModelLiveRefresh: watching ... model directories` in the log.

For a typical macOS/Linux virtual environment, from the ComfyUI root:

```sh
pip install -r requirements.txt
```

## Scope

The watcher reads ComfyUI's live registered model paths. This includes paths registered from `extra_model_paths.yaml`, ComfyUI Desktop's generated `extra_models_config.yaml`, `--models-directory`, and custom nodes. It does not parse or depend on any particular configuration filename. It reacts to filename and directory changes and tells every connected browser to run ComfyUI's native node-definition refresh. It does not reload Python code from `custom_nodes`. The model sidebar has a separate refresh mechanism.

The plugin leaves a currently selected filename as-is when that file is renamed; select the new name before running the workflow. File contents changed under the same name do not trigger a refresh. A newly registered root may take up to 10 seconds to acquire a watch. A root that does not yet exist is watched after its parent categories are added and scanned at the next sync; restart if its creation was missed.

Do not install this together with Fast Node Refresh: the two plugins may trigger duplicate updates.

## ComfyUI Desktop on macOS

The desktop app normally stores its data under the `basePath` in `~/Library/Application Support/ComfyUI/config.json` and generates `~/Library/Application Support/ComfyUI/extra_models_config.yaml`. Install this plugin in the `custom_nodes` folder under that data directory, then install the dependency with the Python environment used by the desktop app.
