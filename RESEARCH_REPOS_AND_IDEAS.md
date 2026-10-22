# Repositories, Devpost references and feature ideas

Research links for **Warehouse Intelligence Twin** (PS 4.2 + PS 1.2-inspired analytics). External projects are inspiration, **not proof that their code is compatible or licensed for reuse**. Inspect current license and source before copying. No hardware.

## Warehouse digital twins and 3D UI

- [WareTwin](https://github.com/WayneChou-bot/WareTwin) — 3D warehouse reference; inspect implementation, license, scene/state architecture.
- [WareTwin — alternate](https://github.com/DoanNguyenTrong/waretwin) — robots, routes, operations dashboard; verify current source and license.
- [3D Express Warehouse](https://github.com/jiaxiantao/3d-express-warehouse) — React Three Fiber, slot IDs, SKU locate, rack visualization, selection.
- [WarehouseDigitalTwin](https://github.com/Alibadloo/WarehouseDigitalTwin) — AI inventory recommendations and live 3D scene.
- [3d-warehouse](https://github.com/astopaal/3d-warehouse) — navigable 3D warehouse UI.
- [3D Virtual Store](https://github.com/Elfoslav/3d-virtual-store) — first-person interactive product scene.
- [Multi-Robot Fulfillment](https://github.com/mihir1mathur/multi-robot-fulfillment-path-planning) — routing and collision-aware coordination; optional reading only.
- [MRWS](https://github.com/automaticdai/MRWS_MultiRobot_Warehouse_Scheduling) — simulation/scheduling architecture; optional reading.
- [Open Industry Project](https://github.com/Open-Industry-Project/Open-Industry-Project) — industrial twin visualization, too large to adopt in 3 hours.

## Picking, slotting, simulation

- [Picking Route](https://github.com/samirsaci/picking-route) — batching, travel-distance comparison.
- [Pick Path Optimization](https://github.com/rithiksachdev/Pick-Path-Optimization) — Python route backend + React UI.
- [warehouse-path](https://github.com/jeremyfourna/warehouse-path) — picker tour heuristics.
- [pick-path-optimizer](https://github.com/virbahu/pick-path-optimizer) — S-shape/largest-gap concepts.
- [warehouse-slotting-optimizer](https://github.com/virbahu/warehouse-slotting-optimizer) — ABC velocity and slot assignment.
- [warehouse-slotting-ml](https://github.com/virbahu/warehouse-slotting-ml) — slotting ML concepts, not required for MVP.
- [warehouse-operations-optimization](https://github.com/Vikas-Jakhar/warehouse-operations-optimization) — ABC, route heuristics and comparisons.
- [warehouse-slotting field manual](https://github.com/warehouse-slotting/warehouse-slotting) — affinity and practical constraints.
- [warehouse_optimization](https://github.com/jbghosh/warehouse_optimization) — co-picking affinity and assignment research; check licensing.
- [warehouse-optimize](https://github.com/nvlinhvn/warehouse-optimize) — item placement optimization notebook.
- [MultiRobot Warehouse Simulation](https://github.com/aaronreycast/Multirobot-Warehouse-Simulation) — congestion/collision concepts.

## Text-to-SQL / DuckDB / evaluation

- [AWS Data Agent on DuckDB](https://github.com/aws-samples/sample-data-agent-on-duckdb) — governed metrics, read-only queries, bounded result handling.
- [AmbiSQL](https://github.com/JustinzjDing/AmbiSQL) — clarify ambiguous questions before SQL.
- [SQLGlot](https://github.com/tobymao/sqlglot) — AST parser/inspection; parser alone is not a sandbox.
- [Duck-UI](https://github.com/caioricciuti/duck-ui) — browser DuckDB analytics UI.
- [UNITE benchmark](https://github.com/awslabs/unified-text2sql-benchmark) — execution-based evaluation.
- [text-to-sql-agent](https://github.com/shreyabaid007/text-to-sql-agent) — LangGraph and streaming UX.
- [sql-agent](https://github.com/tthustla/sql-agent) — DuckDB agent/evaluation patterns.
- [text-to-sql](https://github.com/dogukannulu/text-to-sql) — clarify/validate/correct workflow.
- [LangChain text-to-sql-agent](https://github.com/langchain-ai/text-to-sql-agent) — schema discovery and retries.
- [SQLBot](https://github.com/dataease/SQLBot) — conversational BI and terminology.
- [PremSQL](https://github.com/premAI-io/premsql) — agent and evaluation patterns.
- [Vanna](https://github.com/vanna-ai/vanna) — SQL agent security/UI reference; check archival status.

## Devpost projects — inspiration, not code source

- [SI Storage](https://devpost.com/software/si-storage) — inventory-linked 3D twin, camera observations and trust boundaries. Its previously referenced GitHub URL may be unavailable; verify before cloning.
- [FactoryMind](https://devpost.com/software/factorymind) — what-if simulation and worker assignment.
- [SpineOps AI](https://devpost.com/software/spineops-ai) — bottlenecks and ROI.
- [AromaSys](https://devpost.com/software/aromasys-ai-warehouse-dashboard) — layout editor and AI copilot.
- [Picking by Voice](https://devpost.com/software/picking-by-voice) — hands-free picking; **do not build voice in MVP**.
- [Overwatch](https://devpost.com/software/overwatch-y9jtdx) — dispatch and event audit.
- [RobotixFunnel](https://devpost.com/software/robotixfunnel) — order-driven digital twin.
- [Bee Hackers](https://devpost.com/software/bee-hackers-report-and-map-generating-tool) — cargo slotting and path maps.
- [DammRoute](https://devpost.com/software/dammroute-smart-logistics-platform) — logistics routing.
- [THE WAREHOUSE](https://devpost.com/software/the-warehouse) — warehouse assistant.
- [WarehouseIQ](https://devpost.com/software/warehouseiq-agentic-ai-for-amazon-fulfillment-centers) — evidence-backed operational analysis.
- [DAI](https://devpost.com/software/dai-ai-data-analyst-that-finds-hidden-cash-in-your-data) — read-only SQL and auditable results.
- [CUFIA](https://devpost.com/software/cufia-the-conversational-financial-agent-for-restaurants) — conversational inventory updates; **not for read-only MVP**.
- [TiDB SmartLedger](https://devpost.com/software/tidb-smartledger) — NL-to-SQL plus graphs.

## Original ideas catalog (not all MVP features)

1. **Spatial SQL:** select SQL result rows and highlight associated shelf meshes (high priority after P0).
2. **Counterfactual slotting:** same real orders, three layouts, distance/time delta (mandatory P0).
3. **Basket-affinity slotting:** co-purchased SKUs near each other (later enhancement).
4. **Warehouse time machine:** replay event stream with seek controls (later enhancement).
5. **Explain my route:** expose path and distance provenance (good small addition).
6. **Warehouse strategy game:** swap SKU slots, score against baseline (mandatory P0).
7. **Heatmap of picks:** demand-weighted slot coloring (visual polish).
8. **What-if query:** translate a read-only analytic question into a proposed layout scenario, with explicit user confirmation (later enhancement).
9. **Audit SQL:** show executed query, filters and row counts (P1).
10. **Voice / QR / RFID / ESP32:** explicitly out of scope for this build.

## Dataset and interpretation

[UCI Online Retail II](https://archive.ics.uci.edu/dataset/502/online+retail+ii) is transaction data, **not a measured warehouse map**. Use one month of genuine invoices, derive pick frequency and immutable order batches, exclude cancellation/return quantities from positive pick demand, then map products to clearly synthetic shelf slots. Never describe simulated distance as measured historical walking distance.

## Priority reading for agents

Sol: WareTwin, 3D Express Warehouse, SI Storage showcase. Luna: Picking Route, warehouse-path, slotting optimizer, Retail II data. Antigravity Claude: AWS DuckDB agent, AmbiSQL, SQLGlot. Antigravity Flash: benchmark, smoke tests, dataset validation. Do not spend more than 10–15 minutes on research during the three-hour sprint.
