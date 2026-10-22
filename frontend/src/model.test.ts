import assert from 'node:assert/strict'
import test from 'node:test'
import { samplePlayback, swapAssignments, validateDemo, validateSimulation } from './model.ts'
import { preview } from './preview.ts'
import type { Simulation } from './types.ts'

test('swaps a complete assignment without mutating the request snapshot', () => {
  const before = { A: 'sku-1', B: 'sku-2' }
  const after = swapAssignments(before, 'A', 'B')
  assert.deepEqual(after, { A: 'sku-2', B: 'sku-1' })
  assert.deepEqual(before, { A: 'sku-1', B: 'sku-2' })
})

test('playback uses returned aisle waypoints and pauses for handling', () => {
  const result: Simulation = { dataset_id: 'test', policy: 'player', slot_assignments: {}, orders_replayed: 1, distance_m: 3, estimated_pick_time_s: 12.5, average_pick_time_s: 12.5, warnings: [], assumptions: { speed_mps: 1.2, handling_seconds_per_line: 10 }, routes: [{ order_id: 'O1', waypoints: [[0, 0], [1, 0], [0, 0]], visits: [{ sku: 'sku-1', slot_id: 'A', waypoint_index: 1 }] }] }
  assert.deepEqual(samplePlayback(result, 1.5, 0.625).cell, [0.5, 0])
  assert.equal(samplePlayback(result, 1.5, 4).sku, 'sku-1')
  assert.equal(samplePlayback(result, 1.5, 12.5).distance_m, 3)
  assert.equal(samplePlayback(result, 1.5, 12.5).done, true)
})

test('rejects a response with a route through racks or a changed order', () => {
  assert.equal(validateDemo(preview), true)
  assert.equal(validateDemo({ ...preview, orders: [{ order_id: 'broken' }] } as typeof preview), false)
  const demo = { ...preview, orders: [{ ...preview.orders[0], lines: [preview.orders[0].lines[0]] }] }
  const slots = Object.fromEntries(preview.layout.slots.map(slot => [slot.slot_id, slot.sku]))
  const response: Simulation = { dataset_id: preview.meta.dataset_id, policy: 'player', slot_assignments: slots, orders_replayed: 1, distance_m: 3, estimated_pick_time_s: 12.5, average_pick_time_s: 12.5, warnings: [], assumptions: { speed_mps: 1.2, handling_seconds_per_line: 10 }, routes: [{ order_id: 'DEMO-ORDER-01', waypoints: [[0, 0], [1, 0], [0, 0]], visits: [{ sku: 'DEMO-001', slot_id: 'S001', waypoint_index: 1 }] }] }
  assert.equal(validateSimulation(demo, response, 'player', ['DEMO-ORDER-01'], slots, 1.2), true)
  assert.equal(validateSimulation(demo, { ...response, routes: [{ ...response.routes[0], waypoints: [[0, 0], [1, 1], [0, 0]] }] }, 'player', ['DEMO-ORDER-01'], slots, 1.2), false)
  assert.equal(validateSimulation(demo, response, 'player', ['OTHER-ORDER'], slots, 1.2), false)
  assert.equal(validateSimulation(demo, { ...response, distance_m: 6 }, 'player', ['DEMO-ORDER-01'], slots, 1.2), false)
})
