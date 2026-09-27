<script lang="ts" setup>
import type { ElahEditor } from "~/composables/useElahEditor"

const props = defineProps<{ elah: ElahEditor }>()

const FOO = "bar"
const lbl = computed(() => props.elah.project.value.fps)
</script>

<template>
  <div>{{ FOO }} {{ lbl }} {{ elah.timecode.value }}</div>
</template>
