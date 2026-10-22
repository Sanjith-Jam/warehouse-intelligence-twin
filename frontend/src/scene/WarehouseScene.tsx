import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { Grid, Line, OrbitControls } from '@react-three/drei'
import { Component, useEffect, useLayoutEffect, useRef } from 'react'
import type { ReactNode, RefObject } from 'react'
import { Color, Object3D } from 'three'
import type { Group, InstancedMesh } from 'three'
import type { OrbitControls as OrbitControlsImpl } from 'three-stdlib'
import type { Cell, Demo, Simulation } from '../types'
import { samplePlayback } from '../model'
import { RackFleet } from './RackFleet'

type Props = {
  demo: Demo
  assignments: Record<string, string>
  selected: string | null
  onSelect: (slotId: string) => void
  view: 'iso' | 'top'
  cameraReset: number
  route: Simulation['routes'][number] | null
  simulation: Simulation | null
  playbackClock: RefObject<number>
  playing: boolean
  activeSku: string | null
}

function CameraControls({ view, reset, target, width, depth }: { view: Props['view']; reset: number; target: [number, number, number]; width: number; depth: number }) {
  const control = useRef<OrbitControlsImpl>(null)
  const aspect = useThree(state => state.size.width / Math.max(1, state.size.height))
  useEffect(() => {
    const c = control.current
    if (!c) return
    const distance = Math.max(width / (aspect * 0.72), depth * (view === 'top' ? 1.5 : 1.25), 12)
    c.object.up.set(0, view === 'top' ? 0 : 1, view === 'top' ? -1 : 0)
    c.object.position.set(view === 'top' ? target[0] : target[0] - distance * 0.24, view === 'top' ? distance * 1.05 : distance * 0.9, view === 'top' ? target[2] + 0.01 : target[2] - distance * 0.86)
    c.target.set(...target)
    c.update()
  }, [view, reset, target[0], target[1], target[2], width, depth, aspect])
  return <OrbitControls ref={control} target={target} minDistance={6} maxDistance={Math.max(width, depth) * 4} maxPolarAngle={Math.PI / 2.04} enableDamping />
}

