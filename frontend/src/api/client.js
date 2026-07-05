const jsonHeaders = { 'Content-Type': 'application/json' }

async function request(path, options = {}) {
  const response = await fetch(path, options)
  const payload = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error(payload.detail || `请求失败，状态码：${response.status}`)
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
  getSettings: () => request('/api/settings'),
  saveSettings: (crewProjectPath) =>
    request('/api/settings', {
      method: 'PUT',
      headers: jsonHeaders,
      body: JSON.stringify({ crew_project_path: crewProjectPath })
    }),
  getHealth: () => request('/api/health'),
  startRun: () => request('/api/runs', { method: 'POST' }),
  getRuns: () => request('/api/runs'),
  getRun: (id) => request(`/api/runs/${id}`)
}

export function simplifyLogText(logText) {
  const summary = ['正在启动生产线']
  const keywords = ['task', 'agent', 'success', 'failed', 'error', 'output', 'finished', 'completed', 'writing']
  String(logText || '')
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => {
      const lower = line.toLowerCase()
      return line && keywords.some((keyword) => lower.includes(keyword))
    })
    .forEach((line) => {
      const lower = line.toLowerCase()
      const taskMatch = line.match(/\btask\s+([A-Za-z0-9_-]+)/i)
      const agentMatch = line.match(/\bagent\s+([A-Za-z0-9_-]+)/i)
      const outputMatch = line.match(/([^\s]+?\.(?:md|txt|json))\b/i)
      if (taskMatch) summary.push(`正在执行任务：${taskMatch[1]}`)
      if (agentMatch) summary.push(`当前智能体：${agentMatch[1]}`)
      if (outputMatch) summary.push(`输出文件：${outputMatch[1]}`)
      if (lower.includes('error') || lower.includes('failed') || lower.includes('exception')) summary.push(`运行失败：${line}`)
      else if (lower.includes('success') || lower.includes('finished') || lower.includes('completed')) summary.push('运行成功')
    })
  return summary.length ? summary.slice(-80).join('\n') : '暂无关键进度。需要排查时请切换到原始日志。'
}

export function connectRunLogs(runId, onMessage) {
  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
  const socket = new WebSocket(`${protocol}://${window.location.host}/ws/runs/${runId}/logs`)
  socket.addEventListener('message', (event) => onMessage(event.data))
  return socket
}
