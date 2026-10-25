/** Sage-forward palette for Recharts (matches ZooLog UI tokens). */
export const BEHAVIOR_COLORS: Record<string, string> = {
  eating: "#4a6a50",
  resting: "#6d8f72",
  walking: "#a3bda6",
  swimming: "#5b8a9a",
  climbing: "#8a7a5b",
  playing: "#c4a574",
  not_visible: "#9aa39a",
  unknown: "#b0b8b0",
};

export const FALLBACK_COLORS = [
  "#4a6a50",
  "#6d8f72",
  "#a3bda6",
  "#5b8a9a",
  "#8a7a5b",
  "#c4a574",
  "#9aa39a",
  "#7d8f7a",
];

export function colorForBehavior(behavior: string, index = 0): string {
  return (
    BEHAVIOR_COLORS[behavior] ??
    FALLBACK_COLORS[index % FALLBACK_COLORS.length]
  );
}

export function formatBehavior(behavior: string): string {
  return behavior.replaceAll("_", " ");
}
