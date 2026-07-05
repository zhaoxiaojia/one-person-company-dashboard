<script setup>
defineProps({
  status: {
    type: String,
    default: 'unknown'
  }
})

const labels = {
  running: '运行中',
  success: '成功',
  failed: '失败',
  unknown: '未知'
}
</script>

<template>
  <span
    class="inline-flex items-center rounded px-2 py-1 text-xs font-medium"
    :class="{
      'bg-blue-100 text-blue-800': status === 'running',
      'bg-green-100 text-green-800': status === 'success',
      'bg-red-100 text-red-800': status === 'failed',
      'bg-neutral-200 text-neutral-700': !['running', 'success', 'failed'].includes(status)
    }"
  >
    {{ labels[status] || labels.unknown }}
  </span>
</template>
