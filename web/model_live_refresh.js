import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

const EVENT = "model_live_refresh.changed";
let timer;
let refreshing = false;
let again = false;

async function refresh() {
  if (refreshing) {
    again = true;
    return;
  }
  refreshing = true;
  try {
    // ComfyUI's own Refresh Node Definitions path updates open nodes in both
    // the classic canvas and the Vue-based Nodes 2.0 renderer.
    if (typeof app.refreshComboInNodes !== "function") {
      console.warn("ModelLiveRefresh: this frontend has no refreshComboInNodes API");
      return;
    }
    await app.refreshComboInNodes();
  } catch (error) {
    console.error("ModelLiveRefresh: node definition refresh failed", error);
  } finally {
    refreshing = false;
    if (again) {
      again = false;
      schedule();
    }
  }
}

function schedule() {
  clearTimeout(timer);
  timer = setTimeout(refresh, 350);
}

app.registerExtension({
  name: "ModelLiveRefresh.Nodes2",
  setup() {
    api.addEventListener(EVENT, schedule);
  },
});
