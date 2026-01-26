'use client';

import { useState, useEffect } from 'react';
import { cn } from '@/lib/utils';
import { CheckCircle2, AlertTriangle, XCircle, RefreshCw, ClipboardCheck } from 'lucide-react';
import type { BrewDayCheckResponse, BrewDayCheckItem } from '@/types/api';

interface DataChecklistProps {
    className?: string;
    onReady?: (isReady: boolean) => void;
}

export function DataChecklist({ className, onReady }: DataChecklistProps) {
    const [data, setData] = useState<BrewDayCheckResponse | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const fetchData = async () => {
        setIsLoading(true);
        try {
            const res = await fetch('/api/brew_day_check');
            const json = await res.json();
            if (json.status === 'success' && json.data) {
                setData(json.data);
                setError(null);
                const isReady = json.data.score === 100;
                if (onReady) onReady(isReady);
            } else {
                setError(json.error || 'Failed to verify data');
            }
        } catch (err) {
            console.error('Failed to fetch checklist:', err);
            setError('Connection error');
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, []);

    if (isLoading && !data) {
        return (
            <div className={cn("flex flex-col gap-4 animate-pulse", className)}>
                {[1, 2, 3, 4].map(i => (
                    <div key={i} className="h-14 bg-zinc-900/50 rounded-xl border border-zinc-800" />
                ))}
            </div>
        );
    }

    return (
        <div className={cn("space-y-4", className)}>
            <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                    <ClipboardCheck className="w-5 h-5 text-primary" />
                    <h3 className="font-semibold text-zinc-100 uppercase tracking-wider text-sm">Checks & Balances</h3>
                </div>
                <div className="flex items-center gap-4">
                    <div className="text-right">
                        <p className="text-[10px] text-zinc-500 uppercase font-bold">Readiness</p>
                        <p className={cn("text-xl font-black font-mono leading-none",
                            data?.score === 100 ? "text-emerald-400" : data?.score && data.score > 70 ? "text-amber-400" : "text-rose-400"
                        )}>
                            {data?.score ?? 0}%
                        </p>
                    </div>
                    <button
                        onClick={fetchData}
                        disabled={isLoading}
                        className="p-2 rounded-lg bg-zinc-800 hover:bg-zinc-700 transition-colors disabled:opacity-50"
                    >
                        <RefreshCw className={cn("w-4 h-4 text-zinc-400", isLoading && "animate-spin")} />
                    </button>
                </div>
            </div>

            {error && (
                <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-center gap-2">
                    <XCircle className="w-4 h-4" />
                    {error}
                </div>
            )}

            <div className="space-y-2">
                {data?.checks.map((check, i) => (
                    <CheckItem key={i} check={check} />
                ))}
            </div>

            {data?.score === 100 && (
                <div className="p-4 rounded-2xl bg-emerald-500/5 border border-emerald-500/10 flex gap-3 items-center">
                    <div className="p-2 rounded-full bg-emerald-500/20 text-emerald-400">
                        <CheckCircle2 className="w-5 h-5" />
                    </div>
                    <div>
                        <p className="text-sm font-semibold text-emerald-400">System Ready</p>
                        <p className="text-[10px] text-emerald-500/70">All critical data points verified for AI tracking.</p>
                    </div>
                </div>
            )}
        </div>
    );
}

function CheckItem({ check }: { check: BrewDayCheckItem }) {
    const icons = {
        ready: <CheckCircle2 className="w-5 h-5 text-emerald-400" />,
        warning: <AlertTriangle className="w-5 h-5 text-amber-500" />,
        error: <XCircle className="w-5 h-5 text-rose-500" />
    };

    const statusBg = {
        ready: "bg-emerald-500/5 border-emerald-500/10",
        warning: "bg-amber-500/5 border-amber-500/10",
        error: "bg-rose-500/5 border-rose-500/10"
    };

    return (
        <div className={cn("p-4 rounded-xl border flex items-center gap-4 transition-all duration-300", statusBg[check.status])}>
            <div className="shrink-0">{icons[check.status]}</div>
            <div className="flex-1 min-w-0">
                <p className="text-xs font-bold text-zinc-100 uppercase tracking-tight">{check.name}</p>
                <p className="text-[11px] text-zinc-500 truncate">{check.message}</p>
            </div>
        </div>
    );
}
