<script setup>
import { onMounted, ref } from 'vue'
import { api } from '../api/client'

const settings = ref(null)
const health = ref(null)
const pathInput = ref('')
const error = ref('')
const notice = ref('')

async function load() {
  error.value = ''
  settings.value = await api.getSettings()
  pathInput.value = settings.value.crew_project_path
  await checkHealth()
}

async function save() {
  error.value = ''
  notice.value = ''
  try {
    settings.value = await api.saveSettings(pathInput.value)
    pathInput.value = settings.value.crew_project_path
    notice.value = '项目路径已保存，后端已切换到新路径。'
    await checkHealth()
  } catch (err) {
    error.value = err.message
  }
}

async function checkHealth() {
  try {
    health.value = await api.getHealth()
  } catch (err) {
    error.value = err.message
  }
}

onMounted(load)
</script>

<template>
  <section>
    <div class="mb-6">
      <h1 class="text-2xl font-semibold">项目设置</h1>
      <p class="text-sm text-neutral-500">配置本地 CrewAI 项目路径，并检查运行环境是否就绪</p>
    </div>
    <div v-if="error" class="mb-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">{{ error }}</div>
    <div v-if="notice" class="mb-4 rounded-md border border-green-200 bg-green-50 p-3 text-sm text-green-700">{{ notice }}</div>

    <div class="rounded-md border border-line bg-white p-4">
      <label class="mb-2 block text-sm font-medium" for="projectPath">CrewAI 项目路径</label>
      <div class="flex gap-2">
        <input id="projectPath" v-model="pathInput" class="flex-1 rounded-md border border-line p-2 text-sm" />
        <button class="rounded-md bg-accent px-4 py-2 text-sm text-white" type="button" @click="save">保存路径</button>
        <button class="rounded-md border border-line px-4 py-2 text-sm" type="button" @click="checkHealth">健康检查</button>
      </div>
      <div class="mt-2 text-xs text-neutral-500">
        当前来源：{{ settings?.source === 'local' ? '本地配置' : settings?.source === 'environment' ? '环境变量' : '默认路径' }}
      </div>
    </div>

    <div class="mt-4 rounded-md border border-line bg-white p-4">
      <div class="mb-3 flex items-center justify-between">
        <h2 class="font-semibold">健康检查</h2>
        <span class="rounded px-2 py-1 text-xs font-medium" :class="health?.ok ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'">
          {{ health?.ok ? '可以运行' : '需要处理' }}
        </span>
      </div>
      <p class="mb-3 text-sm text-neutral-600">{{ health?.message }}</p>
      <div class="space-y-2">
        <div v-for="check in health?.checks" :key="check.name" class="rounded-md border border-line p-3 text-sm">
          <div class="flex items-center justify-between">
            <span class="font-medium">{{ check.name }}</span>
            <span :class="check.ok ? 'text-green-700' : 'text-red-700'">{{ check.ok ? '通过' : '失败' }}</span>
          </div>
          <div class="mt-1 text-neutral-600">{{ check.message }}</div>
        </div>
      </div>
    </div>
  </section>
</template>
