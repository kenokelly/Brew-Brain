'use client';

import { cn } from '@/lib/utils';

interface CheckItemProps {
    label: string;
    status: string;
    alertSent?: boolean;
}

export function CheckItem({ label, status, alertSent }: CheckItemProps) {
    return (
        <div className="flex items-center justify-between p-3 rounded-lg bg-secondary/30">
            <span className="capitalize">{label.replace('_', ' ')}</span>
            <span className={cn(
                "text-sm font-medium px-2 py-1 rounded-full",
                status === 'normal' || status === 'ok'
                    ? 'bg-emerald-500/10 text-emerald-500'
                    : alertSent
                        ? 'bg-rose-500/10 text-rose-500'
                        : 'bg-amber-500/10 text-amber-500'
            )}>
                {status || 'unknown'}
            </span>
        </div>
    );
}
