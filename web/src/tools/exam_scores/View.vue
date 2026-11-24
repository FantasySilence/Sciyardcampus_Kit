<!--
  View.vue（测试成绩登记，占位）

  本期只提供占位页：不写假数据、不弹假成功。
  后端 exam_scores.check 明确返回 available=false；
  后续接真实接口时补 actions.py 与本页即可。
-->
<script setup lang="ts">
import type { ToolDef } from '../../platform/types'
import ComingSoon from '../../ui/ComingSoon.vue'

defineProps<{ tool: ToolDef }>()
</script>

<template>
  <ComingSoon :tool="tool" prefix="examScores" />
</template>
