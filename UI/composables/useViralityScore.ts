/**
 * Composable: useViralityScore
 *
 * Utility helpers for formatting and visualising virality scores.
 */
export function useViralityScore() {
  // Per STYLEGUIDE §21: Use only Ink + Nuxt Green. No rainbow traffic lights.
  const scoreColor = (score: number): string => {
    if (score >= 80) return "text-clipper-ink";
    if (score >= 60) return "text-clipper-ink";
    if (score >= 40) return "text-clipper-ink/60";
    return "text-clipper-ink/35";
  };

  const scoreBgColor = (score: number): string => {
    // Active track is always Green; visual difference is opacity/length, not hue
    return "bg-clipper-green";
  };

  const scoreHexColor = (score: number): string => {
    // Always return Nuxt Green; length of bar communicates value, not hue
    return "#00DC82";
  };

  const scoreLabel = (score: number): string => {
    if (score >= 80) return "Excellent";
    if (score >= 60) return "Good";
    if (score >= 40) return "Average";
    return "Low";
  };

  const formatScore = (score: number | undefined): string => {
    if (score === undefined || score === null) return "—";
    return score.toFixed(1);
  };

  const scoreBar = (score: number, label: string) => ({
    label,
    value: score,
    colorClass: scoreColor(score),
    bgClass: scoreBgColor(score),
  });

  return {
    scoreColor,
    scoreBgColor,
    scoreHexColor,
    scoreLabel,
    formatScore,
    scoreBar,
  };
}
