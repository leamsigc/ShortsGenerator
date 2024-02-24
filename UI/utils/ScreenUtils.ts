import { breakpointsTailwind, useBreakpoints } from "@vueuse/core";

export const breakpoints = useBreakpoints(breakpointsTailwind);
export const isMediumOrLargeScreen = breakpoints.between("sm", "xl");
export const isExtraLargeScreen = breakpoints.smallerOrEqual("xl");
export const isSmallerOrEqualSm = breakpoints.smallerOrEqual("sm");
export const isSmallerOrEqualMd = breakpoints.smallerOrEqual("md");
export const isSmallerOrEqualLg = breakpoints.smallerOrEqual("lg");
export const isSmallerOrEqualXl = breakpoints.smallerOrEqual("xl");
export const isSmallerOrEqual2xl = breakpoints.smallerOrEqual("2xl");
export const isGreaterOrEqualSm = breakpoints.greaterOrEqual("sm");
export const isGreaterOrEqualMd = breakpoints.greaterOrEqual("md");
export const isGreaterOrEqualLg = breakpoints.greaterOrEqual("lg");
export const isGreaterOrEqualXl = breakpoints.greaterOrEqual("xl");
export const isGreaterOrEqual2xl = breakpoints.greaterOrEqual("2xl");
