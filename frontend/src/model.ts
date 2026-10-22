import type { Cell, Demo, Policy, Simulation } from './types.ts'

const cellKey = (cell: Cell) => `${cell[0]},${cell[1]}`
const sameCell = (a: Cell, b: Cell) => a[0] === b[0] && a[1] === b[1]

export function validateDemo(demo: Demo): boolean {
  if (!demo?.meta?.dataset_id || !Number.isFinite(demo.meta.cell_size_m) || demo.meta.cell_size_m <= 0 || !demo.layout || !Array.isArray(demo.layout.slots) || !Array.isArray(demo.layout.walkable_cells) || !Array.isArray(demo.orders) || !demo.orders.length || !Array.isArray(demo.products) || !Number.isInteger(demo.layout.width) || !Number.isInteger(demo.layout.height) || demo.layout.width <= 0 || demo.layout.height <= 0) return false
  const cell = (value: Cell) => Array.isArray(value) && value.length === 2 && value.every(Number.isInteger) && value[0] >= 0 && value[0] < demo.layout.width && value[1] >= 0 && value[1] < demo.layout.height
  if (!cell(demo.layout.dock) || !demo.layout.walkable_cells.every(cell)) return false
  const walkable = new Set(demo.layout.walkable_cells.map(cellKey))
  if (!walkable.has(cellKey(demo.layout.dock))) return false
  const slotIds = demo.layout.slots.map(slot => slot?.slot_id)
  const skus = demo.layout.slots.map(slot => slot?.sku)
  if (new Set(slotIds).size !== slotIds.length || new Set(skus).size !== skus.length || demo.layout.slots.some(slot => !slot?.slot_id || !slot.sku || !cell(slot.rack_cell) || !cell(slot.access_cell) || walkable.has(cellKey(slot.rack_cell)) || !walkable.has(cellKey(slot.access_cell)))) return false
  if (demo.products.some(product => !product?.sku || typeof product.name !== 'string' || !product.name || !Number.isFinite(product.pick_frequency) || product.pick_frequency < 0) || new Set(demo.products.map(product => product.sku)).size !== demo.products.length || skus.some(sku => !demo.products.some(product => product.sku === sku))) return false
  const knownSkus = new Set(skus)
  return new Set(demo.orders.map(order => order?.order_id)).size === demo.orders.length && demo.orders.every(order => !!order?.order_id && Array.isArray(order.lines) && order.lines.length > 0 && order.lines.every(line => !!line && knownSkus.has(line.sku) && Number.isInteger(line.quantity) && line.quantity > 0))
}

