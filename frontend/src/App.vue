<script setup>
import { computed, ref } from 'vue'
import { Bot, ClipboardList, FileText, Gauge, GitBranch, History, Settings, SlidersHorizontal } from 'lucide-vue-next'
import Dashboard from './pages/Dashboard.vue'
import Agents from './pages/Agents.vue'
import Tasks from './pages/Tasks.vue'
import CrewConfig from './pages/CrewConfig.vue'
import Runs from './pages/Runs.vue'
import Outputs from './pages/Outputs.vue'
import Models from './pages/Models.vue'
import Flow from './pages/Flow.vue'

const pages = [
  { id: 'dashboard', label: 'Dashboard', icon: Gauge, component: Dashboard },
  { id: 'agents', label: 'Agents', icon: Bot, component: Agents },
  { id: 'tasks', label: 'Tasks', icon: ClipboardList, component: Tasks },
  { id: 'config', label: 'Crew Config', icon: Settings, component: CrewConfig },
  { id: 'runs', label: 'Runs', icon: History, component: Runs },
  { id: 'outputs', label: 'Outputs', icon: FileText, component: Outputs },
  { id: 'models', label: 'Models', icon: SlidersHorizontal, component: Models },
  { id: 'flow', label: 'Flow', icon: GitBranch, component: Flow }
]

const activePage = ref('dashboard')
const activeComponent = computed(() => pages.find((page) => page.id === activePage.value)?.component || Dashboard)
</script>

<template>
  <div class="min-h-screen">
    <aside class="fixed inset-y-0 left-0 w-64 border-r border-line bg-[#fbfaf6] px-4 py-5">
      <div class="mb-8">
        <div class="text-lg font-semibold leading-tight">One Person Company</div>
        <div class="text-sm text-neutral-500">CrewAI Dashboard</div>
      </div>
      <nav class="space-y-1">
        <button
          v-for="page in pages"
          :key="page.id"
          type="button"
          class="flex w-full items-center gap-3 rounded-md px-3 py-2 text-left text-sm transition"
          :class="activePage === page.id ? 'bg-accent text-white' : 'text-neutral-700 hover:bg-panel'"
          @click="activePage = page.id"
        >
          <component :is="page.icon" class="h-4 w-4" />
          <span>{{ page.label }}</span>
        </button>
      </nav>
    </aside>
    <main class="ml-64 px-8 py-6">
      <component :is="activeComponent" />
    </main>
  </div>
</template>
