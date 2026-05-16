'use client';

import { cn } from '@/lib/utils';
import type { AnomalyAlert } from '@/types/api';

interface AlertsListProps {
    alerts: AnomalyAlert[];
}

export function AlertsList({ alerts }: AlertsListProps) {
    if (alerts.length === 0) return null;

    return (
        <div>
            <h3 className="text-sm font-medium text-muted-foreground mb-2">Recent Alerts</h3>
            <div className="space-y-2 max-h-40 overflow-y-auto">
                {alerts.map((alert, i) => (
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
    );
}
