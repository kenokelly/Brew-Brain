'use client';

import { useState, useEffect } from 'react';
import { cn } from '@/lib/utils';
import { HardDrive, Cpu, Thermometer, ShieldCheck, Activity, AlertCircle } from 'lucide-react';
import { fetcher } from '@/lib/hooks';

interface MaintenanceData {
    disk: {
        total_gb: number;
        used_gb: number;
        used_percent: number;
        free_gb: number;
        warning: boolean;
    };
    data_volume: {
        used_percent: number;
        warning: boolean;
    };
    pi_temp: number;
    sd_io?: {
        sectors_written: number;
        write_ms: number;
    };
}

export function SystemHealth() {
    const [data, setData] = useState<MaintenanceData | null>(null);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        const fetchMaintenance = async () => {
            try {
                const json = await fetcher<{ status: string; data: MaintenanceData }>('/api/health/maintenance');
                if (json.status === 'success') {
                    setData(json.data);
                }
            } catch (error) {
                console.error('Failed to fetch maintenance status:', error);
            } finally {
                setIsLoading(false);
            }
        };

        fetchMaintenance();
        const interval = setInterval(fetchMaintenance, 30000); // 30s refresh
        return () => clearInterval(interval);
    }, []);

    if (isLoading) {
        return (
            <div className="rounded-2xl bg-card/50 p-6 border border-border/50 animate-pulse h-full">
                <div className="h-4 bg-secondary rounded w-24 mb-4" />
                <div className="space-y-3">
                    <div className="h-8 bg-secondary rounded w-full" />
                    <div className="h-8 bg-secondary rounded w-full" />
                </div>
            </div>
        );
    }

    if (!data) return null;

    const isSystemCritical = data.disk.warning || data.pi_temp > 75;

    return (
        <div className={cn(
            "group relative overflow-hidden rounded-2xl p-6 shadow-md border transition-all duration-300",
            "bg-card/50 backdrop-blur-md",
            isSystemCritical ? "border-rose-500/30 bg-rose-500/5" : "border-border/50"
        )}>
            <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                    <ShieldCheck className={cn("w-4 h-4", isSystemCritical ? "text-rose-500" : "text-emerald-500")} />
                    Pi Health
                </h3>
                {isSystemCritical && (
                    <AlertCircle className="w-4 h-4 text-rose-500 animate-bounce" />
                )}
            </div>

            <div className="space-y-4">
                {/* Disk Usage */}
                <div>
                    <div className="flex justify-between text-xs mb-1">
                        <span className="flex items-center gap-1"><HardDrive className="w-3 h-3" /> SD Card</span>
                        <span className={cn(data.disk.warning ? "text-rose-500 font-bold" : "text-muted-foreground")}>
                            {data.disk.used_percent}%
                        </span>
                    </div>
                    <div className="h-1.5 w-full bg-secondary rounded-full overflow-hidden">
                        <div 
                            className={cn(
                                "h-full transition-all duration-1000",
                                data.disk.warning ? "bg-rose-500" : "bg-primary"
                            )}
                            style={{ width: `${data.disk.used_percent}%` }}
                        />
                    </div>
                    <div className="text-[10px] text-muted-foreground mt-1">
                        {data.disk.free_gb} GB remaining of {data.disk.total_gb} GB
                    </div>
                </div>

                {/* Pi Temp & IO */}
                <div className="grid grid-cols-2 gap-4">
                    <div className="bg-secondary/30 rounded-xl p-3">
                        <div className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1">SoC Temp</div>
                        <div className="flex items-baseline gap-1">
                            <span className={cn(
                                "text-lg font-bold",
                                data.pi_temp > 65 ? "text-orange-500" : "text-foreground"
                            )}>
                                {data.pi_temp}°
                            </span>
                            <span className="text-[10px] text-muted-foreground">C</span>
                        </div>
                    </div>
                    <div className="bg-secondary/30 rounded-xl p-3">
                        <div className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1">SD Writes</div>
                        <div className="flex items-baseline gap-1">
                            <span className="text-lg font-bold">
                                {data.sd_io ? Math.round(data.sd_io.sectors_written / 2048) : '--'}
                            </span>
                            <span className="text-[10px] text-muted-foreground">MB</span>
                        </div>
                    </div>
                </div>
            </div>

            {/* Hover decoration */}
            <div className="absolute -bottom-2 -right-2 opacity-5 group-hover:opacity-10 transition-opacity">
                <Cpu className="w-16 h-16" />
            </div>
        </div>
    );
}

export default SystemHealth;
