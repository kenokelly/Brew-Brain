/**
 * Loading Skeleton Component
 * Animated placeholder for loading states
 */

import { cn } from '@/lib/utils';

interface SkeletonProps {
    className?: string;
}

export function Skeleton({ className }: SkeletonProps) {
    return (
        <div
            className={cn(
                'animate-pulse rounded-md bg-muted/50',
                className
            )}
        />
    );
}

/**
 * Card Skeleton - represents a loading card
 */
export function CardSkeleton() {
    return (
        <div className="rounded-2xl border border-border/50 bg-card p-6 space-y-4">
            <Skeleton className="h-6 w-1/3" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-2/3" />
            <div className="flex gap-2 pt-2">
                <Skeleton className="h-8 w-20" />
                <Skeleton className="h-8 w-20" />
            </div>
        </div>
    );
}

/**
 * Table Row Skeleton
 */
export function TableRowSkeleton({ cols = 4 }: { cols?: number }) {
    return (
        <tr className="border-b border-border/30">
            {Array.from({ length: cols }).map((_, i) => (
                <td key={i} className="py-3 px-4">
                    <Skeleton className="h-4 w-full" />
                </td>
            ))}
        </tr>
    );
}

/**
 * Stat Card Skeleton
 */
export function StatSkeleton() {
    return (
        <div className="rounded-xl border border-border/50 bg-card/50 p-4 space-y-2">
            <Skeleton className="h-4 w-1/2" />
            <Skeleton className="h-8 w-2/3" />
        </div>
    );
}

/**
 * Dashboard Grid Skeleton
 */
export function DashboardSkeleton() {
    return (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {Array.from({ length: 4 }).map((_, i) => (
                <StatSkeleton key={i} />
            ))}
        </div>
    );
}
