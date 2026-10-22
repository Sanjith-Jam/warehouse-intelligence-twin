export type Cell = [number, number]
export type Slot = { slot_id: string; rack_cell: Cell; access_cell: Cell; sku: string }
export type Product = { sku: string; name: string; pick_frequency: number }
export type Order = { order_id: string; lines: { sku: string; quantity: number }[] }
export type Demo = {
  meta: { dataset_id: string; source: string; month: string | null; real_order_data: boolean; synthetic_warehouse: boolean; cell_size_m: number }
  layout: { layout_id: string; width: number; height: number; walkable_cells: Cell[]; dock: Cell; slots: Slot[] }
  products: Product[]
  orders: Order[]
}
export type Policy = 'original' | 'baseline' | 'player'
export type Simulation = {
  dataset_id: string
  policy: Policy
  slot_assignments: Record<string, string>
  orders_replayed: number
  distance_m: number
  estimated_pick_time_s: number
  average_pick_time_s: number
  routes: { order_id: string; waypoints: Cell[]; visits: { sku: string; slot_id: string; waypoint_index: number }[] }[]
  warnings: string[]
  assumptions: { speed_mps: number; handling_seconds_per_line: number }
}
