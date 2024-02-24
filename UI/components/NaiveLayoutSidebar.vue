<template>
  <n-layout style="min-height: 100vh; min-height: 100dvh">
    <n-layout-header
      bordered
      style="
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 16px;
        height: 56px;
        padding: 0 16px;
      "
      class="layout-header"
    >
      <slot name="start" />
      <div style="flex: 1" />
      <slot name="end" />
      <n-button
        class="mobileOrTablet"
        text
        aria-label="drawer-toggle-btn"
        :focusable="false"
        @click="drawerActive = true"
      >
        <NaiveIcon :name="toggleIcon" :size="26" />
      </n-button>
    </n-layout-header>

    <n-layout
      position="absolute"
      :has-sider="!isMobileOrTablet"
      style="top: 56px"
      class="layout-content"
    >
      <n-layout-sider
        v-if="!isMobileOrTablet && showSider"
        class="notMobileOrTablet"
        content-style="min-height:100%;display:flex;flex-direction:column;justify-content:space-between;gap:16px;padding:8px;"
        :native-scrollbar="false"
        bordered
      >
        <slot name="start" />
        <div style="flex: 1">
          <LazyNaiveMenuLink :routes="routes" mode="vertical" />
        </div>
        <slot name="end" />
      </n-layout-sider>

      <n-layout
        content-style="padding: 16px;"
        :native-scrollbar="nativeScrollbar"
      >
        <slot />
      </n-layout>
    </n-layout>

    <LazyNaiveDrawerLink
      v-model:show="drawerActive"
      :routes="drawerRoutes"
      :placement="drawerPlacement"
      :closable="drawerClosable"
      :width="drawerWidth"
    >
      <template #header>
        <slot name="drawer-header" />
      </template>
      <template #footer>
        <slot name="drawer-footer" />
      </template>
    </LazyNaiveDrawerLink>
  </n-layout>
</template>

<script setup lang="ts">
import { ref, useNaiveDevice } from "#imports";
import type { MenuLinkRoute } from "@bg-dev/nuxt-naiveui";

withDefaults(
  defineProps<{
    toggleIcon?: string;
    routes?: MenuLinkRoute[];
    drawerRoutes?: MenuLinkRoute[];
    drawerPlacement?: "top" | "right" | "bottom" | "left";
    drawerClosable?: boolean;
    drawerWidth?: string | number;
    nativeScrollbar?: boolean;
    showSider?: boolean;
  }>(),
  {
    toggleIcon: "ph:equals",
    routes: () => [],
    drawerRoutes: () => [],
    drawerClosable: true,
    drawerPlacement: "left",
    drawerWidth: "100%",
    nativeScrollbar: false,
    showSider: true,
  }
);

const { isMobileOrTablet } = useNaiveDevice();
const drawerActive = ref(false);
</script>

<style scoped>
@media screen and (min-width: 768px) {
  .layout-header {
    display: none !important;
  }
  .layout-content {
    top: 0 !important;
  }
}
</style>
