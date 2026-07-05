<script setup>
import { onMounted, ref } from 'vue'
import { api } from '../api/client'

const tasks = ref([])
const error = ref('')

async function load() {
  error.value = ''
  try {
    tasks.value = await api.getTasks()
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
        <h1 class="text-2xl font-semibold">流程图</h1>
        <p class="text-sm text-neutral-500">基于当前 task 顺序生成的轻量流程图</p>
      </div>
      <button class="rounded-md bg-ink px-3 py-2 text-sm text-white" type="button" @click="load">刷新</button>
    </div>
    <div v-if="error" class="mb-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">{{ error }}</div>
    <div class="overflow-x-auto rounded-md border border-line bg-white p-8">
      <div class="flex min-w-max items-center gap-4">
        <template v-for="(task, index) in tasks" :key="task.name">
          <div class="w-72 rounded-md border border-line bg-[#fffefa] p-4">
            <div class="mb-2 text-xs font-medium text-neutral-500">第 {{ index + 1 }} 步</div>
            <div class="font-semibold">{{ task.name }}</div>
            <div class="mt-2 rounded bg-panel px-2 py-1 text-xs text-neutral-600">{{ task.agent }}</div>
            <p class="flow-description mt-3 text-sm leading-6 text-neutral-700">{{ task.description }}</p>
          </div>
          <div v-if="index < tasks.length - 1" class="text-2xl text-neutral-400">→</div>
        </template>
      </div>
    </div>
  </section>
</template>

<style scoped>
.flow-description {
  display: -webkit-box;
  -webkit-line-clamp: 4;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
