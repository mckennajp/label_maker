Third-party clones, shallow, for reading — not vendored into our driver.

| Path | Why it is here |
|---|---|
| `phomemo-tools` | Working M110 raster encoder (closest 50 mm sibling). |
| `web-based-label-studio` | Aimotech Print Master protocol + Web Serial UI. M100 is in the SDK catalog but not implemented. |

Re-clone / update with `git pull` inside each folder. Do not mix their git history with this repo if you later `git init` here — add `refs/` to `.gitignore` or use submodules.
