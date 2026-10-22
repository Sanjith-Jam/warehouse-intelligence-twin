import { useCallback, useEffect, useRef, useState } from 'react'
import { compare, loadDemo, loadStaticDemo } from './api'
import { originalAssignments, samplePlayback, swapAssignments } from './model'
import { preview } from './preview'
import { WarehouseScene } from './scene/WarehouseScene'
import type { Demo, Policy, Simulation } from './types'

const SPEED = 1.2
const fmt = (value: number, digits = 1) => new Intl.NumberFormat('en', { maximumFractionDigits: digits }).format(value)
const clock = (seconds: number) => `${String(Math.floor(seconds / 60)).padStart(2, '0')}:${String(Math.floor(seconds % 60)).padStart(2, '0')}`
const policyLabel: Record<Policy, string> = { original: 'Original', baseline: 'Fast-mover baseline', player: 'Your layout' }

export default function App() {
  const [demo, setDemo] = useState<Demo>(preview)
  const [offline, setOffline] = useState(true)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [assignments, setAssignments] = useState<Record<string, string>>(() => originalAssignments(preview))
  const [selected, setSelected] = useState<string | null>(null)
  const [comparison, setComparison] = useState<Record<Policy, Simulation> | null>(null)
  const [comparing, setComparing] = useState(false)
  const [policy, setPolicy] = useState<Policy>('player')
  const [view, setView] = useState<'iso' | 'top'>('iso')
  const [cameraReset, setCameraReset] = useState(0)
  const [elapsed, setElapsed] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [query, setQuery] = useState('')
  const [tab, setTab] = useState<'products' | 'orders'>('products')
  const refreshId = useRef(0)
  const comparisonId = useRef(0)
  const playbackClock = useRef(0)

  const refresh = useCallback(async () => {
    const token = ++refreshId.current
    comparisonId.current++
    setLoading(true)
    setComparing(false)
    setComparison(null)
    setSelected(null)
    setPlaying(false)
    playbackClock.current = 0
    setElapsed(0)
    setError('')
    try {
      const next = await loadDemo()
      if (token !== refreshId.current) return
      setDemo(next)
      setAssignments(originalAssignments(next))
      setOffline(false)
    } catch (cause) {
      if (token !== refreshId.current) return
      const staticDemo = await loadStaticDemo().catch(() => null)
      if (token !== refreshId.current) return
      setOffline(true)
      setDemo(staticDemo ?? preview)
      setAssignments(originalAssignments(staticDemo ?? preview))
      setError(cause instanceof Error ? cause.message : 'Could not reach the backend.')
    } finally {
      if (token === refreshId.current) setLoading(false)
    }
  }, [])

  useEffect(() => { void refresh(); return () => { refreshId.current++; comparisonId.current++ } }, [refresh])

  const invalidate = () => {
    comparisonId.current++
    setComparison(null)
    setPlaying(false)
    playbackClock.current = 0
    setElapsed(0)
    setError('')
    setComparing(false)
  }

  const chooseSlot = (slotId: string) => {
    if (loading) return
    if (!selected) { setSelected(slotId); return }
    if (selected === slotId) { setSelected(null); return }
    setAssignments(current => swapAssignments(current, selected, slotId))
    setSelected(null)
    invalidate()
  }

  const runComparison = async () => {
    if (offline || loading || comparing) return
    const token = ++comparisonId.current
    setComparing(true)
    setComparison(null)
    setPlaying(false)
    playbackClock.current = 0
    setElapsed(0)
    setError('')
    try {
      const result = await compare(demo, assignments, SPEED)
      if (token !== comparisonId.current) return
      setComparison(result)
      setPolicy('player')
      setPlaying(!window.matchMedia('(prefers-reduced-motion: reduce)').matches)
    } catch (cause) {
      if (token === comparisonId.current) setError(cause instanceof Error ? cause.message : 'Comparison failed.')
    } finally {
      if (token === comparisonId.current) setComparing(false)
    }
  }

  const active = comparison?.[policy]
  const sample = active ? samplePlayback(active, demo.meta.cell_size_m, elapsed) : null
  const currentRoute = active?.routes.find(route => route.order_id === sample?.order_id) ?? active?.routes[0] ?? null
  const sceneAssignments = active?.slot_assignments ?? assignments
  const productBySku = new Map(demo.products.map(product => [product.sku, product]))
  const selectedSlot = demo.layout.slots.find(slot => slot.slot_id === selected)
  const filteredSlots = demo.layout.slots.filter(slot => `${slot.slot_id} ${assignments[slot.slot_id]} ${productBySku.get(assignments[slot.slot_id])?.name ?? ''}`.toLowerCase().includes(query.toLowerCase()))
  const dirty = demo.layout.slots.some(slot => assignments[slot.slot_id] !== slot.sku)
  const currentOrderIndex = sample ? demo.orders.findIndex(order => order.order_id === sample.order_id) + 1 : 0

  useEffect(() => {
    if (!playing || !active) return
    const timer = window.setInterval(() => setElapsed(playbackClock.current), 100)
    return () => window.clearInterval(timer)
  }, [playing, active])
  useEffect(() => { if (sample?.done && playing) setPlaying(false) }, [sample?.done, playing])

  const changePolicy = (next: Policy) => { setPolicy(next); playbackClock.current = 0; setElapsed(0); setPlaying(false) }
  const resetLayout = () => { if (loading) return; invalidate(); setAssignments(originalAssignments(demo)); setSelected(null) }
  const resetReplay = () => { setPlaying(false); playbackClock.current = 0; setElapsed(0) }

  return <div className="app-shell">
    <header className="topbar">
      <div className="brand"><span className="brand-symbol" aria-hidden="true"><i /><i /><i /></span><div><strong>WAREHOUSE <span>INTELLIGENCE</span></strong><small>DIGITAL TWIN / OPERATIONS</small></div></div>
      <div className="header-center"><span className="header-label">ACTIVE FLOOR</span><strong>01 / Picking operations</strong></div>
      <div className="header-status"><span className={`status-dot ${offline ? 'offline' : ''}`} /><span>{offline ? 'Preview mode' : 'Simulation connected'}</span><span className="header-rule" /><span className="header-dataset">{demo.meta.month ?? 'SYNTHETIC'} · {demo.meta.source}</span></div>
    </header>

    <main className="console">
      <div className="console-heading"><div><span className="eyebrow">WORKSPACE / PS 4.2</span><h1>Slotting operations</h1></div><p>Reassign stock. Replay the same orders. Measure each route.</p><span className={`data-badge ${demo.meta.real_order_data ? 'real' : ''}`}>{demo.meta.real_order_data ? 'REAL ORDER SNAPSHOT' : 'SYNTHETIC ORDER FIXTURE'}</span></div>

      {offline && <div className="notice" role="status"><div><strong>Backend not connected. Scene preview only.</strong><span>Slot changes are local; comparison needs the simulation API.</span>{error && <small>{error}</small>}</div><button className="button outline" onClick={() => void refresh()} disabled={loading}>{loading ? 'Checking…' : 'Retry connection'}</button></div>}
      {!offline && error && <div className="notice error" role="alert"><span>{error}</span><button className="button outline" onClick={() => setError('')}>Dismiss</button></div>}

      <section className="comparison-strip" aria-label="Layout comparison">
        {(['original', 'baseline', 'player'] as const).map(item => {
          const result = comparison?.[item]
          return <article className={`comparison-card ${comparison && policy === item ? 'current' : ''}`} key={item}>
            <div className="comparison-title"><span className="comparison-marker" /><span>{policyLabel[item]}</span>{comparison && <button onClick={() => changePolicy(item)} aria-label={`Inspect ${item} route`} aria-pressed={policy === item}>Inspect route ↗</button>}</div>
            <div className="comparison-value"><strong>{result ? fmt(result.distance_m) : '—'}</strong><span>m walked</span></div>
            <p>{result ? `${fmt(result.average_pick_time_s)} s / order average` : 'Awaiting simulation'}</p>
          </article>
        })}
        <div className="comparison-context"><strong>{demo.orders.length}</strong><span>ORDERS<br/>IN REPLAY</span><strong>{demo.layout.slots.length}</strong><span>ACTIVE<br/>SLOTS</span></div>
      </section>

      <div className="workspace-grid">
        <section className="floor-card" aria-labelledby="floor-title">
          <div className="floor-toolbar"><div><span className="section-index">WAREHOUSE / SPATIAL VIEW</span><h2 id="floor-title">Picking floor <span>· {demo.layout.width} × {demo.layout.height} grid</span></h2></div><div className="floor-tools"><div className="view-control" role="group" aria-label="Camera view"><button className={view === 'iso' ? 'active' : ''} onClick={() => setView('iso')} aria-pressed={view === 'iso'}>Isometric</button><button className={view === 'top' ? 'active' : ''} onClick={() => setView('top')} aria-pressed={view === 'top'}>Top view</button></div><button className="icon-button" onClick={() => setCameraReset(value => value + 1)} aria-label="Reset camera" title="Reset camera">⌖</button></div></div>
          <div className="scene-frame"><WarehouseScene demo={demo} assignments={sceneAssignments} selected={selected} onSelect={chooseSlot} view={view} cameraReset={cameraReset} route={currentRoute} simulation={active ?? null} playbackClock={playbackClock} playing={playing} activeSku={sample?.sku ?? null} /><div className="scene-hud"><span className="hud-live"><i /> {offline ? 'FLOOR PREVIEW' : 'SIMULATED FLOOR'}</span><span>{demo.meta.synthetic_warehouse ? 'SYNTHETIC GEOMETRY' : 'WAREHOUSE GEOMETRY'}</span></div><div className="scene-legend"><span><i className="legend-rack" /> HIGH PICK RATE</span><span><i className="legend-path" /> PICK ROUTE</span><span><i className="legend-dock" /> DOCK</span></div><div className="scene-hint">DRAG TO ORBIT / SCROLL TO ZOOM</div></div>
          <div className="playback-console"><div className="playback-top"><div className="playback-state"><span className="section-index">PICKER REPLAY <b>· 6× VIEW SPEED</b></span><strong>{active ? sample?.handling ? `Handling ${sample.sku}` : sample?.done ? 'Route complete' : `Walking · ${sample?.order_id}` : 'Run a comparison to inspect a route'}</strong></div><div className="playback-live"><span>ORDER <b>{currentOrderIndex || '—'} / {demo.orders.length}</b></span><span>DISTANCE <b>{active ? `${fmt(sample?.distance_m ?? 0)} / ${fmt(active.distance_m)} m` : '—'}</b></span><span>TIME <b>{active ? `${clock(sample?.time_s ?? 0)} / ${clock(active.estimated_pick_time_s)}` : '—'}</b></span></div></div>
            <div className="timeline"><label htmlFor="route-position">Route timeline</label><input id="route-position" aria-label="Replay position" type="range" min="0" max={active?.estimated_pick_time_s ?? 1} step="0.1" value={Math.min(elapsed, active?.estimated_pick_time_s ?? 1)} disabled={!active} onChange={event => { const next = Number(event.target.value); setPlaying(false); playbackClock.current = next; setElapsed(next) }} /><span>{active ? `${Math.round(elapsed / active.estimated_pick_time_s * 100)}%` : '0%'}</span></div>
            <div className="playback-actions"><span>{active ? `${policyLabel[policy]} · ${active.routes.length} returned routes` : 'Routes follow walkable aisle cells and return to dock.'}</span><div><button className="button outline" disabled={!active} onClick={() => { if (sample?.done) { playbackClock.current = 0; setElapsed(0) } else if (playing) setElapsed(playbackClock.current); setPlaying(!playing) }}>{playing ? 'Pause' : sample?.done ? 'Replay' : 'Play'}</button><button className="button subtle" disabled={!active} onClick={resetReplay}>Reset replay</button></div></div>
          </div>
        </section>

        <aside className="planning-rail" aria-label="Slot planning controls">
          <div className="rail-heading"><div><span className="section-index">SLOT PLANNER</span><h2>Move the fast movers.</h2></div><p>Choose two occupied locations to swap their products.</p></div>
          <div className="selected-readout"><span>SELECTED LOCATION</span><strong>{selected ?? 'No slot selected'}</strong><small>{selectedSlot ? `${assignments[selectedSlot.slot_id]} · ${productBySku.get(assignments[selectedSlot.slot_id])?.name ?? 'Product'}` : 'Select from the floor or stock list'}</small></div>
          <div className="rail-actions"><button className="button primary" onClick={() => void runComparison()} disabled={offline || loading || comparing} aria-busy={comparing}>{comparing ? 'Calculating routes…' : 'Replay & compare'}</button><button className="button subtle" onClick={resetLayout} disabled={loading || (!dirty && !comparison)}>Reset layout</button></div>
          <p className="rail-state"><i className={dirty ? 'modified' : ''} /> {dirty ? 'Layout modified · compare to score' : 'Original slot arrangement'}{offline ? ' · API required' : ''}</p>
          <div className="rail-tabs" role="group" aria-label="Inventory view"><button onClick={() => setTab('products')} aria-pressed={tab === 'products'}>Products <span>{demo.products.length}</span></button><button onClick={() => setTab('orders')} aria-pressed={tab === 'orders'}>Orders <span>{demo.orders.length}</span></button></div>
          {tab === 'products' ? <div className="rail-list-section"><label className="search-label" htmlFor="stock-search">FIND PRODUCT OR SLOT</label><input id="stock-search" value={query} onChange={event => setQuery(event.target.value)} placeholder="Search SKU, name, slot…" /><div className="rail-list" aria-label="Shelf slots">{filteredSlots.map(slot => { const product = productBySku.get(assignments[slot.slot_id]); return <button key={slot.slot_id} className={`stock-row ${selected === slot.slot_id ? 'selected' : ''} ${assignments[slot.slot_id] !== slot.sku ? 'changed' : ''}`} aria-label={`${slot.slot_id} ${product?.name ?? assignments[slot.slot_id]}`} aria-pressed={selected === slot.slot_id} disabled={loading} onClick={() => chooseSlot(slot.slot_id)}><span className="stock-code">{slot.slot_id}</span><span className="stock-detail"><strong>{product?.name ?? assignments[slot.slot_id]}</strong><small>{assignments[slot.slot_id]}</small></span><span className="stock-picks">{fmt(product?.pick_frequency ?? 0, 0)}<small>picks</small></span></button> })}{filteredSlots.length === 0 && <p className="empty-state">No stock matches “{query}”.</p>}</div></div> : <div className="rail-list orders-list">{demo.orders.map(order => <article key={order.order_id}><div><strong>{order.order_id}</strong><span>{order.lines.length} lines</span></div><p>{order.lines.map(line => `${line.sku} × ${line.quantity}`).join(' · ')}</p></article>)}</div>}
          <div className="rail-foot">MONTHLY PICK RATE · {demo.meta.real_order_data ? 'RETAINED UCI ORDER LINES' : 'SYNTHETIC PREVIEW VALUES'}</div>
        </aside>
      </div>

      <div className="console-footer"><span>DATASET {demo.meta.dataset_id}</span><span>{demo.meta.real_order_data ? 'UCI ONLINE RETAIL II ORDERS' : 'SYNTHETIC FIXTURE · NO MEASURED KPIs'}</span><span>1 CELL = {fmt(demo.meta.cell_size_m)} M · SPEED {fmt(SPEED)} M/S · HANDLING 10 S/LINE</span></div>
      {active?.warnings.length ? <p className="warning-note" role="status">{active.warnings.join(' · ')}</p> : null}
    </main>
  </div>
}
