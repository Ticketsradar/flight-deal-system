/**
 * freshnessLabel — pure ISO timestamp → 廣東話 relative-age label
 * No React, no external deps. Safe on server and client.
 */
export function freshnessLabel(iso: string | null | undefined): string {
  if (!iso) return "更新時間未知";

  const parsed = new Date(iso);
  if (isNaN(parsed.getTime())) return "更新時間未知";

  const diffMs = Date.now() - parsed.getTime();
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffDays <= 0) return "今日更新";
  if (diffDays === 1) return "更新於 1 日前";
  return `更新於 ${diffDays} 日前`;
}
