<script lang="ts" setup>
/**
 *
 * Component Description:Desc
 *
 * @author Reflect-Media <reflect.media GmbH>
 * @version 0.0.1
 *
 * @todo [ ] Test the component
 * @todo [ ] Integration test.
 * @todo [✔] Update the typescript.
 */
import { computed } from "vue";
import type { PopoverPlacement } from "naive-ui";

interface ToolTipperProps {
  tooltipText?: string;
  placement?: PopoverPlacement;
  contentClass?: string;
}

const props = withDefaults(defineProps<ToolTipperProps>(), {
  tooltipText: "",
  placement: "bottom",
  contentClass: "",
});
const { tooltipText, placement, contentClass } = toRefs(props);
const shouldShowTooltip = computed(() => Boolean(tooltipText));
</script>

<template>
  <div v-if="shouldShowTooltip">
    <NTooltip :placement="placement" trigger="hover">
      <template #trigger>
        <div
          class="flex-center h-full rounded-lg cursor-pointer"
          :class="contentClass"
        >
          <slot />
        </div>
      </template>
      {{ tooltipText }}
    </NTooltip>
  </div>
  <div
    v-else
    class="flex-center rounded-lg cursor-pointer"
    :class="contentClass"
  >
    <slot />
  </div>
</template>

<style scoped></style>