function WalkableFloor({ cells, size, width, depth }: { cells: Cell[]; size: number; width: number; depth: number }) {
  const ref = useRef<InstancedMesh>(null)
  useLayoutEffect(() => {
    if (!ref.current) return
    const dummy = new Object3D()
    const color = new Color()
    cells.forEach(([x, z], index) => {
      dummy.position.set((x + 0.5) * size - width / 2, 0.015, (z + 0.5) * size - depth / 2)
      dummy.rotation.set(-Math.PI / 2, 0, 0)
      dummy.scale.set(size * 0.94, size * 0.94, 1)
      dummy.updateMatrix()
      ref.current!.setMatrixAt(index, dummy.matrix)
      ref.current!.setColorAt(index, color.set(x === 0 || z === 0 ? '#dbe9e9' : '#f0f2ed'))
    })
    ref.current.instanceMatrix.needsUpdate = true
    if (ref.current.instanceColor) ref.current.instanceColor.needsUpdate = true
    ref.current.computeBoundingSphere()
  }, [cells, size, width, depth])
  return <instancedMesh ref={ref} args={[undefined, undefined, cells.length]} receiveShadow frustumCulled={false}><planeGeometry /><meshStandardMaterial color="#ffffff" roughness={1} /></instancedMesh>
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

function SceneContents({ demo, assignments, selected, onSelect, view, cameraReset, route, simulation, playbackClock, playing, activeSku }: Props) {
  const size = demo.meta.cell_size_m
  const width = demo.layout.width * size
  const depth = demo.layout.height * size
  const world = (cell: Cell): [number, number, number] => [(cell[0] + 0.5) * size - width / 2, 0, (cell[1] + 0.5) * size - depth / 2]
  const dock = world(demo.layout.dock)
  const center: [number, number, number] = [0, 0, 0]
  const routePoints = route?.waypoints.map(cell => { const [x, , z] = world(cell); return [x, 0.1, z] as [number, number, number] }) ?? []
  const selectedSlot = demo.layout.slots.find(slot => slot.slot_id === selected)
  const selectedPoint = selectedSlot ? world(selectedSlot.rack_cell) : null

  return <>
    <color attach="background" args={['#c9d7d9']} />
    <ambientLight intensity={1.25} color="#dce8e9" />
    <hemisphereLight args={['#f3f5ef', '#7b9297', 1.1]} />
    <directionalLight position={[-width * 0.3, 24, -depth * 0.35]} intensity={2.6} castShadow shadow-mapSize={[2048, 2048]} shadow-camera-left={-Math.max(width, depth)} shadow-camera-right={Math.max(width, depth)} shadow-camera-top={Math.max(width, depth)} shadow-camera-bottom={-Math.max(width, depth)} shadow-camera-near={1} shadow-camera-far={80} />
    <mesh position={[0, -0.28, 0]} receiveShadow><boxGeometry args={[width + size * 1.7, 0.4, depth + size * 1.7]} /><meshStandardMaterial color="#9db0b5" roughness={1} /></mesh>
    <mesh position={[0, -0.04, 0]} receiveShadow><boxGeometry args={[width + size * 0.18, 0.09, depth + size * 0.18]} /><meshStandardMaterial color="#d9dfdd" roughness={1} /></mesh>
    <Grid position={[0, 0.008, 0]} args={[width, depth]} cellSize={size} cellThickness={0.55} cellColor="#aebdc0" sectionSize={size * 2} sectionThickness={0.8} sectionColor="#97aab0" fadeDistance={200} infiniteGrid={false} />
    <WalkableFloor cells={demo.layout.walkable_cells} size={size} width={width} depth={depth} />
    <mesh position={[0, 1.35, depth / 2 + 0.21]} castShadow><boxGeometry args={[width + size * 0.55, 2.7, 0.32]} /><meshStandardMaterial color="#9eb5bb" roughness={0.85} /></mesh>
    <mesh position={[width / 2 + 0.21, 1.35, 0]} castShadow><boxGeometry args={[0.32, 2.7, depth + size * 0.55]} /><meshStandardMaterial color="#a9bdc1" roughness={0.85} /></mesh>
    <mesh position={[0, 2.72, depth / 2 + 0.19]}><boxGeometry args={[width + size * 0.6, 0.16, 0.4]} /><meshStandardMaterial color="#4c6873" /></mesh>
    <mesh position={[width / 2 + 0.19, 2.72, 0]}><boxGeometry args={[0.4, 0.16, depth + size * 0.6]} /><meshStandardMaterial color="#4c6873" /></mesh>
    <mesh position={[0, 0.13, -depth / 2 - 0.14]}><boxGeometry args={[width + size * 0.35, 0.26, 0.25]} /><meshStandardMaterial color="#607e87" /></mesh>
    <mesh position={[-width / 2 - 0.14, 0.13, 0]}><boxGeometry args={[0.25, 0.26, depth + size * 0.35]} /><meshStandardMaterial color="#607e87" /></mesh>
    <RackFleet slots={demo.layout.slots} products={demo.products} assignments={assignments} selected={selected} activeSku={activeSku} size={size} width={width} depth={depth} onSelect={onSelect} />
    <group position={[dock[0], 0.04, dock[2]]}>
      <mesh rotation={[-Math.PI / 2, 0, 0]}><planeGeometry args={[size * 0.94, size * 0.94]} /><meshBasicMaterial color="#d39333" /></mesh>
      <mesh position={[0, 0.025, 0]} rotation={[-Math.PI / 2, 0, 0]}><ringGeometry args={[size * 0.2, size * 0.27, 4]} /><meshBasicMaterial color="#fff3d6" side={2} /></mesh>
    </group>
    {selectedPoint && <mesh position={[selectedPoint[0], 0.06, selectedPoint[2]]} rotation={[-Math.PI / 2, 0, 0]}><ringGeometry args={[size * 0.47, size * 0.55, 4]} /><meshBasicMaterial color="#0f9db6" side={2} /></mesh>}
    {routePoints.length > 1 && <Line points={routePoints} color="#078eac" lineWidth={4} />}
    <Picker dock={demo.layout.dock} simulation={simulation} playbackClock={playbackClock} playing={playing} size={size} width={width} depth={depth} />
    <CameraControls view={view} reset={cameraReset} target={center} width={width} depth={depth} />
  </>
}

export function WarehouseScene(props: Props) {
  return <SceneErrorBoundary><Canvas shadows dpr={[1, 1.6]} camera={{ position: [14, 18, 18], fov: 44 }} gl={{ antialias: true }} aria-label="3D warehouse floor with selectable rack slots" fallback={<div className="canvas-fallback">3D view is unavailable. Use the shelf slot buttons to plan the layout.</div>}>
    <SceneContents {...props} />
  </Canvas></SceneErrorBoundary>
}
