<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { api, connectRunLogs, simplifyLogText } from '../api/client'
import StatusPill from '../components/StatusPill.vue'

const runs = ref([])
const selectedRun = ref(null)
const liveLog = ref('')
const error = ref('')
const running = ref(false)
const logMode = ref('simple')
let socket = null
const props = defineProps({
  initialRunId: {
    type: Number,
    default: null
  }
})

const displayLog = computed(() => {
  if (liveLog.value) {
    return logMode.value === 'simple' ? simplifyLogText(liveLog.value) : liveLog.value
  }
  if (!selectedRun.value) return '暂无日志'
  return logMode.value === 'simple' ? selectedRun.value.simple_log_text : selectedRun.value.log_text
})

function formatDate(value) {
  return value ? new Date(value).toLocaleString() : '-'
}

function formatDuration(ms) {
  return ms ? `${(ms / 1000).toFixed(1)} 秒` : '-'
}

async function loadRuns() {
  runs.value = await api.getRuns()
}

async function selectRun(id) {
  selectedRun.value = await api.getRun(id)
  liveLog.value = ''
}

async function followRun(id) {
  if (!id) return
  error.value = ''
  liveLog.value = ''
  running.value = true
  logMode.value = 'simple'
  await loadRuns()
  selectedRun.value = await api.getRun(id)
  if (socket) socket.close()
  socket = connectRunLogs(id, async (message) => {
    liveLog.value += message
    if (message.includes('[run success]') || message.includes('[run failed]')) {
      running.value = false
      await loadRuns()
      await selectRun(id)
    }
  })
}

async function startRun() {
  error.value = ''
  liveLog.value = ''
  running.value = true
  logMode.value = 'simple'
  try {
    const run = await api.startRun()
    await followRun(run.id)
  } catch (err) {
    running.value = false
    error.value = err.message
  }
}

onMounted(async () => {
  await loadRuns()
  if (props.initialRunId) await followRun(props.initialRunId)
})

watch(
  () => props.initialRunId,
  async (runId) => {
    if (runId) await followRun(runId)
  }
)
</script>

<template>
  <section>
    <div class="mb-6 flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-semibold">运行记录</h1>
        <p class="text-sm text-neutral-500">启动生产线，查看简洁进度或原始日志</p>
      </div>
      <button
        class="rounded-md px-4 py-2 text-sm font-medium text-white"
        :class="running ? 'bg-neutral-400' : 'bg-accent'"
        type="button"
        :disabled="running"
        @click="startRun"
      >
        {{ running ? '运行中' : '运行生产线' }}
      </button>
    </div>
    <div v-if="error" class="mb-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">{{ error }}</div>
    <div class="grid grid-cols-[420px_1fr] gap-4">
      <div class="rounded-md border border-line bg-white">
        <div class="border-b border-line p-3 text-sm font-semibold">历史记录</div>
        <button
          v-for="run in runs"
          :key="run.id"
          type="button"
          class="block w-full border-b border-line p-3 text-left text-sm hover:bg-panel"
          @click="selectRun(run.id)"
        >
          <div class="mb-2 flex items-center justify-between">
            <span class="font-medium">第 {{ run.id }} 次运行</span>
            <StatusPill :status="run.status" />
          </div>
          <div class="grid grid-cols-2 gap-2 text-xs text-neutral-500">
            <span>开始：{{ formatDate(run.started_at) }}</span>
            <span>耗时：{{ formatDuration(run.duration_ms) }}</span>
          </div>
        </button>
      </div>
      <div class="rounded-md border border-line bg-white">
        <div class="flex items-center justify-between border-b border-line p-3">
          <div class="text-sm font-semibold">日志</div>
          <div class="rounded-md border border-line bg-panel p-1 text-xs">
            <button class="rounded px-3 py-1" :class="logMode === 'simple' ? 'bg-white shadow-sm' : ''" type="button" @click="logMode = 'simple'">简洁日志</button>
            <button class="rounded px-3 py-1" :class="logMode === 'raw' ? 'bg-white shadow-sm' : ''" type="button" @click="logMode = 'raw'">原始日志</button>
          </div>
        </div>
        <pre class="max-h-[68vh] min-h-[420px] overflow-auto whitespace-pre-wrap bg-[#1f2328] p-4 text-xs leading-5 text-[#f0f3f6]">{{ displayLog }}</pre>
      </div>
    </div>
  </section>
</template>
