'use client';

import { CheckCircle, Activity, AlertTriangle, LucideIcon } from 'lucide-react';
import type { AnomalyStatus } from '@/types/api';

export const severityConfig: Record<string, {
    color: string;
    bg: string;
    border: string;
    icon: LucideIcon;
    label: string;
}> = {
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

interface SeverityIconProps {
    status: AnomalyStatus['anomaly_status'] | 'ok';
    className?: string;
}

export function SeverityIcon({ status, className }: SeverityIconProps) {
    const config = severityConfig[status] || severityConfig.ok;
    const Icon = config.icon;
    return <Icon className={className} />;
}
