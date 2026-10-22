import { Canvas, useFrame } from '@react-three/fiber'
import { Grid, Line, OrbitControls } from '@react-three/drei'
import { Component, useEffect, useRef } from 'react'
import type { ReactNode, RefObject } from 'react'
import type { Group } from 'three'
import type { OrbitControls as OrbitControlsImpl } from 'three-stdlib'
import type { Cell, Demo, Simulation } from '../types'
import { samplePlayback } from '../model'

type Props = {
  demo: Demo
  assignments: Record<string, string>
  selected: string | null
  onSelect: (slotId: string) => void
  view: 'iso' | 'top'
  route: Simulation['routes'][number] | null
  simulation: Simulation | null
  playbackClock: RefObject<number>
  playing: boolean
  activeSku: string | null
}

function CameraControls({ view, target, span }: { view: Props['view']; target: [number, number, number]; span: number }) {
  const control = useRef<OrbitControlsImpl>(null)
  useEffect(() => {
    const c = control.current
    if (!c) return
    const distance = Math.max(span * 1.23, 12)
    c.object.position.set(view === 'top' ? target[0] + 0.01 : target[0] - distance * 0.68, view === 'top' ? distance : distance * 0.85, view === 'top' ? target[2] : target[2] - distance * 0.72)
    c.target.set(...target)
    c.update()
  }, [view, target[0], target[1], target[2], span])
  return <OrbitControls ref={control} target={target} minDistance={8} maxDistance={85} maxPolarAngle={Math.PI / 2.06} enableDamping />
}

function Picker({ dock, simulation, playbackClock, playing, size, width, depth }: { dock: Cell; simulation: Simulation | null; playbackClock: RefObject<number>; playing: boolean; size: number; width: number; depth: number }) {
  const ref = useRef<Group>(null)
  useFrame((_, delta) => {
    if (!ref.current) return
    if (simulation && playing) playbackClock.current = Math.min(playbackClock.current + Math.min(delta, 0.2) * 6, simulation.estimated_pick_time_s)
    const cell = simulation ? samplePlayback(simulation, size, playbackClock.current).cell : dock
    ref.current.position.set((cell[0] + 0.5) * size - width / 2, 0, (cell[1] + 0.5) * size - depth / 2)
  })
  return <group ref={ref} position={[(dock[0] + 0.5) * size - width / 2, 0, (dock[1] + 0.5) * size - depth / 2]}>
    <mesh position={[0, 0.51, 0]} castShadow><capsuleGeometry args={[0.23, 0.56, 4, 10]} /><meshStandardMaterial color="#efb646" /></mesh>
    <mesh position={[0, 1.11, 0]} castShadow><sphereGeometry args={[0.24, 16, 16]} /><meshStandardMaterial color="#1e3b48" /></mesh>
    <mesh position={[0, 0.02, 0]} rotation={[-Math.PI / 2, 0, 0]}><ringGeometry args={[0.36, 0.49, 28]} /><meshBasicMaterial color="#db8c21" side={2} /></mesh>
  </group>
}

class SceneErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false }
  static getDerivedStateFromError() { return { failed: true } }
  render() { return this.state.failed ? <div className="canvas-fallback">3D view could not start. Use the shelf slot buttons to plan the layout.</div> : this.props.children }
}

