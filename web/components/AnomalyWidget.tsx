'use client';

import { useState, useEffect } from 'react';
import { cn } from '@/lib/utils';
import { AlertTriangle, CheckCircle, Activity, X } from 'lucide-react';
import { useSocket } from '@/lib/socket';
import type { AnomalyAlert, AnomalyStatus } from '@/types/api';
import { fetcher } from '@/lib/hooks';

interface AnomalyWidgetProps {
    className?: string;
}

const severityConfig = {
    ok: {
        color: 'text-emerald-500',
        bg: 'bg-emerald-500/10',
        border: 'border-emerald-500/20',
        icon: CheckCircle,
        label: 'Normal'
    },
    elevated: {
        color: 'text-amber-400',
        bg: 'bg-amber-500/10',
        border: 'border-amber-500/20',
        icon: Activity,
        label: 'Elevated'
    },
    warning: {
        color: 'text-orange-500',
        bg: 'bg-orange-500/10',
        border: 'border-orange-500/20',
        icon: AlertTriangle,
        label: 'Warning'
    },
    critical: {
        color: 'text-rose-500',
        bg: 'bg-rose-500/10',
        border: 'border-rose-500/20',
        icon: AlertTriangle,
        label: 'Critical'
    },
};

export function AnomalyWidget({ className }: AnomalyWidgetProps) {
    const { socket } = useSocket();
    const [anomalyData, setAnomalyData] = useState<AnomalyStatus | null>(null);
    const [recentAlerts, setRecentAlerts] = useState<AnomalyAlert[]>([]);
    const [isExpanded, setIsExpanded] = useState(false);
    const [isLoading, setIsLoading] = useState(true);

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
    const config = severityConfig[status];
    const Icon = config.icon;
    const score = anomalyData?.anomaly_score ?? 0;

    if (isLoading) {
        return (
            <div className={cn(
                "rounded-2xl bg-card p-4 border border-border/50 animate-pulse",
                className
            )}>
                <div className="h-6 bg-secondary rounded w-24 mb-2" />
                <div className="h-8 bg-secondary rounded w-16" />
            </div>
        );
    }

    return (
        <>
            {/* Widget Card */}
            <div
                onClick={() => setIsExpanded(true)}
                className={cn(
                    "group relative overflow-hidden rounded-2xl p-6 shadow-md border transition-all duration-300 cursor-pointer",
                    "hover:shadow-lg hover:-translate-y-1",
                    config.bg,
                    config.border,
                    className
                )}
            >
                <div className="flex items-center justify-between mb-4">
                    <h3 className="text-sm font-medium text-muted-foreground">Anomaly Status</h3>
                    <div className={cn("p-2 rounded-full bg-secondary/80", config.color)}>
                        <Icon className="w-5 h-5" />
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
                >
                    <div
                        className="bg-card rounded-3xl p-6 max-w-lg w-full mx-4 shadow-2xl border border-border/50"
                        onClick={e => e.stopPropagation()}
                    >
                        <div className="flex items-center justify-between mb-6">
                            <h2 className="text-xl font-bold">Anomaly Detection</h2>
                            <button
                                onClick={() => setIsExpanded(false)}
                                className="p-2 rounded-full hover:bg-secondary transition-colors"
                            >
                                <X className="w-5 h-5" />
                            </button>
                        </div>

                        {/* Score Display */}
                        <div className={cn("rounded-xl p-4 mb-4", config.bg)}>
                            <div className="flex items-center gap-3">
                                <Icon className={cn("w-8 h-8", config.color)} />
                                <div>
                                    <div className={cn("text-2xl font-bold", config.color)}>
                                        {config.label}
                                    </div>
                                    <div className="text-sm text-muted-foreground">
                                        Anomaly Score: {(score * 100).toFixed(0)}%
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Check Details */}
                        <div className="space-y-3 mb-4">
                            <h3 className="text-sm font-medium text-muted-foreground">Detection Checks</h3>
                            {anomalyData?.checks && Object.entries(anomalyData.checks).map(([key, check]) => (
                                <div
                                    key={key}
                                    className="flex items-center justify-between p-3 rounded-lg bg-secondary/30"
                                >
                                    <span className="capitalize">{key.replace('_', ' ')}</span>
                                    <span className={cn(
                                        "text-sm font-medium px-2 py-1 rounded-full",
                                        check?.status === 'normal' || check?.status === 'ok'
                                            ? 'bg-emerald-500/10 text-emerald-500'
                                            : check?.alert_sent
                                                ? 'bg-rose-500/10 text-rose-500'
                                                : 'bg-amber-500/10 text-amber-500'
                                    )}>
                                        {check?.status || 'unknown'}
                                    </span>
                                </div>
                            ))}
                        </div>

                        {/* Z-Score Details */}
                        {anomalyData?.checks?.statistical && (
                            <div className="p-4 rounded-xl bg-secondary/20 mb-4">
                                <h3 className="text-sm font-medium text-muted-foreground mb-2">Statistical Analysis</h3>
                                <div className="grid grid-cols-2 gap-4 text-sm">
                                    <div>
                                        <div className="text-muted-foreground">Temp Z-Score</div>
                                        <div className="text-lg font-semibold">
                                            {anomalyData.checks.statistical.temp_zscore?.toFixed(2) ?? '--'}
                                        </div>
                                    </div>
                                    <div>
                                        <div className="text-muted-foreground">SG Rate Z-Score</div>
                                        <div className="text-lg font-semibold">
                                            {anomalyData.checks.statistical.sg_rate_zscore?.toFixed(2) ?? '--'}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* Recent Alerts */}
                        {recentAlerts.length > 0 && (
                            <div>
                                <h3 className="text-sm font-medium text-muted-foreground mb-2">Recent Alerts</h3>
                                <div className="space-y-2 max-h-40 overflow-y-auto">
                                    {recentAlerts.map((alert, i) => (
                                        <div
                                            key={i}
                                            className={cn(
                                                "p-3 rounded-lg text-sm",
                                                alert.severity === 'critical' ? 'bg-rose-500/10 text-rose-400' :
                                                    alert.severity === 'error' ? 'bg-orange-500/10 text-orange-400' :
                                                        alert.severity === 'warning' ? 'bg-amber-500/10 text-amber-400' :
                                                            'bg-blue-500/10 text-blue-400'
                                            )}
                                        >
                                            <div className="font-medium">{alert.message}</div>
                                            <div className="text-xs opacity-70">
                                                {new Date(alert.timestamp).toLocaleTimeString()}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            )}
        </>
    );
}

export default AnomalyWidget;
