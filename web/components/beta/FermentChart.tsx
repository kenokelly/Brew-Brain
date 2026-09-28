'use client';

import { useState } from 'react';
import { LineChart as LineIcon } from 'lucide-react';
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { cn } from '@/lib/utils';
import type { FermentationHistory, FermentationSummary } from '@/types/api';
import { BetaCard, CardError } from './BetaCard';
import { num, sg3 } from './format';

type SeriesKey = 'sg' | 'temp' | 'target' | 'velocity' | 'abv';

const SERIES: { key: SeriesKey; label: string; color: string; axis: string; step?: boolean; unit: string }[] = [
    { key: 'sg', label: 'Gravity', color: 'var(--b-gravity)', axis: 'sg', unit: '' },
    { key: 'temp', label: 'Beer °C', color: 'var(--b-temp)', axis: 'temp', unit: '°C' },
    { key: 'target', label: 'Target', color: 'var(--b-target)', axis: 'temp', step: true, unit: '°C' },
    { key: 'velocity', label: 'Velocity', color: 'var(--b-velocity)', axis: 'vel', unit: ' pts/d' },
    { key: 'abv', label: 'ABV', color: 'var(--b-abv)', axis: 'abv', unit: '%' },
];

const dayFmt = (ts: number) => {
    const d = new Date(ts * 1000);
    return `${d.getDate()}/${d.getMonth() + 1}`;
};

/** Whole-ferment chart since pitch, one colour per series (Grafana-free). */
export function FermentChart({ history, summary, error }: {
    history?: FermentationHistory;
    summary?: FermentationSummary;
    error?: unknown;
}) {
    const [hidden, setHidden] = useState<Set<SeriesKey>>(new Set());
    const points = history?.points ?? [];
    const toggle = (k: SeriesKey) =>
        setHidden((h) => {
            const n = new Set(h);
            if (n.has(k)) n.delete(k); else n.add(k);
            return n;
        });

    const og = history?.og ?? summary?.og ?? 1.05;
    const fg = summary?.target_fg ?? 1.01;
    const sgDomain: [number, number] = [
        Math.min(fg, ...points.map((p) => p.sg ?? 9)) - 0.002,
        Math.max(og, ...points.map((p) => p.sg ?? 0)) + 0.002,
    ];
    // Recharts' automatic ticks come out empty over a ~0.06 SG range, so
    // lay out five explicitly.
    const sgTicks = Array.from({ length: 5 }, (_, i) => sgDomain[0] + ((sgDomain[1] - sgDomain[0]) * i) / 4);
    const vels = points.map((p) => p.velocity).filter((v): v is number => v != null);
    const avgVel = vels.length ? vels.reduce((a, b) => a + b, 0) / vels.length : null;

    return (
        <BetaCard icon={LineIcon} title="Fermentation chart" subtitle="this ferment · since OG" live={points.length > 0}>
            <div className="flex flex-wrap gap-x-4 gap-y-1.5 mb-3">
                {SERIES.map((s) => (
                    <button
                        key={s.key}
                        type="button"
                        onClick={() => toggle(s.key)}
                        aria-pressed={!hidden.has(s.key)}
                        className={cn('flex items-center gap-1.5 text-sm transition-opacity', hidden.has(s.key) && 'opacity-35')}
                    >
                        <span className="w-4 h-1 rounded-full" style={{ background: s.color }} />
                        <span className="text-[var(--b-muted)]">{s.label}</span>
                    </button>
                ))}
            </div>

            {error ? (
                <CardError message="Chart data unavailable. Is InfluxDB reachable?" />
            ) : points.length === 0 ? (
                <CardError message="No readings since pitch yet. The chart fills in once the hydrometer reports." />
            ) : (
                <div className="h-64 md:h-72 -mx-2">
                    <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={points} margin={{ top: 4, right: 4, bottom: 0, left: 4 }}>
                            <CartesianGrid stroke="var(--b-border)" strokeDasharray="2 6" vertical={false} />
                            <XAxis
                                dataKey="ts" type="number" domain={['dataMin', 'dataMax']} scale="time"
                                tickFormatter={dayFmt} stroke="var(--b-faint)" tick={{ fontSize: 11 }} minTickGap={40}
                            />
                            <YAxis
                                yAxisId="sg" domain={sgDomain} ticks={sgTicks} tickFormatter={(v) => v.toFixed(3)}
                                stroke="var(--b-faint)" tick={{ fontSize: 11 }} width={48}
                            />
                            <YAxis
                                yAxisId="temp" orientation="right" domain={['dataMin - 2', 'dataMax + 2']}
                                tickFormatter={(v) => `${Math.round(v)}°`} stroke="var(--b-faint)" tick={{ fontSize: 11 }} width={32}
                            />
                            <YAxis yAxisId="vel" hide orientation="right" width={0} domain={["dataMin", "dataMax"]} />
                            <YAxis yAxisId="abv" hide orientation="right" width={0} domain={[0, "dataMax"]} />
                            <Tooltip
                                contentStyle={{ background: 'var(--b-card-hi)', border: '1px solid var(--b-border)', borderRadius: 12, fontSize: 12 }}
                                labelFormatter={(ts) => new Date(Number(ts) * 1000).toLocaleString([], { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}
                                formatter={(value, name) => {
                                    const s = SERIES.find((x) => x.label === name);
                                    const n = Number(value);
                                    return [s?.key === 'sg' ? n.toFixed(4) : `${n.toFixed(s?.key === 'abv' ? 2 : 1)}${s?.unit ?? ''}`, name];
                                }}
                            />
                            {SERIES.filter((s) => !hidden.has(s.key)).map((s) => (
                                <Line
                                    key={s.key} yAxisId={s.axis} dataKey={s.key} name={s.label}
                                    stroke={s.color} strokeWidth={s.key === 'sg' ? 2.5 : 1.5}
                                    type={s.step ? 'stepAfter' : 'monotone'} dot={false} connectNulls isAnimationActive={false}
                                />
                            ))}
                        </LineChart>
                    </ResponsiveContainer>
                </div>
            )}

            <div className="flex flex-wrap gap-x-5 gap-y-1 mt-4 text-sm text-[var(--b-muted)]">
                <span>OG <b className="beta-mono text-[var(--b-text)]">{sg3(og)}</b></span>
                <span>SG <b className="beta-mono text-[var(--b-text)]">{sg3(summary?.sg)}</b></span>
                <span>ABV <b className="beta-mono text-[var(--b-text)]">{num(summary?.abv)}%</b></span>
                <span>Att <b className="beta-mono text-[var(--b-text)]">{num(summary?.attenuation, 0)}%</b></span>
                <span>Avg vel <b className="beta-mono text-[var(--b-text)]">{num(avgVel)} pts/d</b></span>
            </div>
        </BetaCard>
    );
}
