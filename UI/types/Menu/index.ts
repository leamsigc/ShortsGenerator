import type { RouteMeta } from "vue-router";

export enum RoleConstants {
  ADMIN = "admin",
  USER = "user",
  GUEST = "guest",
}

export interface Menu {
  name: string;
  icon?: string;
  path: string;
  paramPath?: string;
  shouldDisabled?: boolean;
  children?: Menu[];
  orderNumber?: number;
  allowedRoles?: RoleConstants[];
  meta?: Partial<RouteMeta>;
  shouldHideMenu?: boolean;
  description?: string;
  data?: Record<string, any>;
  shouldShow?: boolean;
}
