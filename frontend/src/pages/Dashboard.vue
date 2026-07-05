<script setup>
import { computed, onMounted, ref } from 'vue'
import { Play } from 'lucide-vue-next'
import { api } from '../api/client'
import StatusPill from '../components/StatusPill.vue'

const summary = ref(null)
const health = ref(null)
const error = ref('')
const running = ref(false)
const emit = defineEmits(['run-started'])

const latestRun = computed(() => summary.value?.latest_run || null)
const succeeded = computed(() => latestRun.value?.status === 'success')

function formatDuration(ms) {
  if (!ms) return '-'
  return `${(ms / 1000).toFixed(1)} 秒`
}

async function load() {
  error.value = ''
  try {
    const [summaryPayload, healthPayload] = await Promise.all([api.getSummary(), api.getHealth()])
    summary.value = summaryPayload
    health.value = healthPayload
    running.value = latestRun.value?.status === 'running'
  } catch (err) {
    error.value = err.message
  }
}

async function startProductionLine() {
  error.value = ''
  running.value = true
  try {
    const run = await api.startRun()
    emit('run-started', run.id)
  } catch (err) {
    running.value = false
    error.value = err.message
  }
}

onMounted(load)
</script>

<template>
  <section>
    <div class="mb-6 flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-semibold">CEO 控制台</h1>
        <p class="text-sm text-neutral-500">查看生产线状态，一键启动本地 CrewAI 工作流</p>
      </div>
      <button class="rounded-md border border-line px-3 py-2 text-sm" type="button" @click="load">刷新状态</button>
    </div>

    <div v-if="error" class="mb-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">{{ error }}</div>

    <div class="mb-5 rounded-md border border-line bg-white p-5">
      <div class="flex items-center justify-between gap-5">
        <div>
          <div class="text-sm text-neutral-500">当前 Crew</div>
          <div class="mt-1 text-2xl font-semibold">{{ summary?.name || '未读取到 Crew' }}</div>
        </div>
        <button
          class="inline-flex items-center gap-2 rounded-md px-6 py-3 text-base font-semibold text-white shadow-sm"
          :class="running || health?.ok === false ? 'bg-neutral-400' : 'bg-accent hover:brightness-95'"
          type="button"
          :disabled="running || health?.ok === false"
          @click="startProductionLine"
        >
          <Play class="h-5 w-5" />
          {{ running ? '生产线运行中' : '运行生产线' }}
        </button>
      </div>
      <div v-if="health?.ok === false" class="mt-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
        运行环境异常：{{ health.message }}
      </div>
    </div>

    <div v-if="summary" class="grid grid-cols-5 gap-4">
      <div class="rounded-md border border-line bg-white p-4">
        <div class="text-sm text-neutral-500">智能体数量</div>
        <div class="mt-2 text-3xl font-semibold">{{ summary.agent_count }}</div>
      </div>
      <div class="rounded-md border border-line bg-white p-4">
        <div class="text-sm text-neutral-500">任务数量</div>
        <div class="mt-2 text-3xl font-semibold">{{ summary.task_count }}</div>
      </div>
      <div class="rounded-md border border-line bg-white p-4">
        <div class="text-sm text-neutral-500">最近状态</div>
        <div class="mt-3"><StatusPill :status="latestRun?.status || 'unknown'" /></div>
      </div>
      <div class="rounded-md border border-line bg-white p-4">
        <div class="text-sm text-neutral-500">运行环境</div>
        <div class="mt-2 text-2xl font-semibold" :class="health?.ok ? 'text-green-700' : 'text-red-700'">
          {{ health ? (health.ok ? '正常' : '异常') : '-' }}
        </div>
      </div>
      <div class="rounded-md border border-line bg-white p-4">
        <div class="text-sm text-neutral-500">是否成功</div>
        <div class="mt-2 text-2xl font-semibold" :class="succeeded ? 'text-green-700' : 'text-neutral-700'">
          {{ latestRun ? (succeeded ? '成功' : '未成功') : '-' }}
        </div>
      </div>
    </div>

    <div class="mt-4 rounded-md border border-line bg-white p-4">
      <h2 class="mb-4 text-base font-semibold">最近一次运行</h2>
      <div class="grid grid-cols-3 gap-4 text-sm">
        <div>
          <div class="text-neutral-500">耗时</div>
          <div class="mt-1 font-medium">{{ formatDuration(latestRun?.duration_ms) }}</div>
        </div>
        <div>
          <div class="text-neutral-500">输出文件</div>
          <div class="mt-1 truncate font-medium">{{ latestRun?.output_paths?.[0] || '-' }}</div>
        </div>
        <div>
          <div class="text-neutral-500">错误信息</div>
          <div class="mt-1 truncate font-medium">{{ latestRun?.error_message || '-' }}</div>
        </div>
      </div>
    </div>
  </section>
</template>
