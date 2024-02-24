import type {
  RouteLocationNormalized,
  RouteRecordNormalized,
} from "vue-router";

export function getRawRoute(
  route: RouteLocationNormalized
): RouteLocationNormalized {
  if (!route) {
    return route;
  }
  const { matched, ...otherProps } = route;
  return {
    ...otherProps,
    matched: matched?.map(({ meta, name, path }) => ({
      meta,
      name,
      path,
    })) as RouteRecordNormalized[],
  };
}

const key = Symbol("route change event");
const emitter = mitt<{ [key]: RouteLocationNormalized }>();
let lastTab: RouteLocationNormalized;

export function notifyRouteChange(newRoute: RouteLocationNormalized) {
  const rawRoute = getRawRoute(newRoute);
  emitter.emit(key, rawRoute);
  lastTab = rawRoute;
}

export function listenToRouteChange(
  callback: (route: RouteLocationNormalized) => void,
  immediate = true
) {
  emitter.on(key, callback);
  immediate && lastTab && callback(lastTab);
}

export function removeRouteChangeListener() {
  emitter.all.clear();
}