export function validateSimulation(demo: Demo, result: Simulation, policy: Policy, orderIds: string[], playerAssignments: Record<string, string>, speed: number): boolean {
  if (!result || result.dataset_id !== demo.meta.dataset_id || result.policy !== policy || result.orders_replayed !== orderIds.length || !Array.isArray(result.routes) || result.routes.length !== orderIds.length || !result.slot_assignments || !result.assumptions || result.assumptions.speed_mps !== speed || result.assumptions.handling_seconds_per_line !== 10) return false
  if (![result.distance_m, result.estimated_pick_time_s, result.average_pick_time_s].every(value => Number.isFinite(value) && value >= 0)) return false
  const slotIds = demo.layout.slots.map(slot => slot.slot_id)
  const skus = demo.layout.slots.map(slot => slot.sku)
  if (Object.keys(result.slot_assignments).length !== slotIds.length || slotIds.some(id => !result.slot_assignments[id]) || new Set(Object.values(result.slot_assignments)).size !== skus.length || skus.some(sku => !Object.values(result.slot_assignments).includes(sku))) return false
  if (policy === 'player' && slotIds.some(id => result.slot_assignments[id] !== playerAssignments[id])) return false
  const walkable = new Set(demo.layout.walkable_cells.map(cellKey))
  const slots = new Map(demo.layout.slots.map(slot => [slot.slot_id, slot]))
  const validRoutes = result.routes.every((route, index) => route.order_id === orderIds[index] && Array.isArray(route.waypoints) && route.waypoints.length > 0 && Array.isArray(route.waypoints[0]) && Array.isArray(route.waypoints[route.waypoints.length - 1]) && Array.isArray(route.visits) && route.visits.length === demo.orders[index].lines.length && route.visits.every((visit, lineIndex) => visit.sku === demo.orders[index].lines[lineIndex].sku && (lineIndex === 0 || visit.waypoint_index >= route.visits[lineIndex - 1].waypoint_index)) && sameCell(route.waypoints[0], demo.layout.dock) && sameCell(route.waypoints[route.waypoints.length - 1], demo.layout.dock) && route.waypoints.every((cell, i) => Array.isArray(cell) && cell.length === 2 && cell.every(Number.isInteger) && walkable.has(cellKey(cell)) && (i === 0 || Math.abs(cell[0] - route.waypoints[i - 1][0]) + Math.abs(cell[1] - route.waypoints[i - 1][1]) === 1)) && route.visits.every(visit => Number.isInteger(visit.waypoint_index) && visit.waypoint_index >= 0 && visit.waypoint_index < route.waypoints.length && result.slot_assignments[visit.slot_id] === visit.sku && !!slots.get(visit.slot_id) && sameCell(route.waypoints[visit.waypoint_index], slots.get(visit.slot_id)!.access_cell)))
  if (!validRoutes) return false
  const distance = result.routes.reduce((total, route) => total + (route.waypoints.length - 1) * demo.meta.cell_size_m, 0)
  const time = distance / speed + result.routes.reduce((total, route) => total + route.visits.length * 10, 0)
  const near = (a: number, b: number) => Math.abs(a - b) <= 1e-6 * Math.max(1, Math.abs(b))
  return near(result.distance_m, distance) && near(result.estimated_pick_time_s, time) && near(result.average_pick_time_s, time / orderIds.length)
}

export function originalAssignments(demo: Demo): Record<string, string> {
  return Object.fromEntries(demo.layout.slots.map(slot => [slot.slot_id, slot.sku]))
}

export function swapAssignments(assignments: Record<string, string>, first: string, second: string): Record<string, string> {
  if (!assignments[first] || !assignments[second] || first === second) return assignments
  return { ...assignments, [first]: assignments[second], [second]: assignments[first] }
}

export type PlaybackSample = { cell: Cell; distance_m: number; time_s: number; order_id: string; sku: string | null; handling: boolean; done: boolean }

export function samplePlayback(result: Simulation, cellSize: number, elapsed: number): PlaybackSample {
  const speed = result.assumptions.speed_mps
  const handlingSeconds = result.assumptions.handling_seconds_per_line
  let clock = 0
  let walked = 0
  let last: Cell = result.routes[0]?.waypoints[0] ?? [0, 0]
  let orderId = result.routes[0]?.order_id ?? ''
  for (const route of result.routes) {
    orderId = route.order_id
    const visitsAt = new Map<number, typeof route.visits>()
    for (const visit of route.visits) visitsAt.set(visit.waypoint_index, [...(visitsAt.get(visit.waypoint_index) ?? []), visit])
    for (let index = 0; index < route.waypoints.length; index++) {
      const point = route.waypoints[index]
      if (index > 0) {
        const from = route.waypoints[index - 1]
        const segment = (Math.abs(point[0] - from[0]) + Math.abs(point[1] - from[1])) * cellSize
        const duration = segment / speed
        if (elapsed < clock + duration) {
          const t = duration ? (elapsed - clock) / duration : 1
          return { cell: [from[0] + (point[0] - from[0]) * t, from[1] + (point[1] - from[1]) * t], distance_m: walked + segment * t, time_s: elapsed, order_id: orderId, sku: null, handling: false, done: false }
        }
        clock += duration
        walked += segment
      }
      last = point
      for (const visit of visitsAt.get(index) ?? []) {
        if (elapsed < clock + handlingSeconds) return { cell: point, distance_m: walked, time_s: elapsed, order_id: orderId, sku: visit.sku, handling: true, done: false }
        clock += handlingSeconds
      }
    }
  }
  return { cell: last, distance_m: walked, time_s: clock, order_id: orderId, sku: null, handling: false, done: true }
}
