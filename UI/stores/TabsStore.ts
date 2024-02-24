import { defineStore } from "pinia";
import type {
  RouteLocationNormalized,
  RouteRecordName,
  RouteRecordRaw,
} from "vue-router";

const APP_TABS_STORE_ID = "APP_TABS_STORE";
export const LAYOUT = () => import("~/layouts/default.vue");
export const EXCEPTION_COMPONENT = () => import("~/components/ErrorView.vue");
export const PAGE_NOT_FOUND_ROUTE: RouteRecordRaw = {
  path: "/:path(.*)*",
  name: "PageNotFound",
  component: LAYOUT,
  meta: {
    title: "ErrorPage",
    shouldHideInMenu: true,
    shouldHideBreadcrumb: true,
  },
  children: [
    {
      path: "/:path(.*)*",
      name: "PageNotFound",
      component: EXCEPTION_COMPONENT,
      meta: {
        title: "ErrorPage",
        shouldHideInMenu: true,
        shouldHideBreadcrumb: true,
      },
    },
  ],
};
export const REDIRECT_ROUTE: RouteRecordRaw = {
  path: "/redirect",
  component: LAYOUT,
  name: "RedirectTo",
  meta: {
    title: "Redirect",
    shouldHideBreadcrumb: true,
    shouldHideInMenu: true,
  },
  children: [
    {
      path: "/redirect/:path(.*)",
      name: "Redirect",
      component: () => import("~/components/RedirectView.vue"),
      meta: {
        title: "Redirect",
        shouldHideBreadcrumb: true,
      },
    },
  ],
};

export enum PageConstants {
  // basic videos path
  BASE_LOGIN = "/videos",
  // basic home path
  BASE_HOME = "/dashboard",
  // error page path
  ERROR_PAGE = "/exception",
}
interface AppTabsState {
  tabs: Tab[];
  pinnedTabs: Tab[];
  maxVisibleTabs: number;
}
export interface Tab {
  name: RouteRecordName;
  fullPath: string;
  title: string;
}
export const useTabsStore = defineStore({
  id: APP_TABS_STORE_ID,
  state: (): AppTabsState => ({
    tabs: [{ fullPath: "/", name: "Home", title: "Home" }],
    pinnedTabs: [],
    maxVisibleTabs: 3,
  }),
  getters: {
    getTabsList(state): Tab[] {
      return state.tabs;
    },
    getLimitTabsList(state): Tab[] {
      if (isGreaterOrEqual2xl.value) {
        state.maxVisibleTabs = 3;
      } else {
        state.maxVisibleTabs = 1;
      }
      return useTakeRight(
        state.tabs
          .filter(
            (tab) =>
              state.pinnedTabs.findIndex((p) => p.fullPath === tab.fullPath) ===
              -1
          )
          .reverse(),
        state.maxVisibleTabs
      );
    },
    getPinnedTabsList(state): Tab[] {
      return state.pinnedTabs;
    },
  },
  actions: {
    addTab(route: RouteLocationNormalized) {
      const { path, name, meta } = route;
      if (
        !name ||
        path === PageConstants.ERROR_PAGE ||
        path === PageConstants.BASE_LOGIN ||
        ["Redirect", "PageNotFound"].includes(name as string)
      ) {
        return;
      }
      const title =
        (meta?.title as string) || name.toString().split("-").at(-1);
      if (title) {
        const newTab: Tab = { name, fullPath: route.fullPath, title };
        this.tabs = useUniqBy([newTab, ...this.tabs], "fullPath");
      }
    },
    close(isPinned: boolean, tab: Tab) {
      const targetTabs = isPinned ? this.pinnedTabs : this.tabs;
      this.tabs = targetTabs.filter(
        (currentTab) => currentTab.fullPath !== tab.fullPath
      );
    },
    closeTab(tab: Tab) {
      this.close(false, tab);
    },
    closePinnedTab(tab: Tab) {
      this.close(true, tab);
    },
    pinnedTab(tab: Tab) {
      const isPresent = this.pinnedTabs.some(
        (pinnedTab) => pinnedTab.fullPath === tab.fullPath
      );
      if (!isPresent) {
        this.pinnedTabs = [tab, ...this.pinnedTabs];
      }
      return true;
    },
    resetTabsState() {
      this.tabs = [];
      this.pinnedTabs = [];
    },
  },
});
