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
import SettingsPage from './pages/Settings.vue'

const pages = [
  { id: 'dashboard', label: '控制台', icon: Gauge, component: Dashboard },
  { id: 'agents', label: '智能体', icon: Bot, component: Agents },
  { id: 'tasks', label: '任务', icon: ClipboardList, component: Tasks },
  { id: 'config', label: '运行输入', icon: Settings, component: CrewConfig },
  { id: 'runs', label: '运行记录', icon: History, component: Runs },
  { id: 'outputs', label: '输出文件', icon: FileText, component: Outputs },
  { id: 'models', label: '模型设置', icon: SlidersHorizontal, component: Models },
  { id: 'flow', label: '流程图', icon: GitBranch, component: Flow },
  { id: 'settings', label: '项目设置', icon: Settings, component: SettingsPage }
]

const activePage = ref('dashboard')
const pendingRunId = ref(null)
const appRefreshKey = ref(0)
const activeComponent = computed(() => pages.find((page) => page.id === activePage.value)?.component || Dashboard)

function handleRunStarted(runId) {
  pendingRunId.value = runId
  activePage.value = 'runs'
}

function handleSettingsSaved() {
  appRefreshKey.value += 1
  pendingRunId.value = null
}
</script>

<template>
  <div class="min-h-screen">
    <aside class="fixed inset-y-0 left-0 w-64 border-r border-line bg-[#fbfaf6] px-4 py-5">
      <div class="mb-8">
        <div class="text-lg font-semibold leading-tight">一人公司控制台</div>
        <div class="text-sm text-neutral-500">本地 CrewAI 生产线</div>
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
      <component
        :is="activeComponent"
        :key="`${activePage}-${appRefreshKey}`"
        :initial-run-id="activePage === 'runs' ? pendingRunId : null"
        @run-started="handleRunStarted"
        @settings-saved="handleSettingsSaved"
      />
    </main>
  </div>
</template>
