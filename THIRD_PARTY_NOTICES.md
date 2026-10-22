# Third-party references and dependencies

## Reference research — no source or assets copied

Inspected on 22 October 2026 during development. Research clones are outside the product repository in `../work/reference-repos/`. No reference-project build scripts or install hooks were executed.

| Reference | Revision / availability | License observed | Ideas reviewed |
| --- | --- | --- | --- |
| [WareTwin](https://github.com/WayneChou-bot/WareTwin) | `81f365f323e1a097e5819ca9045637544163f219` | MIT; Copyright (c) 2026 Wayne Chou | Procedural rack posts, beams and cartons; instanced geometry; capped device pixel ratio; orbit controls; stable animation transforms. |
| [3D Express Warehouse](https://github.com/jiaxiantao/3d-express-warehouse) | `8554816a504416f7327e47862e9f29053927e179` | MIT; Copyright (c) 2026 jiaxiantao | Slot selection and detail panel; common coordinate definitions; selection coloring; camera presets; movement-linked animation. |
| [SI Storage showcase](https://devpost.com/software/si-storage) | Devpost writeup retrieved successfully; [previously linked source](https://github.com/Tommy-Ren/SI-Storage) returned HTTP 404 | No source license verified | Linked rack inspection and clear distinctions between generated sample data, verified inventory, and illustrative shelf positions. |

Files read included WareTwin's `README.md`, `LICENSE`, `Scene3D.tsx`, `RackInstances.tsx`, `People.tsx`, and `Robots.tsx`; and 3D Express Warehouse's `README.md`, `LICENSE`, `warehouse-scene.tsx`, `warehouse-layout.ts`, and `warehouse-robot-animator.tsx`. Both file trees were inspected. The alternate WareTwin fork was unnecessary because the primary repository was available.

These are research acknowledgements, not claims that their source was incorporated. If source or assets are incorporated later, record the exact origin and retain the applicable license and copyright notices. SI Storage media and source are not included.

### Additional industrial design references

Official pages retrieved on 22 October 2026 through Firecrawl search and page retrieval. These pages describe vendor products; they do not establish an open-source license. No vendor code, models, screenshots, logos, or other assets are incorporated.

| Reference | Observed material | Application to this project |
| --- | --- | --- |
| [WATON — WATA AI](https://www.wata-ai.com/en/waton) | The product page describes warehouse walls, racks, floor loading, docks, safety tape, an object properties panel, and top/front/3D views. | Inspiration for an original industrial scene with a visible floor slab, open-front walls, rack frames, dock markings, and a selected-slot inspector. |
| [WareBee Digital Twin](https://warebee.com/digital-twin/) | The page describes historical orders, navigation maps, alternative slotting layouts compared through reports, and ABC/velocity heatmaps. | Inspiration for aligned original/baseline/player comparison rows and a secondary demand-color legend. |
| [Siemens/NVIDIA industrial digital twins](https://www.nvidia.com/en-us/case-studies/siemens-accelerates-product-development-and-innovation-with-industrial-ai/) | The official case study describes combining 2D/3D data with operational information, including conveyor, pallet, and operator paths. | Inspiration for keeping the spatial scene prominent while grouping operational status, selected-object details, and measured simulation results beside it. |
| [ConnectMQ conveyor digital twin tutorial](https://connectmq.com/blog/conveyor-digital-twin/) | This related tutorial explains motion driven by physical speed units, repeated instanced geometry, status indicators, and stopping movement when telemetry is stale. | General animation/status inspiration only; no MQTT, equipment control, hardware, or tutorial source is incorporated. |

The exact reference named “Digital Twin Conveyor” was not uniquely identified. The ConnectMQ tutorial above is a related discovery, not a verified match. A playback timeline is this project's own requirement-driven design choice, not an observed feature attributed to that tutorial. Suggested colors, panel arrangement, and scene composition are implementation interpretations rather than verified vendor UI specifications. Vendor-reported performance improvements must not be presented as this project's results.

## Frontend package dependencies

Direct package metadata inspected in `frontend/node_modules` on 22 October 2026:

| Package | Installed version observed | Declared license |
| --- | --- | --- |
| React / React DOM | 19.3.1 / 19.3.1 | MIT |
| Three.js | 0.180.0 | MIT |
| React Three Fiber | 9.8.2 | MIT |
| Drei | 10.7.9 | MIT |
| Vite | 7.3.7 | MIT |
| `@vitejs/plugin-react` | 5.2.0 | MIT |
| TypeScript | 5.9.3 | Apache-2.0 |
| `@types/node` / `@types/react` / `@types/react-dom` / `@types/three` | 24.19.2 / 19.3.0 / 19.3.0 / 0.180.0 | MIT |

Package license texts remain in their distributed packages. React credits Meta Platforms, Inc. and affiliates; Three.js credits the three.js authors; Drei credits react-spring. This table records direct dependencies, not an exhaustive transitive license inventory. Use `frontend/package-lock.json` for the committed resolved versions when available; update this table if dependencies change.

## Dataset

The project specifies [Online Retail II](https://archive.ics.uci.edu/dataset/502/online+retail+ii), Chen, D. (2012), UCI Machine Learning Repository, [DOI: 10.24432/C5CG6D](https://doi.org/10.24432/C5CG6D), CC BY 4.0. Dataset processing and filters must be documented alongside the actual backend export. This attribution does not assert that the real dataset has already been processed. Warehouse geometry, slot assignments, walking speed, and estimated travel times are simulated assumptions.
