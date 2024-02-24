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
import type { MenuLinkRoute } from "@bg-dev/nuxt-naiveui";

const menuOptions: MenuLinkRoute[] = [
  {
    label: "Settings",
    path: "/settings",
    icon: "mdi:gamepad-circle",
  },
  {
    label: "Generate script",
    path: "/",
    icon: "mdi:script-text-outline",
  },
  {
    label: "Generated videos",
    icon: "material-symbols:slow-motion-video-rounded",
    path: "/videos",
  },
  {
    label: "Documentation",
    icon: "material-symbols:description-rounded",
    path: "/docs",
  },
];

/*----------  Menu state   ----------*/
const { getCollapsed } = useMenuSetting();
</script>

<template>
  <NEl tag="div" class="flex flex-col flex-1 h-full w-full">
    <NaiveLayoutSidebar
      :routes="menuOptions"
      :drawer-closable="true"
      :drawer-routes="menuOptions"
      :show-sider="false"
    >
      <n-layout position="absolute">
        <n-layout-header
          style="height: 64px"
          :bordered="false"
          class="bg-transparent px-10"
        >
          <HeaderLayout />
        </n-layout-header>
        <n-layout position="absolute" style="top: 64px; bottom: 64px">
          <n-layout content-style="padding: 24px;">
            <slot />
          </n-layout>
        </n-layout>
        <n-layout-footer
          :bordered="false"
          position="absolute"
          style="height: 64px; padding: 24px"
        >
          Money Printer UI
        </n-layout-footer>
      </n-layout>
    </NaiveLayoutSidebar>
    <SearchDialog />
  </NEl>
</template>
<style scoped></style>
