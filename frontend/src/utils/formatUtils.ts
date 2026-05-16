export const formatNumber = (num: number | undefined | null): string => {
  if (num === undefined || num === null) return '0';
  if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
  if (num >= 1000) return (num / 1000).toFixed(1) + 'k';
  return num.toString();
};

export const formatCurrency = (num: number | undefined | null): string => {
  if (num === undefined || num === null || num === 0) return '$0.00';
  if (num < 0.01) return '<$0.01';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
  }).format(num);
};

/**
 * Format an ISO-8601 timestamp string for display in the user's locale.
 *
 * Falls back to the raw input on parse failure so the UI never shows "Invalid
 * Date" for an unexpected payload — useful for the audit log + system health
 * panels where the source is the backend and any drift would be a regression
 * we'd rather see verbatim than silently mask.
 */
export const formatTimestamp = (iso: string): string => {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
};
