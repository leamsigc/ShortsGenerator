import type { MenuSetting } from "~/types/Project/Settings";

export function useMenuSetting() {
  console.log("useMenuSetting");

  const appStore = useAppStore();

  const getCollapsed = computed(() => appStore.getMenuSetting.collapsed);

  function getMenuSetting() {
    return appStore.getMenuSetting;
  }

  // Set menu configuration
  function setMenuSetting(menuSetting: Partial<MenuSetting>): void {
    appStore.setProjectSetting({ menuSetting });
  }

  function toggleCollapsed() {
    console.log("toggleCollapsed");

    setMenuSetting({
      collapsed: !unref(getCollapsed),
    });
  }
  return {
    getMenuSetting,
    setMenuSetting,
    getCollapsed,
    toggleCollapsed,
  };
}
