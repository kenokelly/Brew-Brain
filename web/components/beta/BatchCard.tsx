'use client';

import { Beer, CalendarDays, Layers, SkipForward, Thermometer, Timer, RefreshCcw } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { FermentationSummary } from '@/types/api';
import { BetaCard } from './BetaCard';
import { duration, num } from './format';

/** Batch + recipe step timeline (Brewfather fermentation profile). */
export function BatchCard({ s, onSync, syncing }: { s: FermentationSummary; onSync: () => void; syncing: boolean }) {
    const sched = s.schedule;
    const steps = sched?.steps ?? [];
    const idx = sched?.current_index ?? -1;
    const cur = sched?.current;
    const nxt = sched?.next;

    // Countdown chip: cold crash if one is coming, otherwise end of schedule.
    let countdown: string | null = null;
    if (sched) {
        if (sched.days_to_crash != null && sched.days_to_crash > 0) countdown = `${duration(sched.days_to_crash)} to cold crash`;
        else if (sched.days_to_end > 0) countdown = `${duration(sched.days_to_end)} to packaging`;
        else countdown = 'Ready to package';
    }

    const delta = s.temp_delta;
    const deltaColor = delta == null ? '' : Math.abs(delta) <= 1 ? 'text-[var(--b-good)]' : Math.abs(delta) <= 3 ? 'text-[var(--b-warn)]' : 'text-[var(--b-bad)]';

    return (
        <BetaCard
            icon={Beer}
            title="Batch"
            subtitle="Brewfather"
            live={s.brew_active}
            badge={
                <button
                    type="button"
                    onClick={onSync}
                    disabled={syncing}
                    aria-label="Sync from Brewfather"
                    className="p-2 rounded-lg text-[var(--b-muted)] hover:text-[var(--b-text)] hover:bg-[var(--b-card-hi)] disabled:opacity-50"
                >
                    <RefreshCcw className={cn('w-4 h-4', syncing && 'animate-spin')} />
                </button>
            }
        >
            <h1 className="text-2xl md:text-[28px] font-bold tracking-tight leading-tight">{s.batch_name || 'No batch'}</h1>
            <p className="text-[var(--b-accent)] font-medium mt-0.5">
                {[s.style, s.yeast].filter((v) => v && v !== 'Unknown').join(' · ') || 'Style unknown'}
            </p>

            {steps.length > 0 ? (
                <div className="flex gap-1.5 mt-4" aria-label={`Step ${idx + 1} of ${steps.length}`}>
                    {steps.map((step, i) => (
                        <div
                            key={i}
                            title={`${step.name}${step.temp != null ? ` @ ${step.temp}°C` : ''} · ${step.days}d`}
                            className={cn(
                                'h-2 flex-1 rounded-full',
                                i < idx ? 'bg-[var(--b-accent)]' : i === idx ? 'bg-[var(--b-accent)] animate-pulse-soft' : 'bg-[var(--b-border)]',
                            )}
                        />
                    ))}
                </div>
            ) : (
                <p className="mt-4 text-sm text-[var(--b-muted)]">
                    No fermentation schedule yet. Sync from Brewfather to load the recipe steps.
                </p>
            )}

            <ul className="mt-4 space-y-2.5 text-[15px]">
                {cur && (
                    <li className="flex items-center gap-2.5">
                        <Layers className="w-4 h-4 text-[var(--b-info)]" />
                        <span className="font-semibold">{cur.name}</span>
                        <span className="text-[var(--b-muted)]">· {idx + 1}/{steps.length}</span>
                        {cur.temp != null && <span className="text-[var(--b-accent)] beta-mono">· {num(cur.temp)}°C</span>}
                    </li>
                )}
                {nxt && (
                    <li className="flex items-center gap-2.5">
                        <SkipForward className="w-4 h-4 text-[var(--b-accent)]" />
                        <span className="text-[var(--b-muted)]">next:</span>
                        <span className="font-semibold">
                            {nxt.name}{nxt.temp != null && <> @ <span className="beta-mono">{num(nxt.temp, 0)}°C</span></>}
                        </span>
                        <span className="text-[var(--b-muted)]">· in {duration(sched?.days_to_next)}</span>
                    </li>
                )}
                <li className="flex items-center gap-2.5 flex-wrap">
                    <Thermometer className="w-4 h-4 text-[var(--b-muted)]" />
                    <span className="beta-mono font-semibold">{num(s.temp)}°</span>
                    <span className="text-[var(--b-muted)]">beer</span>
                    {s.target_temp != null && (
                        <>
                            <span className="text-[var(--b-faint)]">·</span>
                            <span className="beta-mono">{num(s.target_temp)}°</span>
                            <span className="text-[var(--b-muted)]">target</span>
                        </>
                    )}
                    {delta != null && (
                        <span className={cn('ml-auto beta-mono font-semibold', deltaColor)}>
                            Δ {delta > 0 ? '+' : ''}{num(delta)}°
                        </span>
                    )}
                </li>
            </ul>

            <div className="flex flex-wrap gap-2 mt-5">
                {s.day != null && (
                    <Chip icon={CalendarDays}>Day {s.day}</Chip>
                )}
                {countdown && <Chip icon={Timer} accent>{countdown}</Chip>}
                {!s.brew_active && <Chip>Idle: turn on Brew Active in Settings</Chip>}
            </div>
        </BetaCard>
    );
}

function Chip({ icon: Icon, accent, children }: { icon?: typeof Timer; accent?: boolean; children: React.ReactNode }) {
    return (
        <span
            className={cn(
                'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium',
                accent ? 'bg-[var(--b-tile)] text-[var(--b-accent)]' : 'bg-[var(--b-card-hi)] text-[var(--b-muted)]',
            )}
        >
            {Icon && <Icon className="w-3.5 h-3.5" />}
            {children}
        </span>
    );
}
