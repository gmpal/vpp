export const DEFAULT_TIME_WINDOW_MINUTES = 30;

export const TIME_WINDOW_OPTIONS: Array<{ label: string; minutes: number }> = [
  { label: "Last 5 minutes", minutes: 5 },
  { label: "Last 15 minutes", minutes: 15 },
  { label: "Last 30 minutes", minutes: 30 },
  { label: "Last 60 minutes", minutes: 60 },
  { label: "Last 180 minutes", minutes: 180 },
];

export function getTimeWindowRange(minutes: number): {
  startIso: string;
  endIso: string;
} {
  const end = new Date();
  const start = new Date(end.getTime() - minutes * 60_000);
  return {
    startIso: start.toISOString(),
    endIso: end.toISOString(),
  };
}

export function getPointLimitForWindow(minutes: number): number {
  const pointsPerMinute = 12; // 1 point every 5 seconds
  const safetyMargin = 24;
  return Math.ceil(minutes * pointsPerMinute) + safetyMargin;
}

export function formatTimeWithSeconds(timestamp: string): string {
  return new Date(timestamp).toLocaleTimeString("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}