import { useCallback, useEffect, useRef, useState } from 'react'
import { compare, loadDemo } from './api'
import { originalAssignments, samplePlayback, swapAssignments } from './model'
import { preview } from './preview'
import { WarehouseScene } from './scene/WarehouseScene'
import type { Demo, Policy, Simulation } from './types'

const SPEED = 1.2
const fmt = (n: number, digits = 1) => new Intl.NumberFormat('en', { maximumFractionDigits: digits }).format(n)

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
      setSelected(null)
      setComparison(null)
      setElapsed(0)
      playbackClock.current = 0
      setPlaying(false)
      setOffline(false)
    } catch (cause) {
      if (token !== refreshId.current) return
      setOffline(true)
      setDemo(preview)
      setAssignments(originalAssignments(preview))
      setComparison(null)
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
    if (offline || comparing) return
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
  const selectedSlot = demo.layout.slots.find(slot => slot.slot_id === selected)
  const productBySku = new Map(demo.products.map(product => [product.sku, product]))
  const filteredProducts = demo.products.filter(product => `${product.sku} ${product.name}`.toLowerCase().includes(query.toLowerCase()))
  const productSlot = (sku: string) => Object.entries(assignments).find(([, value]) => value === sku)?.[0]
  const dirty = demo.layout.slots.some(slot => assignments[slot.slot_id] !== slot.sku)

  useEffect(() => {
    if (!playing || !active) return
    const timer = window.setInterval(() => {
      setElapsed(playbackClock.current)
    }, 100)
    return () => window.clearInterval(timer)
  }, [playing, active])

  useEffect(() => {
    if (sample?.done && playing) setPlaying(false)
  }, [sample?.done, playing])

  const changePolicy = (next: Policy) => { setPolicy(next); playbackClock.current = 0; setElapsed(0); setPlaying(false) }
  const resetLayout = () => { if (loading) return; invalidate(); setAssignments(originalAssignments(demo)); setSelected(null) }

  return <div className="app-shell">
    <header className="topbar">
      <div className="brand"><div className="brand-symbol" aria-hidden="true"><span /><span /><span /></div><div><strong>WAREHOUSE<span> / </span>INTELLIGENCE</strong><small>DIGITAL TWIN · SLOT PLANNING</small></div></div>
      <div className="topbar-right"><span className={`status-dot ${offline ? 'offline' : ''}`} /> <span>{offline ? 'Preview mode' : 'Simulation connected'}</span><span className="top-divider" /> <span className="top-meta">PS 4.2 / OPERATIONS LAB</span></div>
    </header>

    <main className="main-content">
      <section className="intro" aria-labelledby="page-title">
        <div><p className="eyebrow">WAREHOUSE INTELLIGENCE TWIN <span>—</span> FLOOR 01</p><h1 id="page-title">Plan the floor.<br/><em>Prove the route.</em></h1><p className="intro-copy">Swap products between shelf slots, replay the same orders, and see how walking distance changes.</p></div>
        <div className="dataset-stamp"><span className="stamp-label">DATA SNAPSHOT</span><strong>{demo.meta.month ?? 'Preview only'}</strong><span>{demo.meta.source}</span><small>{demo.meta.real_order_data ? 'Real retail order lines' : 'Synthetic order fixture'} · Synthetic warehouse geometry</small></div>
      </section>

      {offline && <div className="notice" role="status"><div><strong>Backend unavailable — scene preview only.</strong><span> You can inspect the floor and try swaps. Start the API to calculate routes and compare layouts.</span>{error && <small>Connection: {error}</small>}</div><button className="button outline" onClick={() => void refresh()} disabled={loading}>{loading ? 'Checking…' : 'Retry connection'}</button></div>}
      {!offline && error && <div className="notice error" role="alert"><span>{error}</span><button className="button outline" onClick={() => setError('')}>Dismiss</button></div>}

      <div className="workspace-grid">
        <section className="floor-card" aria-labelledby="floor-title">
          <div className="panel-heading"><div><span className="section-index">01 / FLOOR VIEW</span><h2 id="floor-title">Picking floor</h2></div><div className="view-control" aria-label="Camera view"><button className={view === 'iso' ? 'active' : ''} onClick={() => setView('iso')} aria-pressed={view === 'iso'}>Isometric</button><button className={view === 'top' ? 'active' : ''} onClick={() => setView('top')} aria-pressed={view === 'top'}>Top view</button></div></div>
          <div className="scene-frame"><WarehouseScene demo={demo} assignments={sceneAssignments} selected={selected} onSelect={chooseSlot} view={view} route={currentRoute} simulation={active ?? null} playbackClock={playbackClock} playing={playing} activeSku={sample?.sku ?? null} /><div className="scene-overlay"><span><i className="legend-rack" /> HIGH PICK RATE</span><span><i className="legend-path" /> ROUTE</span><span><i className="legend-dock" /> DOCK</span></div><div className="scene-corner">DRAG TO ORBIT · SCROLL TO ZOOM</div></div>
          <div className="floor-footer"><p><strong>{demo.layout.slots.length} shelf slots</strong><span> · Select two racks to swap their products.</span></p><span>1 CELL = {fmt(demo.meta.cell_size_m)} M</span></div>
        </section>

        <aside className="side-stack">
          <section className="control-card" aria-labelledby="slot-title"><span className="section-index">02 / SLOT PLANNING</span><h2 id="slot-title">Reassign stock</h2><p className="muted">Choose two occupied slots. The products exchange places; routes update when you compare.</p>
            <div className="selected-readout"><span>FIRST SLOT</span><strong>{selected ?? 'Select a slot'}</strong><small>{selectedSlot ? `${assignments[selectedSlot.slot_id]} · ${productBySku.get(assignments[selectedSlot.slot_id])?.name ?? 'Product'}` : 'Select from the floor or list below'}</small></div>
            <div className="slot-grid" aria-label="Shelf slots">{demo.layout.slots.map(slot => <button key={slot.slot_id} className={`slot-button ${selected === slot.slot_id ? 'selected' : ''} ${assignments[slot.slot_id] !== slot.sku ? 'changed' : ''}`} onClick={() => chooseSlot(slot.slot_id)} disabled={loading} aria-pressed={selected === slot.slot_id} title={`${slot.slot_id}: ${productBySku.get(assignments[slot.slot_id])?.name ?? assignments[slot.slot_id]}`}><strong>{slot.slot_id}</strong><span>{productBySku.get(assignments[slot.slot_id])?.name ?? assignments[slot.slot_id]}</span></button>)}</div>
            <div className="control-actions"><button className="button primary" onClick={() => void runComparison()} disabled={offline || loading || comparing} aria-busy={comparing}>{comparing ? 'Calculating routes…' : 'Replay & compare'}</button><button className="button quiet" onClick={resetLayout} disabled={loading || (!dirty && !comparison)}>Reset layout</button></div>
            <small className="control-hint">{dirty ? 'Layout modified · comparison needed' : 'Original slot arrangement'}{offline ? ' · API required for scoring' : ''}</small>
          </section>
        </aside>
      </div>

      <section className="results-section" aria-labelledby="results-title"><div className="section-header"><div><span className="section-index">03 / REPLAY & COMPARE</span><h2 id="results-title">One order set. Three layouts.</h2></div><span className="section-note">{demo.orders.length} orders · {fmt(SPEED)} m/s · same routing rules</span></div>
        <div className="metric-grid">{(['original', 'baseline', 'player'] as const).map(item => { const result = comparison?.[item]; return <article key={item} className={`metric-card ${item === policy && comparison ? 'focused' : ''}`}><div className="metric-card-top"><span>{item === 'original' ? 'ORIGINAL' : item === 'baseline' ? 'FAST-MOVER BASELINE' : 'YOUR LAYOUT'}</span>{comparison && <button onClick={() => changePolicy(item)} aria-label={`Inspect ${item} route`} aria-pressed={policy === item}>VIEW ROUTE ↗</button>}</div><strong>{result ? fmt(result.distance_m) : '—'} <small>{result ? 'm walked' : ''}</small></strong><div className="metric-footer"><span>Average pick time</span><b>{result ? `${fmt(result.average_pick_time_s)} s / order` : 'Awaiting simulation'}</b></div></article> })}</div>
        <div className="replay-strip"><div className="replay-info"><span className="live-indicator" /> <div><strong>{active ? sample?.handling ? `Handling ${sample.sku}` : sample?.done ? 'Replay complete' : `Walking · ${sample?.order_id}` : 'Replay ready when comparison finishes'}</strong><small>{active ? `${fmt(sample?.distance_m ?? 0)} / ${fmt(active.distance_m)} m walked · ${fmt(sample?.time_s ?? 0)} / ${fmt(active.estimated_pick_time_s)} s elapsed · 6× playback` : 'Server routes and metrics appear here.'}</small></div></div><div className="replay-actions"><button className="button outline" disabled={!active} onClick={() => { if (sample?.done) { playbackClock.current = 0; setElapsed(0) } setPlaying(!playing) }}>{playing ? 'Pause' : sample?.done ? 'Replay' : 'Play'}</button><button className="button quiet" disabled={!active} onClick={() => { setPlaying(false); playbackClock.current = 0; setElapsed(0) }}>Reset replay</button></div></div>
        {active?.warnings.length ? <p className="warning-note" role="status">{active.warnings.join(' · ')}</p> : null}
        {comparison && <p className="provenance-note">Results use server-returned routes and assignments for dataset <strong>{demo.meta.dataset_id}</strong>. Estimated time includes {fmt(active?.assumptions.handling_seconds_per_line ?? 0)} s handling per line.</p>}
      </section>

      <section className="inventory-section" aria-labelledby="inventory-title"><div className="section-header"><div><span className="section-index">04 / ORDER SNAPSHOT</span><h2 id="inventory-title">The stock behind the floor.</h2></div><div className="tabs" role="group" aria-label="Inventory view"><button onClick={() => setTab('products')} aria-pressed={tab === 'products'}>Products</button><button onClick={() => setTab('orders')} aria-pressed={tab === 'orders'}>Orders</button></div></div>
        {tab === 'products' ? <><label className="search-label">Find a product <input value={query} onChange={event => setQuery(event.target.value)} placeholder="Search by name or SKU" /></label><div className="table-wrap"><table><caption>Products in the demo snapshot and current shelf assignment</caption><thead><tr><th scope="col">Product</th><th scope="col">SKU</th><th scope="col">Monthly picks</th><th scope="col">Current slot</th><th scope="col">Action</th></tr></thead><tbody>{filteredProducts.map(product => { const slot = productSlot(product.sku); return <tr key={product.sku}><td><strong>{product.name}</strong></td><td className="mono">{product.sku}</td><td>{fmt(product.pick_frequency, 0)}</td><td className="mono">{slot ?? '—'}</td><td><button className="table-action" disabled={!slot} onClick={() => slot && chooseSlot(slot)}>{selected && selected !== slot ? 'Swap here' : selected === slot ? 'Clear' : 'Select slot'}</button></td></tr> })}</tbody></table>{filteredProducts.length === 0 && <p className="empty-state">No products match “{query}”.</p>}</div></> : <div className="orders-list">{demo.orders.map(order => <article key={order.order_id}><strong className="mono">{order.order_id}</strong><span>{order.lines.length} product lines</span><small>{order.lines.map(line => `${line.sku} × ${line.quantity}`).join(' · ')}</small></article>)}</div>}
      </section>
    </main>
    <footer className="footer"><span>WAREHOUSE INTELLIGENCE TWIN</span><span>{demo.meta.real_order_data ? 'UCI Online Retail II order snapshot' : 'Synthetic fixture · no measured KPIs'} / Synthetic floor and movement assumptions</span></footer>
  </div>
}
