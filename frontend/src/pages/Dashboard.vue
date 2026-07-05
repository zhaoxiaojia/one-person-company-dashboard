<script setup>
import { onMounted, ref } from 'vue'
import { api } from '../api/client'
import StatusPill from '../components/StatusPill.vue'

const summary = ref(null)
const error = ref('')

function formatDuration(ms) {
  if (!ms) return '-'
  return `${(ms / 1000).toFixed(1)}s`
}

async function load() {
  error.value = ''
  try {
    summary.value = await api.getSummary()
  } catch (err) {
    error.value = err.message
  }
}

onMounted(load)
</script>

<template>
  <section>
    <div class="mb-6 flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-semibold">Dashboard</h1>
        <p class="text-sm text-neutral-500">当前 Crew 状态和最近一次运行结果</p>
      </div>
      <button class="rounded-md bg-ink px-3 py-2 text-sm text-white" type="button" @click="load">刷新</button>
    </div>

    <div v-if="error" class="mb-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">{{ error }}</div>

    <div v-if="summary" class="grid grid-cols-3 gap-4">
      <div class="rounded-md border border-line bg-white p-4">
        <div class="text-sm text-neutral-500">Crew 名称</div>
        <div class="mt-2 text-xl font-semibold">{{ summary.name }}</div>
      </div>
      <div class="rounded-md border border-line bg-white p-4">
        <div class="text-sm text-neutral-500">Agents</div>
        <div class="mt-2 text-3xl font-semibold">{{ summary.agent_count }}</div>
      </div>
      <div class="rounded-md border border-line bg-white p-4">
        <div class="text-sm text-neutral-500">Tasks</div>
        <div class="mt-2 text-3xl font-semibold">{{ summary.task_count }}</div>
      </div>
    </div>

    <div v-if="summary?.latest_run" class="mt-4 rounded-md border border-line bg-white p-4">
      <div class="mb-4 flex items-center justify-between">
        <h2 class="text-base font-semibold">最近一次运行</h2>
        <StatusPill :status="summary.latest_run.status" />
      </div>
      <div class="grid grid-cols-4 gap-4 text-sm">
        <div>
          <div class="text-neutral-500">耗时</div>
          <div class="mt-1 font-medium">{{ formatDuration(summary.latest_run.duration_ms) }}</div>
        </div>
        <div>
          <div class="text-neutral-500">Input Tokens</div>
          <div class="mt-1 font-medium">{{ summary.latest_run.input_tokens ?? '-' }}</div>
        </div>
        <div>
          <div class="text-neutral-500">Output Tokens</div>
          <div class="mt-1 font-medium">{{ summary.latest_run.output_tokens ?? '-' }}</div>
        </div>
        <div>
          <div class="text-neutral-500">输出文件</div>
          <div class="mt-1 truncate font-medium">{{ summary.latest_run.output_paths?.[0] || '-' }}</div>
        </div>
      </div>
    </div>
  </section>
</template>
