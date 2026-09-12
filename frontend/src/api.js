const BASE_URL = 'http://localhost:8000'

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  const data = await res.json().catch(() => null)
  if (!res.ok) {
    const detail = data?.detail
    const message = (detail && detail.message) || detail || 'Request failed'
    const error = new Error(message)
    error.payload = data
    throw error
  }
  return data
}

export const api = {
  getStatus: () => request('/status'),
  createAppliance: (appliance) =>
    request('/appliances', { method: 'POST', body: JSON.stringify(appliance) }),
  deleteAppliance: (id) => request(`/appliances/${id}`, { method: 'DELETE' }),
  turnOn: (id) => request(`/appliances/${id}/on`, { method: 'POST' }),
  turnOff: (id) => request(`/appliances/${id}/off`, { method: 'POST' }),
  getEvents: () => request('/events'),
}