/**
 * The one place a fit score turns into a colour.
 *
 * The UI is otherwise black and white on purpose; the score is the exception,
 * because scanning a list for "which of these is worth my afternoon" is the one
 * job colour does better than any amount of typography.
 */
export function scoreTone(score: number): string {
  if (score >= 0.5) return "text-green-600 dark:text-green-500";
  if (score >= 0.3) return "text-amber-600 dark:text-amber-500";
  return "text-muted-foreground";
}
