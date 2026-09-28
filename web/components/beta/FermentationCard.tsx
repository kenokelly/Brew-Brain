'use client';

import { Pill, TrendingDown, TrendingUp, Minus } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { FermentationPhase, FermentationSummary } from '@/types/api';
import { BetaCard } from './BetaCard';
import { duration, num, sg3 } from './format';

const PHASE_STYLE: Record<FermentationPhase, string> = {
    ACTIVE: 'text-[var(--b-good)] bg-[var(--b-good)]/15',
    SLOWING: 'text-[var(--b-warn)] bg-[var(--b-warn)]/15',
    STABLE: 'text-[var(--b-info)] bg-[var(--b-info)]/15',
    STALLED: 'text-[var(--b-bad)] bg-[var(--b-bad)]/15',
    LAG: 'text-[var(--b-muted)] bg-[var(--b-card-hi)]',
    'NO DATA': 'text-[var(--b-muted)] bg-[var(--b-card-hi)]',
};

/** Headline gravity, velocity, OG→FG progress and the three derived stats. */
export function FermentationCard({ s }: { s: FermentationSummary }) {
    const og = s.og;
    const fg = s.target_fg;
    const progress = s.sg != null && og > fg ? Math.min(1, Math.max(0, (og - s.sg) / (og - fg))) : 0;
    const v = s.velocity;
    const VIcon = v == null || Math.abs(v) < 0.2 ? Minus : v < 0 ? TrendingDown : TrendingUp;
    const stale = (s.sensor.last_reading_age_min ?? Infinity) > 60;

    return (
        <BetaCard
            icon={Pill}
            title="Fermentation"
            subtitle={s.test_mode ? 'Test mode · simulated' : 'Tilt hydrometer'}
            live={!stale}
            badge={
                <span className={cn('px-3 py-1 rounded-full text-xs font-bold tracking-wider', PHASE_STYLE[s.phase])}>
                    {s.phase}
                </span>
            }
        >
            <div className="flex items-baseline gap-3 flex-wrap">
                <span className="beta-mono text-6xl md:text-7xl font-bold tracking-tighter">{sg3(s.sg)}</span>
                <span className="flex items-center gap-1 text-[var(--b-accent)] beta-mono font-semibold">
                    <VIcon className="w-4 h-4" />
                    {v == null ? '--' : num(Math.abs(v))} pts/day
                </span>
            </div>

            <div className="mt-5">
                <div className="relative h-2.5 rounded-full bg-[var(--b-border)]">
                    <div
                        className="absolute inset-y-0 left-0 rounded-full bg-gradient-to-r from-[var(--b-accent)]/60 to-[var(--b-accent)]"
                        style={{ width: `${progress * 100}%` }}
                    />
                    <div
                        className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-5 h-5 rounded-full bg-white border-4 border-[var(--b-card)] shadow"
                        style={{ left: `${progress * 100}%` }}
                    />
                </div>
                <div className="flex justify-between mt-2 text-sm text-[var(--b-muted)]">
                    <span>OG <span className="beta-mono text-[var(--b-text)]">{sg3(og)}</span></span>
                    <span>FG <span className="beta-mono text-[var(--b-text)]">{sg3(fg)}</span></span>
                </div>
            </div>

            <div className="grid grid-cols-3 gap-2 mt-5">
                <Stat value={s.attenuation != null ? `${num(s.attenuation, 0)}%` : '--'} label="Attenuation" />
                <Stat value={s.abv != null ? `${num(s.abv)}%` : '--'} label="ABV now" />
                <Stat
                    value={s.eta_days == null ? '--' : s.eta_days === 0 ? 'At FG' : `~${duration(s.eta_days)}`}
                    label="ETA to FG"
                />
            </div>
        </BetaCard>
    );
}

function Stat({ value, label }: { value: string; label: string }) {
    return (
        <div className="rounded-xl bg-[var(--b-card-hi)] py-3 px-2 text-center">
            <div className="beta-mono text-xl md:text-2xl font-bold">{value}</div>
            <div className="text-[10px] md:text-xs font-semibold tracking-wider uppercase text-[var(--b-muted)] mt-1">{label}</div>
        </div>
    );
}
