export enum OperatingSystem {
  Windows = "Windows",
  MacOS = "MacOS",
  UNIX = "UNIX",
  Linux = "Linux",
  Unknown = "Unknown",
}
export type OS = keyof typeof OperatingSystem;
export function detectOperatingSystem(): OS {
  const { userAgent } = navigator || { userAgent: "" };
  if (userAgent.includes("Win")) {
    return OperatingSystem.Windows;
  }
  if (userAgent.includes("Mac")) {
    return OperatingSystem.MacOS;
  }
  if (userAgent.includes("X11")) {
    return OperatingSystem.UNIX;
  }
  if (userAgent.includes("Linux")) {
    return OperatingSystem.Linux;
  }

  return OperatingSystem.Unknown;
}
export function isWindows(): boolean {
  return detectOperatingSystem() === OperatingSystem.Windows;
}
