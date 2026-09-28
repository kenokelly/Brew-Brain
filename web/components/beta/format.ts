/** Formatting helpers for the beta dashboard. */

export const sg3 = (v: number | null | undefined) => (v == null ? '-.---' : v.toFixed(3));

export const num = (v: number | null | undefined, digits = 1, fallback = '--') =>
    v == null || Number.isNaN(v) ? fallback : v.toFixed(digits);

/** Days as "2.3d", or hours when under a day ("18h"). */
export function duration(days: number | null | undefined): string {
    if (days == null) return '--';
    if (days < 1) return `${Math.max(0, Math.round(days * 24))}h`;
    return `${days.toFixed(1)}d`;
}

/** "5m" / "16h" / "3d" since an ISO timestamp. */
export function ago(iso: string | null | undefined, now = Date.now()): string {
    if (!iso) return '--';
    const mins = Math.max(0, (now - new Date(iso).getTime()) / 60000);
    if (mins < 60) return `${Math.round(mins)}m`;
    if (mins < 60 * 48) return `${Math.round(mins / 60)}h`;
    return `${Math.round(mins / 1440)}d`;
}

/** Tilt RSSI to a 0-100 bar: -100 dBm is unusable, -50 dBm is excellent. */
export const signalPct = (rssi: number | null | undefined) =>
    rssi == null ? 0 : Math.round(Math.min(100, Math.max(0, ((rssi + 100) / 50) * 100)));
