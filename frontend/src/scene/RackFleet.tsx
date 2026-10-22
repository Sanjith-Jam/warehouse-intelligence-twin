import { useLayoutEffect, useRef } from 'react'
import { Color, Object3D } from 'three'
import type { InstancedMesh } from 'three'
import type { Product, Slot } from '../types'

type Props = { slots: Slot[]; products: Product[]; assignments: Record<string, string>; selected: string | null; activeSku: string | null; size: number; width: number; depth: number; onSelect: (slotId: string) => void }

export function RackFleet({ slots, products, assignments, selected, activeSku, size, width, depth, onSelect }: Props) {
  const posts = useRef<InstancedMesh>(null)
  const beams = useRef<InstancedMesh>(null)
  const cartons = useRef<InstancedMesh>(null)
  const hit = useRef<InstancedMesh>(null)

  useLayoutEffect(() => {
    if (!posts.current || !beams.current || !cartons.current || !hit.current) return
    const dummy = new Object3D()
    const color = new Color()
    const frequencies = new Map(products.map(product => [product.sku, product.pick_frequency]))
    const cutoff = [...products].sort((a, b) => b.pick_frequency - a.pick_frequency)[Math.max(0, Math.ceil(products.length / 4) - 1)]?.pick_frequency ?? Infinity
    let postIndex = 0, beamIndex = 0, cartonIndex = 0
    const place = (mesh: InstancedMesh, index: number, x: number, y: number, z: number, sx: number, sy: number, sz: number, tint?: string) => {
      dummy.position.set(x, y, z)
      dummy.scale.set(sx, sy, sz)
      dummy.updateMatrix()
      mesh.setMatrixAt(index, dummy.matrix)
      if (tint) mesh.setColorAt(index, color.set(tint))
    }
    slots.forEach((slot, index) => {
      const x = (slot.rack_cell[0] + 0.5) * size - width / 2
      const z = (slot.rack_cell[1] + 0.5) * size - depth / 2
      const active = selected === slot.slot_id || assignments[slot.slot_id] === activeSku
      const fast = (frequencies.get(assignments[slot.slot_id]) ?? 0) >= cutoff
      const steel = active ? '#168fa6' : fast ? '#305b69' : '#718e9b'
      const beam = active ? '#41bbcb' : '#b9803a'
      for (const px of [-0.39, 0.39]) for (const pz of [-0.35, 0.35]) place(posts.current!, postIndex++, x + px * size, 0.9, z + pz * size, 0.085, 1.8, 0.085, steel)
      for (const y of [0.18, 0.89, 1.7]) place(beams.current!, beamIndex++, x, y, z, size * 0.83, 0.065, size * 0.76, beam)
      for (const y of [0.2, 0.91]) place(beams.current!, beamIndex++, x, y, z - size * 0.35, size * 0.83, 0.075, 0.07, steel)
      place(cartons.current!, cartonIndex++, x - size * 0.16, 0.53, z, size * 0.29, 0.48, size * 0.39, '#c0a17a')
      place(cartons.current!, cartonIndex++, x + size * 0.17, 1.24, z, size * 0.31, 0.49, size * 0.38, '#dfc093')
      place(hit.current!, index, x, 0.91, z, size * 0.84, 1.82, size * 0.78)
    })
    for (const mesh of [posts.current, beams.current, cartons.current, hit.current]) { mesh.instanceMatrix.needsUpdate = true; mesh.computeBoundingSphere() }
    for (const mesh of [posts.current, beams.current, cartons.current]) if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true
  }, [slots, products, assignments, selected, activeSku, size, width, depth])

  return <>
    <instancedMesh ref={posts} args={[undefined, undefined, slots.length * 4]} castShadow frustumCulled={false}><boxGeometry /><meshStandardMaterial color="#ffffff" roughness={0.55} metalness={0.35} /></instancedMesh>
    <instancedMesh ref={beams} args={[undefined, undefined, slots.length * 5]} castShadow receiveShadow frustumCulled={false}><boxGeometry /><meshStandardMaterial color="#ffffff" roughness={0.62} metalness={0.2} /></instancedMesh>
    <instancedMesh ref={cartons} args={[undefined, undefined, slots.length * 2]} castShadow frustumCulled={false}><boxGeometry /><meshStandardMaterial color="#ffffff" roughness={0.92} /></instancedMesh>
    <instancedMesh ref={hit} args={[undefined, undefined, slots.length]} onClick={event => { event.stopPropagation(); if (event.instanceId !== undefined) onSelect(slots[event.instanceId].slot_id) }} onPointerOver={() => { document.body.style.cursor = 'pointer' }} onPointerOut={() => { document.body.style.cursor = '' }} frustumCulled={false}><boxGeometry /><meshBasicMaterial transparent opacity={0} depthWrite={false} /></instancedMesh>
  </>
}
