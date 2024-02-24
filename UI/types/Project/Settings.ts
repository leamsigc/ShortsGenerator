export enum RouterTransitionConstants {
  /**
   * A transition that zooms in and fades out the previous route, then zooms out and fades in the new route.
   */
  ZOOM_FADE = "zoom-fade",

  /**
   * A transition that zooms out and fades out the previous route, then fades in the new route.
   */
  ZOOM_OUT = "zoom-out",

  /**
   * A transition that fades out the previous route to the side, then fades in the new route from the opposite side.
   */
  FADE_SLIDE = "fade-slide",

  /**
   * A simple fade transition.
   */
  FADE = "fade",

  /**
   * A transition that fades out the previous route to the bottom, then fades in the new route from the bottom.
   */
  FADE_BOTTOM = "fade-bottom",

  /**
   * A transition that scales down and fades out the previous route, then scales up and fades in the new route.
   */
  FADE_SCALE = "fade-scale",
}

export interface TransitionSetting {
  // Whether to open the page switching animation
  shouldEnable: boolean;
  // Route basic switching animation
  routerBasicTransition: RouterTransitionConstants;
  // Whether to open page switching loading
  shouldOpenPageLoading: boolean;
  // Whether to open the top progress bar
  shouldOpenNProgress: boolean;
}

export interface HeaderSetting {
  // Whether to display the website header
  shouldShow: boolean;
  // Whether to display the full screen button
  shouldShowFullScreen: boolean;
  // Whether to display the search
  shouldShowSearch: boolean;
  // Whether to display the notice
  shouldShowNotice: boolean;
  // Whether to display the setting drawer
  shouldShowSettingDrawer: boolean;
}
export interface MenuSetting {
  collapsed: boolean;
}
export interface ProjectSetting {
  // Whether to display the setting button
  shouldShowSettingButton: boolean;
  // The locale
  locale: string;
  // Whether to display the dark mode toggle button
  // Whether to display the main interface in full screen, without menu and top bar
  shouldShowFullContent: boolean;
  // Whether to display the logo
  shouldShowLogo: boolean;
  // Whether to display the global footer
  shouldShowFooter: boolean;
  // The header setting
  headerSetting: HeaderSetting;
  // The menu setting
  menuSetting: MenuSetting;
  // The animation configuration
  transitionSetting: TransitionSetting;
  // Whether to enable keep-alive for page layout
  shouldOpenKeepAlive: boolean;
  // The lock screen time
  lockTime: number;
  // Whether to display the breadcrumb
  shouldShowBreadCrumb: boolean;
  // Whether to display the breadcrumb icon
  shouldShowBreadCrumbIcon: boolean;
  // Whether to use the error-handler-plugin
  shouldUseErrorHandle: boolean;
  // Whether to enable the back to top function
  shouldUseOpenBackTop: boolean;
  // Whether to embed iframe pages
  canEmbedIFramePage: boolean;
  // Whether to delete unclosed messages and notify when switching pages
  shouldCloseMessageOnSwitch: boolean;
  // Whether to cancel sent but unresponsive http requests when switching pages
  shouldRemoveAllHttpPending: boolean;
}

export enum SettingButtonPositionConstants {
  // Automatically adjust according to menu type
  AUTO = "auto",
  // Display in the top menu bar
  HEADER = "header",
  // Fixed display in the lower right corner
  FIXED = "fixed",
}
