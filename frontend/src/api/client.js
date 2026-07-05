const jsonHeaders = { 'Content-Type': 'application/json' }

async function request(path, options = {}) {
  const response = await fetch(path, options)
  const payload = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error(payload.detail || `Request failed: ${response.status}`)
  }
  return payload
}

export const api = {
  getSummary: () => request('/api/crew/summary'),
  getAgents: () => request('/api/agents'),
  getAgent: (filename) => request(`/api/agents/${encodeURIComponent(filename)}`),
  saveAgent: (filename, content) =>
    request(`/api/agents/${encodeURIComponent(filename)}`, {
      method: 'PUT',
      headers: jsonHeaders,
      body: JSON.stringify({ content })
    }),
  deleteAgent: (filename) => request(`/api/agents/${encodeURIComponent(filename)}`, { method: 'DELETE' }),
  getTasks: () => request('/api/tasks'),
  saveTasks: (tasks) =>
    request('/api/tasks', {
      method: 'PUT',
      headers: jsonHeaders,
      body: JSON.stringify({ tasks })
    }),
  getCrewConfig: () => request('/api/crew/config'),
  updateInputs: (inputs) =>
    request('/api/crew/inputs', {
      method: 'PATCH',
      headers: jsonHeaders,
      body: JSON.stringify({ inputs })
    }),
  getModelConfig: () => request('/api/models/config'),
  updateAgentModels: (llm) =>
    request('/api/models/agents', {
      method: 'PATCH',
      headers: jsonHeaders,
      body: JSON.stringify({ llm })
    }),
  getOutputs: () => request('/api/outputs'),
  getOutputContent: (path) => request(`/api/outputs/content?path=${encodeURIComponent(path)}`),
  startRun: () => request('/api/runs', { method: 'POST' }),
  getRuns: () => request('/api/runs'),
  getRun: (id) => request(`/api/runs/${id}`)
}

export function connectRunLogs(runId, onMessage) {
  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
  const socket = new WebSocket(`${protocol}://${window.location.host}/ws/runs/${runId}/logs`)
  socket.addEventListener('message', (event) => onMessage(event.data))
  return socket
}
