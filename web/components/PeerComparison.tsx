'use client';

import { useState, useEffect } from 'react';
import { cn } from '@/lib/utils';
import { Users, Info, BarChart2, TrendingUp, Droplets, FlaskConical } from 'lucide-react';
import type { PeerComparison } from '@/types/api';

interface PeerComparisonProps {
    className?: string;
}

export function PeerComparisonWidget({ className }: PeerComparisonProps) {
    const [data, setData] = useState<PeerComparison | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const fetchData = async () => {
        try {
            import { fetcher } from '@/lib/hooks';

            // ... imports

            export function PeerComparisonWidget({ className }: PeerComparisonProps) {
                // ...
                const fetchData = async () => {
                    try {
                        // Use safe fetcher which handles non-JSON responses
                        const json = await fetcher<{ status: string; data: PeerComparison; error?: string }>('/api/ml/peers');

                        if (json.status === 'success' && json.data) {
                            setData(json.data);
                            setError(null);
                        } else {
                            setError(json.error || 'No benchmark data');
                        }
                    } catch (err: any) {
                        console.error('Failed to fetch peer data:', err);
                        setError(err.message || 'Connection error');
                    } finally {
                        setIsLoading(false);
                    }
                };
            } catch (err) {
                console.error('Failed to fetch peer data:', err);
                setError('Connection error');
            } finally {
                setIsLoading(false);
            }
        };

        useEffect(() => {
            fetchData();
            // Refresh every 30 minutes
            const interval = setInterval(fetchData, 30 * 60 * 1000);
            return () => clearInterval(interval);
        }, []);

        if (isLoading) {
            return (
                <div className={cn("bg-zinc-900/50 border border-zinc-800 rounded-xl p-6 h-full flex flex-col justify-center items-center gap-4 animate-pulse", className)}>
                    <Users className="w-8 h-8 text-zinc-700" />
                    <div className="h-4 w-32 bg-zinc-800 rounded" />
                </div>
            );
        }

        if (error || !data) {
            return (
                <div className={cn("bg-zinc-900/50 border border-zinc-800 rounded-xl p-6 h-full flex flex-col justify-center items-center gap-2 text-zinc-500", className)}>
                    <Users className="w-6 h-6 mb-2 opacity-50" />
                    <p className="text-sm text-center">{error || 'Peer insights unavailable'}</p>
                    <button
                        onClick={() => { setIsLoading(true); fetchData(); }}
                        className="text-xs text-blue-400 hover:text-blue-300 transition-colors mt-2"
                    >
                        Retry
                    </button>
                </div>
            );
        }

        return (
            <div className={cn("bg-zinc-900/50 border border-zinc-800 rounded-xl overflow-hidden flex flex-col h-full", className)}>
                <div className="p-4 border-b border-zinc-800 flex items-center justify-between bg-zinc-900/30">
                    <div className="flex items-center gap-2">
                        <div className="p-1.5 rounded-lg bg-emerald-500/10 text-emerald-400">
                            <Users className="w-4 h-4" />
                        </div>
                        <div>
                            <h3 className="text-sm font-medium text-zinc-200">Style Benchmarks</h3>
                            <p className="text-[10px] text-zinc-500 uppercase tracking-wider font-semibold">
                                Based on {data.total_samples} external recipes
                            </p>
                        </div>
                    </div>
                    <div title={data.included_styles.join(', ')}>
                        <Info className="w-3.5 h-3.5 text-zinc-600 cursor-help" />
                    </div>
                </div>

                <div className="p-5 flex-1 flex flex-col gap-4">
                    <div className="flex items-center justify-between mb-1">
                        <span className="text-[10px] font-bold text-zinc-600 uppercase tracking-widest">{data.primary_style} Averages</span>
                        <BarChart2 className="w-3 h-3 text-zinc-700" />
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                        <MetricBox
                            icon={<TrendingUp className="w-2.5 h-2.5" />}
                            label="Avg OG"
                            value={data.avg_og.toFixed(3)}
                        />
                        <MetricBox
                            icon={<Droplets className="w-2.5 h-2.5" />}
                            label="Avg FG"
                            value={data.avg_fg.toFixed(3)}
                        />
                        <MetricBox
                            icon={<FlaskConical className="w-2.5 h-2.5" />}
                            label="Avg ABV"
                            value={`${data.avg_abv}%`}
                        />
                        <MetricBox
                            icon={<BarChart2 className="w-2.5 h-2.5" />}
                            label="Avg IBU"
                            value={Math.round(data.avg_ibu).toString()}
                        />
                    </div>

                    <div className="mt-2 flex flex-col gap-2">
                        <span className="text-[10px] font-bold text-zinc-600 uppercase tracking-widest">Recommendations</span>
                        <div className="flex flex-col gap-1.5">
                            {data.recommendations?.map((rec, i) => (
                                <div key={i} className="p-2 rounded-lg bg-emerald-500/5 border border-emerald-500/10 flex gap-2 items-start">
                                    <FlaskConical className="w-3 h-3 text-emerald-400 shrink-0 mt-0.5" />
                                    <p className="text-[10px] text-zinc-300 leading-tight">
                                        {rec}
                                    </p>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    function MetricBox({ icon, label, value }: { icon: React.ReactNode, label: string, value: string }) {
        return (
            <div className="bg-zinc-800/30 rounded-lg p-2.5 border border-zinc-800/30 flex flex-col gap-1">
                <div className="text-[10px] text-zinc-500 flex items-center gap-1.5 uppercase tracking-tighter">
                    {icon} {label}
                </div>
                <div className="text-sm font-mono font-bold text-zinc-200">
                    {value}
                </div>
            </div>
        );
    }
