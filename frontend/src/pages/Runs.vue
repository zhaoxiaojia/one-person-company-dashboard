<script setup>
import { onMounted, ref } from 'vue'
import { api, connectRunLogs } from '../api/client'
import StatusPill from '../components/StatusPill.vue'

const runs = ref([])
const selectedRun = ref(null)
const liveLog = ref('')
const error = ref('')
const running = ref(false)
let socket = null

function formatDate(value) {
  return value ? new Date(value).toLocaleString() : '-'
}

function formatDuration(ms) {
  return ms ? `${(ms / 1000).toFixed(1)}s` : '-'
}

async function loadRuns() {
  runs.value = await api.getRuns()
}

async function selectRun(id) {
  selectedRun.value = await api.getRun(id)
}

async function startRun() {
  error.value = ''
  liveLog.value = ''
  running.value = true
  try {
    const run = await api.startRun()
    if (socket) socket.close()
    socket = connectRunLogs(run.id, async (message) => {
      liveLog.value += message
      if (message.includes('[run success]') || message.includes('[run failed]')) {
        running.value = false
        await loadRuns()
        await selectRun(run.id)
      }
    })
    await loadRuns()
  } catch (err) {
    running.value = false
    error.value = err.message
  }
}

onMounted(async () => {
  await loadRuns()
})
</script>

<template>
  <section>
    <div class="mb-6 flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-semibold">Runs</h1>
        <p class="text-sm text-neutral-500">运行 Crew、查看实时日志和历史记录</p>
      </div>
      <button
        class="rounded-md px-4 py-2 text-sm font-medium text-white"
        :class="running ? 'bg-neutral-400' : 'bg-accent'"
        type="button"
        :disabled="running"
        @click="startRun"
      >
        {{ running ? 'Running' : 'Run Crew' }}
      </button>
    </div>
    <div v-if="error" class="mb-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">{{ error }}</div>
    <div class="grid grid-cols-[420px_1fr] gap-4">
      <div class="rounded-md border border-line bg-white">
        <div class="border-b border-line p-3 text-sm font-semibold">运行历史</div>
        <button
          v-for="run in runs"
          :key="run.id"
          type="button"
          class="block w-full border-b border-line p-3 text-left text-sm hover:bg-panel"
          @click="selectRun(run.id)"
        >
          <div class="mb-2 flex items-center justify-between">
            <span class="font-medium">Run #{{ run.id }}</span>
            <StatusPill :status="run.status" />
          </div>
          <div class="grid grid-cols-2 gap-2 text-xs text-neutral-500">
            <span>开始：{{ formatDate(run.started_at) }}</span>
            <span>耗时：{{ formatDuration(run.duration_ms) }}</span>
          </div>
        </button>
      </div>
      <div class="rounded-md border border-line bg-white">
        <div class="border-b border-line p-3 text-sm font-semibold">日志</div>
        <pre class="max-h-[68vh] min-h-[420px] overflow-auto whitespace-pre-wrap bg-[#1f2328] p-4 text-xs leading-5 text-[#f0f3f6]">{{ liveLog || selectedRun?.log_text || '暂无日志' }}</pre>
      </div>
    </div>
  </section>
</template>
