import type { Demo } from './types.ts'

const products = [
  ['DEMO-001', 'Lantern set', 82], ['DEMO-002', 'Glass jar', 68], ['DEMO-003', 'Desk clock', 59],
  ['DEMO-004', 'Gift wrap', 51], ['DEMO-005', 'Tea tin', 44], ['DEMO-006', 'Ceramic bowl', 38],
  ['DEMO-007', 'Storage basket', 33], ['DEMO-008', 'Photo frame', 29], ['DEMO-009', 'Candle holder', 24],
  ['DEMO-010', 'Notebook', 19], ['DEMO-011', 'Serving tray', 16], ['DEMO-012', 'Wall hook', 12],
] as const

export const preview: Demo = {
  meta: { dataset_id: 'local-preview-v1', source: 'synthetic UI preview', month: null, real_order_data: false, synthetic_warehouse: true, cell_size_m: 1.5 },
  layout: {
    layout_id: 'preview', width: 9, height: 7, dock: [0, 0],
    walkable_cells: Array.from({ length: 7 }, (_, z) => Array.from({ length: 9 }, (_, x) => [x, z] as [number, number]).filter(([x, y]) => x === 0 || y % 2 === 0)).flat(),
    slots: products.map(([sku], index) => {
      const x = 1 + index % 4 * 2
      const z = 1 + Math.floor(index / 4) * 2
      return { slot_id: `S${String(index + 1).padStart(3, '0')}`, rack_cell: [x, z], access_cell: [x, z - 1], sku }
    }),
  },
  products: products.map(([sku, name, pick_frequency]) => ({ sku, name, pick_frequency })),
  orders: [
    { order_id: 'DEMO-ORDER-01', lines: [{ sku: 'DEMO-001', quantity: 1 }, { sku: 'DEMO-004', quantity: 2 }] },
    { order_id: 'DEMO-ORDER-02', lines: [{ sku: 'DEMO-003', quantity: 1 }, { sku: 'DEMO-009', quantity: 1 }] },
  ],
}
