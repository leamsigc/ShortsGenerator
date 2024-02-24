import { defineStore } from "pinia";
import type { DeepPartial } from "unocss";
import {
  type HeaderSetting,
  type MenuSetting,
  type ProjectSetting,
  type TransitionSetting,
  RouterTransitionConstants,
} from "~/types/Project/Settings";

const APP_STORE_ID = "MONEY_PRINTER";
const DEFAULT_PROJECT_SETTING = {
  shouldShowSettingButton: true,
  locale: "en",
  shouldShowFullContent: false,
  shouldShowLogo: true,
  shouldShowFooter: true,
  headerSetting: {
    shouldShow: true,
    shouldShowFullScreen: true,
    shouldShowSearch: true,
    shouldShowNotice: true,
    shouldShowSettingDrawer: false,
  },
  menuSetting: {
    collapsed: false,
  },
  transitionSetting: {
    shouldEnable: true,
    routerBasicTransition: RouterTransitionConstants.FADE,
    shouldOpenPageLoading: true,
    shouldOpenNProgress: true,
  },
  shouldOpenKeepAlive: true,
  lockTime: 0,
  shouldShowBreadCrumb: true,
  shouldShowBreadCrumbIcon: true,
  shouldUseErrorHandle: false,
  shouldUseOpenBackTop: true,
  canEmbedIFramePage: true,
  shouldCloseMessageOnSwitch: true,
  shouldRemoveAllHttpPending: false,
};
interface AppState {
  // project config
  projectSetting: ProjectSetting;
  // Page loading status
  pageLoading: boolean;
}

let pageLoadingTimeout: ReturnType<typeof setTimeout>;
export const useAppStore = defineStore({
  id: APP_STORE_ID,
  state: (): AppState => ({
    projectSetting: DEFAULT_PROJECT_SETTING,
    pageLoading: true,
  }),
  getters: {
    getPageLoading(state): boolean {
      return state.pageLoading;
    },

    getProjectSetting(state): ProjectSetting {
      return state.projectSetting || ({} as ProjectSetting);
    },

    getMenuSetting(): MenuSetting {
      return this.getProjectSetting.menuSetting;
    },

    getHeaderSetting(): HeaderSetting {
      return this.getProjectSetting.headerSetting;
    },

    getTransitionSetting(): TransitionSetting {
      return this.getProjectSetting.transitionSetting;
    },
  },
  actions: {
    setPageLoading(loading: boolean): void {
      this.pageLoading = loading;
    },

    setProjectSetting(config: DeepPartial<ProjectSetting>): void {
      //Merge the current config with the default config
      this.projectSetting = {
        ...this.projectSetting,
        ...config,
      } as ProjectSetting;
    },

    setMenuSetting(menuSetting: Partial<MenuSetting>): void {
      this.setProjectSetting({ menuSetting });
    },

    setHeaderSetting(headerSetting: Partial<HeaderSetting>): void {
      this.setProjectSetting({ headerSetting });
    },

    setTransitionSetting(transitionSetting: Partial<TransitionSetting>): void {
      this.setProjectSetting({ transitionSetting });
    },

    setPageLoadingAction(loading: boolean) {
      clearTimeout(pageLoadingTimeout);
      if (loading) {
        // Prevent flicker by delaying the setPageLoading call
        pageLoadingTimeout = setTimeout(() => {
          this.setPageLoading(loading);
        }, 50);
      } else {
        this.setPageLoading(loading);
      }
    },

    resetAPPState() {
      this.setProjectSetting(DEFAULT_PROJECT_SETTING);
    },
  },
});