function SceneContents({ demo, assignments, selected, onSelect, view, route, simulation, playbackClock, playing, activeSku }: Props) {
  const size = demo.meta.cell_size_m
  const width = demo.layout.width * size
  const depth = demo.layout.height * size
  const world = (cell: Cell): [number, number, number] => [(cell[0] + 0.5) * size - width / 2, 0, (cell[1] + 0.5) * size - depth / 2]
  const dock = world(demo.layout.dock)
  const center: [number, number, number] = [0, 0, 0]
  const routePoints = route?.waypoints.map(cell => { const [x, , z] = world(cell); return [x, 0.1, z] as [number, number, number] }) ?? []
  const productMap = new Map(demo.products.map(product => [product.sku, product]))
  const fastMoverCutoff = [...demo.products].sort((a, b) => b.pick_frequency - a.pick_frequency)[Math.max(0, Math.ceil(demo.products.length / 4) - 1)]?.pick_frequency ?? Infinity

  return <>
    <color attach="background" args={['#dce5e8']} />
    <ambientLight intensity={2.1} />
    <directionalLight position={[9, 18, 8]} intensity={2.7} castShadow shadow-mapSize={[2048, 2048]} />
    <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.055, 0]} receiveShadow>
      <planeGeometry args={[width + size * 3, depth + size * 3]} />
      <meshStandardMaterial color="#d6e0e3" />
    </mesh>
    <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.03, 0]} receiveShadow>
      <planeGeometry args={[width, depth]} />
      <meshStandardMaterial color="#edf2f3" />
    </mesh>
    <Grid position={[0, -0.016, 0]} args={[width, depth]} cellSize={size} cellThickness={0.75} cellColor="#a9bbbf" sectionSize={size * 2} sectionThickness={0.9} sectionColor="#a9bbbf" fadeDistance={150} infiniteGrid={false} />
    {demo.layout.walkable_cells.map(([x, z]) => {
      const p = world([x, z])
      return <mesh key={`${x}-${z}`} rotation={[-Math.PI / 2, 0, 0]} position={[p[0], 0.001, p[2]]}>
        <planeGeometry args={[size * 0.94, size * 0.94]} />
        <meshBasicMaterial color={z % 2 ? '#e3eaec' : '#f4f7f7'} transparent opacity={0.58} />
      </mesh>
    })}
    {demo.layout.slots.map(slot => {
      const p = world(slot.rack_cell)
      const sku = assignments[slot.slot_id]
      const active = selected === slot.slot_id || sku === activeSku
      const steel = active ? '#c27b22' : (productMap.get(sku)?.pick_frequency ?? 0) >= fastMoverCutoff ? '#315d69' : '#78939c'
      return <group key={slot.slot_id} position={[p[0], 0, p[2]]} onClick={(event) => { event.stopPropagation(); onSelect(slot.slot_id) }} onPointerOver={() => { document.body.style.cursor = 'pointer' }} onPointerOut={() => { document.body.style.cursor = '' }}>
        <mesh position={[0, 0.75, 0]}><boxGeometry args={[size * 0.81, 1.5, size * 0.76]} /><meshBasicMaterial transparent opacity={0} depthWrite={false} /></mesh>
        {[-1, 1].map(side => <mesh key={side} castShadow position={[side * size * 0.38, 0.75, 0]}><boxGeometry args={[0.09, 1.5, size * 0.74]} /><meshStandardMaterial color={steel} /></mesh>)}
        {[0.18, 0.77, 1.43].map(y => <mesh key={y} castShadow receiveShadow position={[0, y, 0]}><boxGeometry args={[size * 0.81, 0.08, size * 0.76]} /><meshStandardMaterial color={steel} /></mesh>)}
        <mesh castShadow position={[-size * 0.16, 0.48, 0]}><boxGeometry args={[size * 0.3, 0.46, size * 0.4]} /><meshStandardMaterial color={active ? '#eab65e' : '#b99d71'} /></mesh>
        <mesh castShadow position={[size * 0.18, 1.06, 0]}><boxGeometry args={[size * 0.34, 0.47, size * 0.38]} /><meshStandardMaterial color={active ? '#f1c981' : '#d3ba8d'} /></mesh>
      </group>
    })}
    <mesh position={[dock[0], 0.03, dock[2]]} rotation={[-Math.PI / 2, 0, 0]}><planeGeometry args={[size * 0.89, size * 0.89]} /><meshBasicMaterial color="#bc772b" /></mesh>
    {routePoints.length > 1 && <Line points={routePoints} color="#d98a26" lineWidth={4} />}
    <Picker dock={demo.layout.dock} simulation={simulation} playbackClock={playbackClock} playing={playing} size={size} width={width} depth={depth} />
    <CameraControls view={view} target={center} span={Math.max(width, depth)} />
  </>
}

export function WarehouseScene(props: Props) {
  return <SceneErrorBoundary><Canvas shadows dpr={[1, 1.6]} camera={{ position: [14, 18, 18], fov: 44 }} gl={{ antialias: true }} aria-label="3D warehouse floor with selectable rack slots" fallback={<div className="canvas-fallback">3D view is unavailable. Use the shelf slot buttons to plan the layout.</div>}>
    <SceneContents {...props} />
  </Canvas></SceneErrorBoundary>
}
