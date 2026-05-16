'use client';

import { cn } from '@/lib/utils';
import { useSocket } from '@/lib/socket';
import { useStatus } from '@/lib/hooks';

export function ConnectionStatus() {
    const { isConnected } = useSocket();
    const { data: status, error } = useStatus();

    let statusFormatted = "Offline";
    let statusColor = "bg-rose-500";

    if (isConnected) {
        statusFormatted = "Connected";
        statusColor = "bg-emerald-500";
    } else if (status && !error) {
        statusFormatted = "Via API";
        statusColor = "bg-amber-500";
    }

    return (
        <div className="flex items-center justify-center lg:justify-start gap-3 text-xs text-muted-foreground">
            <div className={cn("w-2 h-2 rounded-full animate-pulse", statusColor)} />
            <span className="hidden lg:block">{statusFormatted}</span>
        </div>
    );
}

export function MobileConnectionStatus() {
    const { isConnected } = useSocket();
    const { data: status, error } = useStatus();

    let statusColor = "bg-rose-500";
    if (isConnected) statusColor = "bg-emerald-500";
    else if (status && !error) statusColor = "bg-amber-500";

    return (
        <div className="flex items-center gap-1.5 mt-1">
            <div className={cn("w-1.5 h-1.5 rounded-full animate-pulse", statusColor)} />
            <span className="text-[10px] text-muted-foreground uppercase tracking-tight font-semibold">Live</span>
        </div>
    );
}
