/** Hash a primary key record into a stable string key for Maps and React keys. */
export function hashPK(primaryKey: Record<string, any>): string {
  return Object.entries(primaryKey)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([k, v]) => `${k}=${v}`)
    .join('|');
}
