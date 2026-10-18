'use client';

import { useState } from 'react';
import { Activity, ChevronDown, ExternalLink } from 'lucide-react';
import { cn } from '@/lib/utils';
import { PredictionCard } from '@/components/PredictionCard';
import { AdviceWidget } from '@/components/AdviceWidget';
import { AnomalyWidget } from '@/components/AnomalyWidget';
import { PeerComparisonWidget } from '@/components/PeerComparison';
import { SystemHealth } from '@/components/SystemHealth';
import { GrafanaChart } from '@/components/GrafanaChart';

const RANGES = ['now-24h', 'now-3d', 'now-7d', 'now-30d'];

/**
 * Cards carried over from the original dashboard, plus the Grafana
 * fermentation chart folded away until it's wanted.
 */
export function MoreInsights() {
    const [chartOpen, setChartOpen] = useState(false);
    const [timeRange, setTimeRange] = useState('now-7d');

    const openTiltPi = () => {
        window.open(`http://${window.location.hostname}:1880/ui/`, '_blank');
    };

    return (
        <div className="space-y-5 pt-2">
            <h2 className="text-sm font-bold tracking-widest uppercase text-[var(--b-muted)]">Insights</h2>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                <PredictionCard className="h-full rounded-3xl" />
                <AdviceWidget className="h-full rounded-3xl" />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                <AnomalyWidget className="h-full rounded-3xl" />
                <PeerComparisonWidget />
                <SystemHealth />
            </div>

            <section className="beta-card">
                <button
                    type="button"
                    onClick={() => setChartOpen((o) => !o)}
                    aria-expanded={chartOpen}
                    className="w-full flex items-center gap-3 p-5 md:p-6 text-left"
                >
                    <div className="w-11 h-11 shrink-0 rounded-xl flex items-center justify-center bg-[var(--b-tile)] text-[var(--b-accent)]">
                        <Activity className="w-5 h-5" />
                    </div>
                    <div className="min-w-0 flex-1">
                        <h2 className="text-[17px] font-semibold leading-tight">Fermentation analysis</h2>
                        <p className="text-sm text-[var(--b-muted)]">Detailed Grafana chart</p>
                    </div>
                    <ChevronDown className={cn('w-5 h-5 text-[var(--b-muted)] transition-transform', chartOpen && 'rotate-180')} />
                </button>

                {chartOpen && (
                    <div className="px-5 md:px-6 pb-5 md:pb-6 space-y-4">
                        <div className="flex flex-wrap items-center justify-between gap-3">
                            <button
                                type="button"
                                onClick={openTiltPi}
                                className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-sm bg-[var(--b-tile)] border border-[var(--b-border)] text-[var(--b-muted)] hover:text-[var(--b-text)]"
                            >
                                <ExternalLink className="w-4 h-4" /> TiltPi panel
                            </button>
                            <div className="flex rounded-full p-1 bg-[var(--b-tile)] border border-[var(--b-border)]">
                                {RANGES.map((range) => (
                                    <button
                                        key={range}
                                        type="button"
                                        onClick={() => setTimeRange(range)}
                                        className={cn(
                                            'px-3 py-1 text-xs font-bold uppercase rounded-full',
                                            timeRange === range ? 'bg-[var(--b-accent)] text-black' : 'text-[var(--b-muted)] hover:text-[var(--b-text)]',
                                        )}
                                    >
                                        {range.replace('now-', '')}
                                    </button>
                                ))}
                            </div>
                        </div>
                        <div className="w-full h-[450px] md:h-[650px] rounded-2xl overflow-hidden">
                            <GrafanaChart timeRange={timeRange} />
                        </div>
                    </div>
                )}
            </section>
        </div>
    );
}
