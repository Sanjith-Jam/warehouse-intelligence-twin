import type { Demo, Policy, Simulation } from './types.ts'
import { validateDemo, validateSimulation } from './model'

const base = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '')

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${base}${path}`, { ...init, signal: AbortSignal.timeout(25000) })
  } catch (cause) {
    if (cause instanceof Error && cause.name === 'TimeoutError') throw new Error('The backend did not respond within 25 seconds.')
    throw new Error('Could not connect to the backend.')
  }
  if (!response.ok) {
    let reason = `Server returned ${response.status}`
    try {
      const body = await response.json() as { detail?: string | unknown[] }
      if (typeof body.detail === 'string') reason = body.detail
    } catch { /* Keep status text when the response is not JSON. */ }
    throw new Error(reason)
  }
  return response.json() as Promise<T>
}

export async function loadDemo(): Promise<Demo> {
  const demo = await request<Demo>('/api/demo')
  if (!validateDemo(demo)) throw new Error('The demo response is incomplete or invalid.')
  return demo
}

export async function compare(demo: Demo, assignments: Record<string, string>, speed: number): Promise<Record<Policy, Simulation>> {
  // The ordered selection and player mapping are copied once for this comparison run.
  const order_ids = demo.orders.map(order => order.order_id)
  const slot_assignments = { ...assignments }
  const policies: Policy[] = ['original', 'baseline', 'player']
  const results = await Promise.all(policies.map(policy => request<Simulation>('/api/simulate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ order_ids, slot_assignments, policy, speed_mps: speed }),
  })))
  for (let i = 0; i < policies.length; i++) {
    const result = results[i]
    if (!validateSimulation(demo, result, policies[i], order_ids, slot_assignments, speed)) {
      throw new Error('The simulation response does not match this order snapshot or warehouse layout.')
    }
  }
  return { original: results[0], baseline: results[1], player: results[2] }
}
