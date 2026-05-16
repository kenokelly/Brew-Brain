'use client';

import { useState, useEffect } from 'react';
import { cn } from '@/lib/utils';
import { X, Brain, Loader2 } from 'lucide-react';
import { useSocket } from '@/lib/socket';
import type { AnomalyAlert, AnomalyStatus } from '@/types/api';
import { fetcher } from '@/lib/hooks';
import { apiFetch } from '@/lib/api';
import { SeverityIcon, severityConfig } from './anomaly/SeverityIcon';
import { CheckItem } from './anomaly/CheckItem';
import { AIAnalysis } from './anomaly/AIAnalysis';
import { AlertsList } from './anomaly/AlertsList';
import { StatisticalGrid } from './anomaly/StatisticalGrid';

import { AnomalySkeleton } from '@/components/ui/skeleton';

interface AnomalyWidgetProps {
    className?: string;
}

interface AIAnalysis {
    status: 'success' | 'fallback' | 'error';
    analysis: string;
    source?: string;
}

export function AnomalyWidget({ className }: AnomalyWidgetProps) {
    const { socket } = useSocket();
    const [anomalyData, setAnomalyData] = useState<AnomalyStatus | null>(null);
    const [recentAlerts, setRecentAlerts] = useState<AnomalyAlert[]>([]);
    const [isExpanded, setIsExpanded] = useState(false);
    const [isLoading, setIsLoading] = useState(true);
    const [aiAnalysis, setAiAnalysis] = useState<AIAnalysis | null>(null);
    const [isAnalyzing, setIsAnalyzing] = useState(false);

    // Fetch initial anomaly status
    useEffect(() => {
        const fetchAnomalyStatus = async () => {
            try {
                const json = await fetcher<{ status: string; data: AnomalyStatus; error?: string }>('/api/anomaly');
                if (json.status === 'success' && json.data) {
                    setAnomalyData(json.data);
                }
            } catch (error) {
                console.error('Failed to fetch anomaly status:', error);
            } finally {
                setIsLoading(false);
            }
        };

        fetchAnomalyStatus();
        // Refresh every 5 minutes
        const interval = setInterval(fetchAnomalyStatus, 5 * 60 * 1000);
        return () => clearInterval(interval);
    }, []);

    const handleTroubleshoot = async () => {
        if (!anomalyData || isAnalyzing) return;
        
        setIsAnalyzing(true);
        setAiAnalysis(null);
        
        try {
            const res = await apiFetch<any>('/api/ai/troubleshoot', {
                method: 'POST',
                body: { 
                    anomaly: {
                        type: config.label,
                        severity: status,
                        message: recentAlerts[0]?.message || 'General anomaly detected in fermentation parameters.',
                        batch_name: 'Current Batch',
                        score: score
                    } 
                }
            });
            
            // The backend wraps results in a "data" object
            const data = res.data || res;
            setAiAnalysis(data);
        } catch (_error) {
            setAiAnalysis({
                status: 'error',
                analysis: 'Failed to connect to Brewmaster AI. Please check if the service is online.'
            });
        } finally {
            setIsAnalyzing(false);
        }
    };

    // Escape key support for expanded view
    useEffect(() => {
        const handleEsc = (e: KeyboardEvent) => {
            if (e.key === 'Escape') setIsExpanded(false);
        };
        if (isExpanded) {
            window.addEventListener('keydown', handleEsc);
        }
        return () => window.removeEventListener('keydown', handleEsc);
    }, [isExpanded]);

    // Listen for real-time anomaly alerts via WebSocket
    useEffect(() => {
        if (!socket) return;

        const handleAnomalyAlert = (alert: AnomalyAlert) => {
            setRecentAlerts(prev => {
                const updated = [alert, ...prev].slice(0, 5); // Keep last 5
                return updated;
            });

            // Update anomaly status based on alert severity
            setAnomalyData(prev => {
                if (!prev) return prev;
                const newStatus = alert.severity === 'critical' ? 'critical'
                    : alert.severity === 'error' ? 'warning'
                        : prev.anomaly_status;
                return {
                    ...prev,
                    anomaly_status: newStatus as AnomalyStatus['anomaly_status'],
                    alerts_sent: (prev.alerts_sent || 0) + 1
                };
            });
        };

        socket.on('anomaly_alert', handleAnomalyAlert);
        return () => {
            socket.off('anomaly_alert', handleAnomalyAlert);
        };
    }, [socket]);

    const status = anomalyData?.anomaly_status ?? 'ok';
    const config = severityConfig[status] || severityConfig.ok;
    const score = anomalyData?.anomaly_score ?? 0;

    if (isLoading) {
        return <AnomalySkeleton />;
    }

    return (
        <>
            {/* Widget Card */}
            <div
                onClick={() => setIsExpanded(true)}
                onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        setIsExpanded(true);
                    }
                }}
                role="button"
                tabIndex={0}
                aria-label={`Anomaly Status: ${config.label}. Click for details.`}
                className={cn(
                    "group relative overflow-hidden rounded-2xl p-6 shadow-md border transition-all duration-300 cursor-pointer",
                    "hover:shadow-lg hover:-translate-y-1 focus-visible:ring-2 focus-visible:ring-primary outline-none",
                    config.bg,
                    config.border,
                    className
                )}
            >
                <div className="flex items-center justify-between mb-4">
                    <h3 className="text-sm font-medium text-muted-foreground">Anomaly Status</h3>
                    <div className={cn("p-2 rounded-full bg-secondary/80", config.color)}>
                        <SeverityIcon status={status} className="w-5 h-5" />
                    </div>
                </div>

                <div className="flex items-baseline gap-2">
                    <span className={cn("text-3xl font-bold tracking-tight", config.color)}>
                        {config.label}
                    </span>
                    {score > 0 && (
                        <span className="text-sm text-muted-foreground">
                            ({(score * 100).toFixed(0)}%)
                        </span>
                    )}
                </div>

                {anomalyData?.alerts_sent ? (
                    <div className="text-xs text-muted-foreground mt-2">
                        {anomalyData.alerts_sent} alert{anomalyData.alerts_sent > 1 ? 's' : ''} sent
                    </div>
                ) : null}

                {/* Hover indicator */}
                <div className="absolute bottom-0 left-0 h-1 w-full bg-gradient-to-r from-primary/0 via-primary/20 to-primary/0 opacity-0 group-hover:opacity-100 transition-opacity" />
            </div>

            {/* Expanded Modal */}
            {isExpanded && (
                <div
                    className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
                    onClick={() => setIsExpanded(false)}
                    role="presentation"
                >
                    <div
                        className="bg-card rounded-3xl p-6 max-w-lg w-full mx-4 shadow-2xl border border-border/50"
                        onClick={e => e.stopPropagation()}
                        role="dialog"
                        aria-modal="true"
                        aria-labelledby="anomaly-title"
                    >
                        <div className="flex items-center justify-between mb-6">
                            <h2 id="anomaly-title" className="text-xl font-bold">Anomaly Detection</h2>
                            <button
                                onClick={() => setIsExpanded(false)}
                                className="p-2 rounded-full hover:bg-secondary focus-visible:ring-2 focus-visible:ring-primary outline-none transition-colors"
                                aria-label="Close anomaly details"
                            >
                                <X className="w-5 h-5" />
                            </button>
                        </div>

                        {/* Score Display */}
                        <div className={cn("rounded-xl p-4 mb-6", config.bg)}>
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    <SeverityIcon status={status} className={cn("w-8 h-8", config.color)} />
                                    <div>
                                        <div className={cn("text-2xl font-bold", config.color)}>
                                            {config.label}
                                        </div>
                                        <div className="text-sm text-muted-foreground">
                                            Anomaly Score: {(score * 100).toFixed(0)}%
                                        </div>
                                    </div>
                                </div>
                                <button
                                    onClick={handleTroubleshoot}
                                    disabled={isAnalyzing}
                                    className="flex items-center gap-2 px-4 py-2 rounded-xl bg-purple-600 text-white hover:bg-purple-500 transition-colors disabled:opacity-50 text-sm font-medium shadow-sm"
                                >
                                    {isAnalyzing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Brain className="w-4 h-4" />}
                                    Troubleshoot
                                </button>
                            </div>
                        </div>

                        {/* AI Analysis Result */}
                        {aiAnalysis && (
                            <AIAnalysis analysis={aiAnalysis.analysis} source={aiAnalysis.source} />
                        )}

                        {/* Check Details */}
                        <div className="space-y-3 mb-4">
                            <h3 className="text-sm font-medium text-muted-foreground">Detection Checks</h3>
                            {anomalyData?.checks && Object.entries(anomalyData.checks).map(([key, check]) => (
                                <CheckItem 
                                    key={key} 
                                    label={key} 
                                    status={check?.status || 'unknown'} 
                                    alertSent={check?.alert_sent} 
                                />
                            ))}
                        </div>

                        {/* Z-Score Details */}
                        <StatisticalGrid 
                            tempZScore={anomalyData?.checks?.statistical?.temp_zscore}
                            sgRateZScore={anomalyData?.checks?.statistical?.sg_rate_zscore}
                        />

                        {/* Recent Alerts */}
                        <AlertsList alerts={recentAlerts} />
                    </div>
                </div>
            )}
        </>
    );
}


export default AnomalyWidget;
