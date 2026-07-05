<script setup>
import { computed, onMounted, ref } from 'vue'
import { marked } from 'marked'
import { api } from '../api/client'

const outputs = ref([])
const selected = ref(null)
const error = ref('')
const notice = ref('')

const renderedMarkdown = computed(() => {
  if (!selected.value || selected.value.kind !== 'markdown') return ''
  return marked.parse(selected.value.content)
})

async function load() {
  error.value = ''
  outputs.value = await api.getOutputs()
}

async function selectOutput(output) {
  error.value = ''
  selected.value = await api.getOutputContent(output.path)
}

async function copyContent() {
  if (!selected.value) return
  await navigator.clipboard.writeText(selected.value.content)
  notice.value = '内容已复制。'
}

onMounted(load)
</script>

<template>
  <section>
    <div class="mb-6 flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-semibold">输出文件</h1>
        <p class="text-sm text-neutral-500">查看项目根目录和 outputs/ 下的 md、txt、json 产物</p>
      </div>
      <button class="rounded-md bg-ink px-3 py-2 text-sm text-white" type="button" @click="load">刷新</button>
    </div>
    <div v-if="error" class="mb-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">{{ error }}</div>
    <div v-if="notice" class="mb-4 rounded-md border border-green-200 bg-green-50 p-3 text-sm text-green-700">{{ notice }}</div>
    <div class="grid grid-cols-[360px_1fr] gap-4">
      <div class="rounded-md border border-line bg-white">
        <div class="border-b border-line p-3 text-sm font-semibold">输出文件</div>
        <button
          v-for="output in outputs"
          :key="output.path"
          class="block w-full border-b border-line p-3 text-left text-sm hover:bg-panel"
          type="button"
          @click="selectOutput(output)"
        >
          <div class="font-medium">{{ output.name }}</div>
          <div class="mt-1 text-xs text-neutral-500">{{ output.path }} · {{ output.kind }} · {{ output.size }} 字节</div>
        </button>
      </div>
      <div class="rounded-md border border-line bg-white">
        <div class="flex items-center justify-between border-b border-line p-3">
          <div class="text-sm font-semibold">{{ selected?.name || '预览' }}</div>
          <button class="rounded-md border border-line px-3 py-1 text-sm" type="button" :disabled="!selected" @click="copyContent">复制内容</button>
        </div>
        <div v-if="selected?.kind === 'markdown'" class="prose-preview max-h-[70vh] overflow-auto p-4 text-sm" v-html="renderedMarkdown" />
        <pre v-else class="max-h-[70vh] min-h-[420px] overflow-auto whitespace-pre-wrap p-4 text-sm">{{ selected?.content || '请选择一个输出文件' }}</pre>
      </div>
    </div>
  </section>
</template>
