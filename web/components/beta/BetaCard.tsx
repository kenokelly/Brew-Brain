'use client';

import type { LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';

/** Shared shell for the beta dashboard: icon tile, title/subtitle, live dot. */
export function BetaCard({
    icon: Icon,
    title,
    subtitle,
    live,
    badge,
    className,
    children,
}: {
    icon: LucideIcon;
    title: string;
    subtitle?: string;
    /** true = green dot, false = red dot, undefined = no dot */
    live?: boolean;
    badge?: React.ReactNode;
    className?: string;
    children: React.ReactNode;
}) {
    return (
        <section className={cn('beta-card p-5 md:p-6', className)}>
            <header className="flex items-start gap-3 mb-4">
                <div className="w-11 h-11 shrink-0 rounded-xl flex items-center justify-center bg-[var(--b-tile)] text-[var(--b-accent)]">
                    <Icon className="w-5 h-5" />
                </div>
                <div className="min-w-0 flex-1">
                    <h2 className="text-[17px] font-semibold leading-tight">{title}</h2>
                    {subtitle && <p className="text-sm text-[var(--b-muted)] truncate">{subtitle}</p>}
                </div>
                {badge}
                {live !== undefined && (
                    <span
                        aria-label={live ? 'Live' : 'Stale'}
                        className={cn(
                            'w-2.5 h-2.5 rounded-full mt-1.5 shrink-0',
                            live ? 'bg-[var(--b-good)] shadow-[0_0_8px_var(--b-good)]' : 'bg-[var(--b-bad)]',
                        )}
                    />
                )}
            </header>
            {children}
        </section>
    );
}

export function CardError({ message }: { message: string }) {
    return <p className="text-sm text-[var(--b-muted)] py-6 text-center">{message}</p>;
}
