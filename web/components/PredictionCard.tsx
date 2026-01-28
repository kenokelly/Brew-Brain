'use client';

import { useState, useEffect } from 'react';
import { cn } from '@/lib/utils';
import { Brain, Clock, ChevronRight, TrendingDown, Thermometer, Database, Activity } from 'lucide-react';
import type { MLPrediction } from '@/types/api';
import { fetcher } from '@/lib/hooks';

interface PredictionCardProps {
    className?: string;
}

export function PredictionCard({ className }: PredictionCardProps) {
    const [prediction, setPrediction] = useState<MLPrediction | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const fetchPrediction = async () => {
        try {
            const json = await fetcher<{ status: string; data: MLPrediction; error?: string }>('/api/ml/predict');

            if (json.status === 'success' && json.data) {
                setPrediction(json.data);
                setError(null);
            } else {
                setError(json.error || 'Failed to fetch predictions');
            }
        } catch (err: any) {
            console.error('Failed to fetch ML predictions:', err);
            setError(err.message || 'Connection error');
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        fetchPrediction();
        // Refresh every 10 minutes
        const interval = setInterval(fetchPrediction, 10 * 60 * 1000);
        return () => clearInterval(interval);
    }, []);

    if (isLoading) {
        return (
            <div className={cn("bg-zinc-900/50 border border-zinc-800 rounded-xl p-6 h-full flex flex-col justify-center items-center gap-4 animate-pulse", className)}>
                <Brain className="w-8 h-8 text-zinc-700" />
                <div className="h-4 w-32 bg-zinc-800 rounded" />
            </div>
        );
    }

    if (error || !prediction) {
        return (
            <div className={cn("bg-zinc-900/50 border border-zinc-800 rounded-xl p-6 h-full flex flex-col justify-center items-center gap-2 text-zinc-500", className)}>
                <Brain className="w-6 h-6 mb-2 opacity-50" />
                <p className="text-sm text-center">{error || 'No active prediction'}</p>
                <button
                    onClick={() => { setIsLoading(true); fetchPrediction(); }}
                    className="text-xs text-blue-400 hover:text-blue-300 transition-colors mt-2"
                >
                    Retry
                </button>
            </div>
        );
    }

    const { prediction_fg, prediction_time, features, batch_metadata } = prediction;
    const isML = prediction_fg.method === 'ml_model';

    return (
        <div className={cn("bg-zinc-900/50 border border-zinc-800 rounded-xl overflow-hidden flex flex-col h-full", className)}>
            <div className="p-4 border-b border-zinc-800 flex items-center justify-between bg-zinc-900/30">
                <div className="flex items-center gap-2">
                    <div className={cn(
                        "p-1.5 rounded-lg",
                        isML ? "bg-purple-500/10 text-purple-400" : "bg-zinc-800 text-zinc-400"
                    )}>
                        <Brain className="w-4 h-4" />
                    </div>
                    <div>
                        <h3 className="text-sm font-medium text-zinc-200">AI Predictions</h3>
                        <p className="text-[10px] text-zinc-500 uppercase tracking-wider font-semibold">
                            {isML ? 'Machine Learning Model' : 'Formula Estimator'}
                        </p>
                    </div>
                </div>
                {isML && (
                    <div className={cn(
                        "px-2 py-0.5 rounded-full text-[10px] font-bold border",
                        prediction_fg.confidence === 'high'
                            ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                            : "bg-amber-500/10 text-amber-400 border-amber-500/20"
                    )}>
                        {prediction_fg.confidence.toUpperCase()} CONFIDENCE
                    </div>
                )}
            </div>

            <div className="p-5 flex-1 flex flex-col gap-6">
                {/* Main Predictions */}
                <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-1">
                        <span className="text-xs text-zinc-500 flex items-center gap-1">
                            <TrendingDown className="w-3 h-3" /> Predicted FG
                        </span>
                        <div className="text-2xl font-bold text-zinc-100 tracking-tight">
                            {prediction_fg.predicted_fg.toFixed(3)}
                        </div>
                        <p className="text-[10px] text-zinc-500">
                            Est. ABV: {prediction_fg.predicted_abv}%
                        </p>
                    </div>
                    <div className="space-y-1">
                        <span className="text-xs text-zinc-500 flex items-center gap-1">
                            <Clock className="w-3 h-3" /> Time Remaining
                        </span>
                        <div className="text-2xl font-bold text-zinc-100 tracking-tight">
                            {prediction_time.days_remaining} <span className="text-sm font-normal text-zinc-400">days</span>
                        </div>
                        {prediction_time.total_estimated_days && (
                            <p className="text-[10px] text-zinc-500">
                                Total cycle: {prediction_time.total_estimated_days} days
                            </p>
                        )}
                    </div>
                </div>

                {/* Live Features / Data Quality */}
                <div className="space-y-3 pt-2 border-t border-zinc-800/50">
                    <h4 className="text-[10px] font-bold text-zinc-600 uppercase tracking-widest flex items-center gap-2">
                        <Activity className="w-3 h-3" /> Feature Analysis
                    </h4>
                    <div className="grid grid-cols-3 gap-2">
                        <div className="bg-zinc-800/30 rounded-lg p-2 border border-zinc-800/30">
                            <div className="text-[10px] text-zinc-500 flex items-center gap-1 mb-1">
                                <TrendingDown className="w-2.5 h-2.5" /> Velocity
                            </div>
                            <div className="text-xs font-mono text-zinc-300">
                                {features.velocity.toFixed(2)} pts/d
                            </div>
                        </div>
                        <div className="bg-zinc-800/30 rounded-lg p-2 border border-zinc-800/30">
                            <div className="text-[10px] text-zinc-500 flex items-center gap-1 mb-1">
                                <Thermometer className="w-2.5 h-2.5" /> Variant
                            </div>
                            <div className="text-xs font-mono text-zinc-300">
                                {features.temp_variance.toFixed(2)}°
                            </div>
                        </div>
                        <div className="bg-zinc-800/30 rounded-lg p-2 border border-zinc-800/30">
                            <div className="text-[10px] text-zinc-500 flex items-center gap-1 mb-1">
                                <Database className="w-2.5 h-2.5" /> Data
                            </div>
                            <div className="text-xs font-mono text-zinc-300">
                                {batch_metadata.data_points} pts
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <div className="px-4 py-2 bg-zinc-900/50 border-t border-zinc-800 flex items-center justify-between">
                <span className="text-[10px] text-zinc-600 italic">
                    Updated every 10 min
                </span>
                <button
                    onClick={() => { setIsLoading(true); fetchPrediction(); }}
                    className="group flex items-center gap-1 text-[10px] text-blue-400/80 hover:text-blue-400 transition-colors"
                >
                    Refresh <ChevronRight className="w-2.5 h-2.5 group-hover:translate-x-0.5 transition-transform" />
                </button>
            </div>
        </div>
    );
}
