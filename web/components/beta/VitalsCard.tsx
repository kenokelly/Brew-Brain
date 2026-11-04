'use client';

import { Activity, BarChart3, Clock, Cpu, FlaskConical, Droplet, Thermometer } from 'lucide-react';
import type { FermentationSummary } from '@/types/api';
import { BetaCard } from './BetaCard';
import { num, sg3, signalPct } from './format';

/** Hydrometer health: signal ring plus the raw readings. */
export function VitalsCard({ s }: { s: FermentationSummary }) {
    const age = s.sensor.last_reading_age_min;
    const stale = age == null || age > 60;
    const hasRssi = s.sensor.rssi != null;
    // No RSSI (some TiltPi setups omit it): show freshness of the last reading instead
    const pct = hasRssi ? signalPct(s.sensor.rssi) : stale ? 0 : Math.round(100 - ((age ?? 0) / 60) * 100);
    const ring = stale ? 'var(--b-bad)' : pct >= 50 ? 'var(--b-good)' : 'var(--b-warn)';
    const r = 34;
    const c = 2 * Math.PI * r;

    const rows: { icon: typeof Clock; label: string; value: string }[] = [
        { icon: BarChart3, label: 'Signal', value: s.sensor.rssi != null ? `${s.sensor.rssi} dBm` : '--' },
        { icon: Clock, label: 'Last reading', value: age == null ? 'never' : age < 60 ? `${Math.round(age)}m` : age < 2880 ? `${Math.round(age / 60)}h` : `${Math.round(age / 1440)}d` },
        { icon: Thermometer, label: 'Beer temp', value: s.temp != null ? `${num(s.temp)} °${s.temp_unit || 'C'}` : '--' },
        { icon: FlaskConical, label: 'Original gravity', value: sg3(s.og) },
        { icon: Droplet, label: 'Current gravity', value: sg3(s.sg) },
        { icon: Cpu, label: 'Pi temp', value: s.sensor.pi_temp ? `${num(s.sensor.pi_temp)} °C` : '--' },
    ];

    return (
        <BetaCard icon={Activity} title="Hydrometer vitals" subtitle={s.test_mode ? 'Simulated Tilt' : 'Tilt'} live={!stale}>
            <div className="flex items-center gap-6">
                <div className="relative w-24 h-24 shrink-0">
                    <svg viewBox="0 0 80 80" className="w-full h-full -rotate-90">
                        <circle cx="40" cy="40" r={r} fill="none" stroke="var(--b-border)" strokeWidth="6" />
                        <circle
                            cx="40" cy="40" r={r} fill="none" stroke={ring} strokeWidth="6" strokeLinecap="round"
                            strokeDasharray={c} strokeDashoffset={c * (1 - (stale ? 0 : pct) / 100)}
                        />
                    </svg>
                    <div className="absolute inset-0 flex flex-col items-center justify-center">
                        <span className="beta-mono font-bold text-lg">{stale ? 'OFF' : `${pct}%`}</span>
                        <span className="text-[10px] uppercase tracking-wider text-[var(--b-muted)]">{hasRssi ? 'signal' : 'fresh'}</span>
                    </div>
                </div>
                <dl className="flex-1 space-y-1.5 text-sm">
                    {rows.map(({ icon: Icon, label, value }) => (
                        <div key={label} className="flex items-center gap-2">
                            <Icon className="w-3.5 h-3.5 text-[var(--b-accent)]" />
                            <dt className="text-[var(--b-muted)]">{label}</dt>
                            <dd className="ml-auto beta-mono font-semibold">{value}</dd>
                        </div>
                    ))}
                </dl>
            </div>
            {stale && (
                <p className="mt-4 text-sm text-[var(--b-muted)]">
                    No recent readings. Check the Tilt battery and that it&apos;s within Bluetooth range of the Pi.
                </p>
            )}
        </BetaCard>
    );
}
