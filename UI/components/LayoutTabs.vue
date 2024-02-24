<script lang="ts" setup>
import { RouterTransitionConstants } from "~/types/Project/Settings";

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
const router = useRouter();

function getLimitTabsList() {
  return [
    {
      title: "settings",
      fullPath: "/settings",
      name: "settings",
      icon: "mdi:gamepad-circle",
    },
  ];
}
function getPinnedTabsList() {
  return [
    {
      title: "Generate",
      fullPath: "/generate",
      name: "generate",
      icon: "mdi:script-text-outline",
    },
    {
      title: "Videos",
      fullPath: "/videos",
      name: "generate",
      icon: "material-symbols:slow-motion-video-rounded",
    },
    {
      title: "Documentation",
      fullPath: "/docs",
      name: "generate",
      icon: "material-symbols:description-rounded",
    },
  ];
}

function go(fullPath: string) {
  router.push({ path: fullPath });
  return true;
}
const { t, te } = useI18n();
function localize(key: string) {
  return te(key) ? t(key) : key;
}
console.log("LayoutTabs.vue");

// listenToRouteChange((route) => {
//   addTab(route);
// });
</script>

<template>
  <div class="flex layout-tags items-end">
    <TransitionGroup
      :name="RouterTransitionConstants.FADE"
      tag="div"
      class="latest-list flex items-center gap-4"
    >
      <NTag
        v-for="tab of getLimitTabsList()"
        :key="tab.fullPath"
        round
        :bordered="false"
        class="bg-transparent"
      >
        <span class="router-name" @click="go(tab.fullPath)">
          {{ localize(tab.title) }}
        </span>
        <template #icon>
          <div
            class="hover:color-primary-color hover:bg-[var(--action-color)] cursor-pointer mr-1 transition"
          >
            <Icon size="14" name="tabler:pinned" />
          </div>
        </template>
      </NTag>
    </TransitionGroup>

    <div
      v-if="getLimitTabsList().length && getPinnedTabsList().length"
      class="divider-point h-1 w-1 relative top-2 z-1 rounded-full opacity-90 bg-primary-color mx-2"
    />
    <TransitionGroup
      :name="RouterTransitionConstants.FADE"
      tag="div"
      class="pinned-list flex items-center gap-2"
    >
      <NTag
        v-for="tab of getPinnedTabsList()"
        :key="tab.name"
        round
        :bordered="false"
        class="bg-transparent"
      >
        <div class="router-name" @click="go(tab.fullPath)">
          {{ localize(tab.title) }}
        </div>
        <template #icon>
          <div
            class="hover:color-primary-color hover:bg-[var(--action-color)] cursor-pointer mr-1 transition"
          >
            <Icon size="14" :name="tab.icon" />
          </div>
        </template>
      </NTag>
    </TransitionGroup>
    <div
      class="bar absolute bottom-[-0.5rem] bg-action-color rounded-2xl left-0 w-full h-1"
    />
  </div>
</template>

<style scoped>
.layout-tags {
  position: relative;
}
.layout-tags :deep(.ca-tag) {
  background-color: transparent;
}

.pinned-list :deep(.ca-tag) {
  background-color: var(--action-color);
}

.layout-tags :deep(.ca-tag).ca-tag--round {
  padding: 0.5rem;
  transition-property: all;
  transition-timing-function: cubic-bezier(0.4, 0, 0.2, 1);
  transition-duration: 400ms;
}
.layout-tags :deep(.ca-tag) .ca-tag__icon {
  margin: 0 !important;
}
.layout-tags :deep(.ca-tag) .ca-tag__close {
  overflow: hidden;
  width: 0;
  margin-left: 0;
  margin-right: 0;
  transition-property: all;
  transition-timing-function: cubic-bezier(0.4, 0, 0.2, 1);
  transition-duration: 400ms;
}
.layout-tags :deep(.ca-tag):hover {
  background-color: var(--action-color);
}
.layout-tags :deep(.ca-tag):hover.ca-tag--round {
  padding: 0 calc(var(--n-height) / 3) 0 calc(var(--n-height) / 3);
}
.layout-tags :deep(.ca-tag):hover .ca-tag__close {
  margin-left: 0.25rem;
  overflow: unset;
  width: 1rem;
}
.layout-tags :deep(.ca-tag) .ca-base-icon {
  transform: unset;
}

.layout-tags .router-name {
  cursor: pointer;
  margin-left: 0.25rem;
  margin-right: 0.25rem;
}
.layout-tags .current-tab {
  text-decoration: underline;
  text-decoration-thickness: 0.1rem;
  text-decoration-color: var(--primary-color);
}
</style>
