<script setup>
import { computed, onMounted, ref } from 'vue'
import { api } from '../api/client'

const agents = ref([])
const selectedFilename = ref('')
const editorText = ref('')
const newFilename = ref('new_agent.jsonc')
const error = ref('')
const notice = ref('')

const selectedAgent = computed(() => agents.value.find((agent) => agent.filename === selectedFilename.value))

const emptyAgent = {
  role: '新 Agent',
  goal: '描述这个 Agent 要完成的目标。',
  backstory: '描述这个 Agent 的背景和工作方式。',
  llm: 'openai/deepseek-chat',
  tools: ['FileReadTool', 'FileWriterTool'],
  settings: { verbose: false, allow_delegation: false }
}

async function load() {
  error.value = ''
  notice.value = ''
  agents.value = await api.getAgents()
  if (!selectedFilename.value && agents.value.length) {
    await selectAgent(agents.value[0].filename)
  }
}

async function selectAgent(filename) {
  error.value = ''
  selectedFilename.value = filename
  const detail = await api.getAgent(filename)
  editorText.value = JSON.stringify(detail.content, null, 2)
}

function createDraft() {
  selectedFilename.value = newFilename.value
  editorText.value = JSON.stringify(emptyAgent, null, 2)
}

async function save() {
  error.value = ''
  notice.value = ''
  try {
    const parsed = JSON.parse(editorText.value)
    await api.saveAgent(selectedFilename.value, parsed)
    notice.value = 'Agent 已保存，旧文件已自动备份。'
    await load()
    await selectAgent(selectedFilename.value)
  } catch (err) {
    error.value = err.message
  }
}

async function remove() {
  error.value = ''
  notice.value = ''
  if (!selectedFilename.value) return
  try {
    await api.deleteAgent(selectedFilename.value)
    notice.value = 'Agent 已删除，删除前已自动备份。'
    selectedFilename.value = ''
    editorText.value = ''
    await load()
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
        <h1 class="text-2xl font-semibold">Agents</h1>
        <p class="text-sm text-neutral-500">查看、创建、编辑和删除 agent JSONC 文件</p>
      </div>
      <button class="rounded-md bg-ink px-3 py-2 text-sm text-white" type="button" @click="load">刷新</button>
    </div>
    <div v-if="error" class="mb-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">{{ error }}</div>
    <div v-if="notice" class="mb-4 rounded-md border border-green-200 bg-green-50 p-3 text-sm text-green-700">{{ notice }}</div>

    <div class="grid grid-cols-[420px_1fr] gap-4">
      <div class="rounded-md border border-line bg-white">
        <div class="border-b border-line p-3 text-sm font-semibold">Agent 列表</div>
        <button
          v-for="agent in agents"
          :key="agent.filename"
          type="button"
          class="block w-full border-b border-line p-3 text-left text-sm hover:bg-panel"
          :class="selectedFilename === agent.filename ? 'bg-panel' : ''"
          @click="selectAgent(agent.filename)"
        >
          <div class="font-medium">{{ agent.filename }}</div>
          <div class="mt-1 text-neutral-600">{{ agent.role }}</div>
          <div class="mt-1 text-xs text-neutral-500">{{ agent.llm }}</div>
        </button>
        <div class="space-y-2 p-3">
          <input v-model="newFilename" class="w-full rounded-md border border-line p-2 text-sm" />
          <button class="w-full rounded-md border border-line px-3 py-2 text-sm" type="button" @click="createDraft">新建 Agent 草稿</button>
        </div>
      </div>

      <div class="rounded-md border border-line bg-white p-4">
        <div class="mb-3 flex items-center justify-between">
          <div>
            <div class="text-sm text-neutral-500">当前文件</div>
            <div class="font-semibold">{{ selectedFilename || '-' }}</div>
          </div>
          <div class="flex gap-2">
            <button class="rounded-md border border-line px-3 py-2 text-sm" type="button" :disabled="!selectedAgent" @click="remove">删除</button>
            <button class="rounded-md bg-accent px-3 py-2 text-sm text-white" type="button" :disabled="!selectedFilename" @click="save">保存</button>
          </div>
        </div>
        <textarea v-model="editorText" class="min-h-[560px] w-full rounded-md border border-line bg-[#fffefa] p-3 font-mono text-xs outline-none focus:border-accent" />
      </div>
    </div>
  </section>
</template>
