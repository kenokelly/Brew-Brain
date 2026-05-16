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
        <div className="space-y-6 p-4 md:p-8">
            <div className="flex justify-between items-center">
                <div className="space-y-2">
                    <Skeleton className="h-10 w-48" />
                    <Skeleton className="h-4 w-64" />
                </div>
                <Skeleton className="h-10 w-32 rounded-full" />
            </div>
            
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {Array.from({ length: 4 }).map((_, i) => (
                    <StatSkeleton key={i} />
                ))}
            </div>

            <div className="h-32 w-full rounded-2xl bg-muted/20 animate-pulse" />

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <CardSkeleton />
                <CardSkeleton />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                <StatSkeleton />
                <StatSkeleton />
                <StatSkeleton />
            </div>
        </div>
    );
}

/**
 * Anomaly Widget Skeleton
 */
export function AnomalySkeleton() {
    return (
        <div className="rounded-2xl border border-border/50 bg-card p-6 space-y-4">
            <div className="flex justify-between items-center">
                <Skeleton className="h-4 w-24" />
                <Skeleton className="h-8 w-8 rounded-full" />
            </div>
            <Skeleton className="h-10 w-32" />
            <Skeleton className="h-3 w-20" />
        </div>
    );
}

/**
 * Advice Widget Skeleton
 */
export function AdviceSkeleton() {
    return (
        <div className="rounded-2xl border border-border/50 bg-card p-6 space-y-4">
            <div className="flex justify-between items-center">
                <div className="flex items-center gap-2">
                    <Skeleton className="h-8 w-8 rounded-xl" />
                    <Skeleton className="h-4 w-32" />
                </div>
                <Skeleton className="h-8 w-8 rounded-full" />
            </div>
            <div className="flex gap-3">
                <Skeleton className="h-5 w-5 shrink-0" />
                <div className="space-y-2 flex-1">
                    <Skeleton className="h-4 w-full" />
                    <Skeleton className="h-4 w-full" />
                    <Skeleton className="h-4 w-2/3" />
                </div>
            </div>
        </div>
    );
}

/**
 * Prediction Widget Skeleton
 */
export function PredictionSkeleton() {
    return (
        <div className="rounded-2xl border border-border/50 bg-card p-6 space-y-6">
            <div className="flex justify-between items-center border-b border-border/30 pb-4">
                <div className="flex items-center gap-2">
                    <Skeleton className="h-8 w-8 rounded-lg" />
                    <div className="space-y-1">
                        <Skeleton className="h-4 w-24" />
                        <Skeleton className="h-3 w-32" />
                    </div>
                </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                    <Skeleton className="h-3 w-16" />
                    <Skeleton className="h-8 w-20" />
                </div>
                <div className="space-y-2">
                    <Skeleton className="h-3 w-16" />
                    <Skeleton className="h-8 w-20" />
                </div>
            </div>
            <div className="space-y-3 pt-4 border-t border-border/30">
                <Skeleton className="h-3 w-24" />
                <div className="grid grid-cols-3 gap-2">
                    <Skeleton className="h-12 w-full rounded-lg" />
                    <Skeleton className="h-12 w-full rounded-lg" />
                    <Skeleton className="h-12 w-full rounded-lg" />
                </div>
            </div>
        </div>
    );
}
