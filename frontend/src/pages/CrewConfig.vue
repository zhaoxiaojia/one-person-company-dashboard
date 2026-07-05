<script setup>
import { onMounted, ref } from 'vue'
import { api } from '../api/client'

const config = ref(null)
const storyIdea = ref('')
const error = ref('')
const notice = ref('')

async function load() {
  error.value = ''
  notice.value = ''
  try {
    config.value = await api.getCrewConfig()
    storyIdea.value = config.value.inputs?.story_idea || ''
  } catch (err) {
    error.value = err.message
  }
}

async function save() {
  error.value = ''
  notice.value = ''
  try {
    const inputs = { ...(config.value?.inputs || {}), story_idea: storyIdea.value }
    config.value = await api.updateInputs(inputs)
    notice.value = '已保存 inputs，并创建 crew.jsonc 备份。'
  } catch (err) {
    error.value = err.message
  }
}

onMounted(load)
</script>

<template>
  <section>
    <div class="mb-6">
      <h1 class="text-2xl font-semibold">Crew Config</h1>
      <p class="text-sm text-neutral-500">编辑本次运行输入</p>
    </div>
    <div v-if="error" class="mb-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">{{ error }}</div>
    <div v-if="notice" class="mb-4 rounded-md border border-green-200 bg-green-50 p-3 text-sm text-green-700">{{ notice }}</div>
    <div v-if="config" class="rounded-md border border-line bg-white p-4">
      <dl class="mb-5 grid grid-cols-4 gap-4 text-sm">
        <div>
          <dt class="text-neutral-500">Name</dt>
          <dd class="mt-1 font-medium">{{ config.name }}</dd>
        </div>
        <div>
          <dt class="text-neutral-500">Process</dt>
          <dd class="mt-1 font-medium">{{ config.process }}</dd>
        </div>
        <div>
          <dt class="text-neutral-500">Verbose</dt>
          <dd class="mt-1 font-medium">{{ config.verbose }}</dd>
        </div>
        <div>
          <dt class="text-neutral-500">Memory</dt>
          <dd class="mt-1 font-medium">{{ config.memory }}</dd>
        </div>
      </dl>
      <label class="mb-2 block text-sm font-medium" for="storyIdea">story_idea</label>
      <textarea
        id="storyIdea"
        v-model="storyIdea"
        class="min-h-36 w-full rounded-md border border-line bg-[#fffefa] p-3 text-sm outline-none focus:border-accent"
      />
      <div class="mt-4 flex justify-end">
        <button class="rounded-md bg-accent px-4 py-2 text-sm font-medium text-white" type="button" @click="save">
          保存输入
        </button>
      </div>
    </div>
  </section>
</template>
