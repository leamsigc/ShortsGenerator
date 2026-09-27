<script lang="ts" setup>
/**
 * EmptyState — reusable empty-state block.
 *
 * @author Ismael Garcia <leamsigc@leamsigc.com>
 * @version 0.0.1
 */
const props = withDefaults(defineProps<{
  icon?: string
  title: string
  description?: string
}>(), {
  icon: "ph:clipboard-text",
})

const emit = defineEmits<{ (e: "action"): void }>()
</script>

<template>
  <div class="py-16 text-center border border-clipper-ink/08 dark:border-white/08 rounded-lg">
    <Icon :name="props.icon" size="40" class="mx-auto text-clipper-ink/35 dark:text-white/40 mb-4" />
    <h3 class="text-lg font-semibold text-clipper-ink dark:text-white">{{ props.title }}</h3>
    <p v-if="props.description" class="text-sm text-clipper-ink/60 dark:text-white/60 mt-2 max-w-sm mx-auto">
      {{ props.description }}
    </p>
    <slot v-if="$slots.action" name="action" />
    <button
      v-else
      class="mt-5 h-10 px-4 rounded-lg bg-clipper-green text-ink font-semibold text-sm hover:opacity-90"
      @click="emit('action')"
    >
      {{ $slots.button || $t('clipperEmptyAction') || 'Get started' }}
    </button>
  </div>
</template>