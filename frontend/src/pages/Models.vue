<script setup>
import { onMounted, ref } from 'vue'
import { api } from '../api/client'

const config = ref(null)
const llm = ref('deepseek/deepseek-chat')
const error = ref('')
const notice = ref('')

async function load() {
  error.value = ''
  notice.value = ''
  config.value = await api.getModelConfig()
  llm.value = config.value.agent_llms?.[0]?.llm || llm.value
}

async function saveModels() {
  error.value = ''
  notice.value = ''
  try {
    await api.updateAgentModels(llm.value)
    notice.value = '所有 Agent 的 llm 已批量更新，旧文件已自动备份。'
    await load()
  } catch (err) {
    error.value = err.message
  }
}

onMounted(load)
</script>

<template>
  <section>
    <div class="mb-6">
      <h1 class="text-2xl font-semibold">模型设置</h1>
      <p class="text-sm text-neutral-500">查看脱敏环境变量，并批量切换智能体模型</p>
    </div>
    <div v-if="error" class="mb-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">{{ error }}</div>
    <div v-if="notice" class="mb-4 rounded-md border border-green-200 bg-green-50 p-3 text-sm text-green-700">{{ notice }}</div>
    <div class="grid grid-cols-2 gap-4">
      <div class="rounded-md border border-line bg-white p-4">
        <h2 class="mb-3 font-semibold">.env</h2>
        <dl class="space-y-2 text-sm">
          <div v-for="(value, key) in config?.env" :key="key" class="flex justify-between gap-4 border-b border-line pb-2">
            <dt class="font-medium">{{ key }}</dt>
            <dd class="text-neutral-600">{{ value }}</dd>
          </div>
        </dl>
      </div>
      <div class="rounded-md border border-line bg-white p-4">
        <h2 class="mb-3 font-semibold">批量切换智能体模型</h2>
        <input v-model="llm" class="mb-3 w-full rounded-md border border-line p-2 text-sm" />
        <button class="rounded-md bg-accent px-4 py-2 text-sm text-white" type="button" @click="saveModels">应用到全部智能体</button>
        <div class="mt-5 space-y-2 text-sm">
          <div v-for="agent in config?.agent_llms" :key="agent.filename" class="flex justify-between gap-4 border-b border-line pb-2">
            <span class="font-medium">{{ agent.filename }}</span>
            <span class="text-neutral-600">{{ agent.llm }}</span>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
