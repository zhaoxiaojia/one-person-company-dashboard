<script setup>
import { onMounted, ref } from 'vue'
import { api } from '../api/client'

const tasks = ref([])
const error = ref('')
const notice = ref('')

const emptyTask = () => ({
  name: 'new_task',
  description: '描述这个任务要做什么。',
  expected_output: '描述这个任务应该输出什么。',
  agent: ''
})

async function load() {
  error.value = ''
  notice.value = ''
  tasks.value = await api.getTasks()
}

function addTask() {
  tasks.value.push(emptyTask())
}

function removeTask(index) {
  tasks.value.splice(index, 1)
}

function moveTask(index, direction) {
  const target = index + direction
  if (target < 0 || target >= tasks.value.length) return
  const [task] = tasks.value.splice(index, 1)
  tasks.value.splice(target, 0, task)
}

async function save() {
  error.value = ''
  notice.value = ''
  try {
    tasks.value = await api.saveTasks(tasks.value)
    notice.value = '任务已保存到 crew.jsonc，旧文件已自动备份。'
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
        <h1 class="text-2xl font-semibold">任务</h1>
        <p class="text-sm text-neutral-500">新增、编辑、删除和调整 crew.jsonc 中的任务顺序</p>
      </div>
      <div class="flex gap-2">
        <button class="rounded-md border border-line px-3 py-2 text-sm" type="button" @click="addTask">新增任务</button>
        <button class="rounded-md bg-accent px-3 py-2 text-sm text-white" type="button" @click="save">保存任务</button>
      </div>
    </div>
    <div v-if="error" class="mb-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">{{ error }}</div>
    <div v-if="notice" class="mb-4 rounded-md border border-green-200 bg-green-50 p-3 text-sm text-green-700">{{ notice }}</div>

    <div class="space-y-3">
      <article v-for="(task, index) in tasks" :key="`${task.name}-${index}`" class="rounded-md border border-line bg-white p-4">
        <div class="mb-3 flex items-center justify-between">
          <h2 class="font-semibold">#{{ index + 1 }}</h2>
          <div class="flex gap-2">
            <button class="rounded-md border border-line px-2 py-1 text-xs" type="button" @click="moveTask(index, -1)">上移</button>
            <button class="rounded-md border border-line px-2 py-1 text-xs" type="button" @click="moveTask(index, 1)">下移</button>
            <button class="rounded-md border border-red-200 px-2 py-1 text-xs text-red-700" type="button" @click="removeTask(index)">删除</button>
          </div>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <label class="text-sm">
            <span class="mb-1 block text-neutral-500">name</span>
            <input v-model="task.name" class="w-full rounded-md border border-line p-2" />
          </label>
          <label class="text-sm">
            <span class="mb-1 block text-neutral-500">agent</span>
            <input v-model="task.agent" class="w-full rounded-md border border-line p-2" />
          </label>
        </div>
        <label class="mt-3 block text-sm">
            <span class="mb-1 block text-neutral-500">任务说明</span>
          <textarea v-model="task.description" class="min-h-24 w-full rounded-md border border-line p-2" />
        </label>
        <label class="mt-3 block text-sm">
            <span class="mb-1 block text-neutral-500">预期输出</span>
          <textarea v-model="task.expected_output" class="min-h-20 w-full rounded-md border border-line p-2" />
        </label>
      </article>
    </div>
  </section>
</template>
