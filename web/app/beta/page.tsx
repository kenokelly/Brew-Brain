'use client';

import { useState } from 'react';
import Link from 'next/link';
import { FlaskRound } from 'lucide-react';
import { toast } from 'react-hot-toast';
import { useFermentationHistory, useFermentationSummary, useJournal } from '@/lib/hooks';
import { BatchCard } from '@/components/beta/BatchCard';
import { FermentationCard } from '@/components/beta/FermentationCard';
import { FermentChart } from '@/components/beta/FermentChart';
import { JournalCard } from '@/components/beta/JournalCard';
import { VitalsCard } from '@/components/beta/VitalsCard';
import { CardError } from '@/components/beta/BetaCard';

/**
 * Beta dashboard: step timeline, fermentation velocity/ETA, native chart and
 * the autopilot journal in a dark instrument-panel style. Lives alongside the
 * production dashboard at / until it's promoted.
 */
export default function BetaDashboard() {
    const { data: summary, error: summaryError, isLoading, mutate: mutateSummary } = useFermentationSummary();
    const { data: history, error: historyError, mutate: mutateHistory } = useFermentationHistory();
    const { entries, error: journalError, mutate: mutateJournal } = useJournal(60);
    const [syncing, setSyncing] = useState(false);

    const sync = async () => {
        setSyncing(true);
        const id = toast.loading('Syncing with Brewfather…');
        try {
            const res = await fetch('/api/sync_brewfather', { method: 'POST' });
            const d = await res.json();
            if (res.ok && d.status === 'synced') {
                toast.success(`Synced ${d.data.name} · ${d.data.steps} fermentation steps`, { id });
                mutateSummary();
                mutateHistory();
            } else {
                toast.error(`Sync error: ${d.error || 'Unknown'}`, { id });
            }
        } catch (e) {
            toast.error(`Sync error: ${e instanceof Error ? e.message : String(e)}`, { id });
        } finally {
            setSyncing(false);
        }
    };

    return (
        <div className="beta-ui min-h-screen p-4 md:p-8 pb-24">
            <div className="max-w-7xl mx-auto space-y-5">
                <div className="flex items-center justify-between gap-3">
                    <div className="flex items-center gap-2 text-sm">
                        <FlaskRound className="w-4 h-4 text-[var(--b-accent)]" />
                        <span className="font-bold tracking-widest uppercase text-[var(--b-accent)]">Beta</span>
                        <span className="text-[var(--b-muted)] hidden sm:inline">New dashboard preview</span>
                    </div>
                    <Link href="/" className="text-sm text-[var(--b-muted)] hover:text-[var(--b-text)] underline underline-offset-4">
                        Back to current dashboard
                    </Link>
                </div>

                {isLoading && !summary ? (
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
                        {[0, 1, 2].map((i) => <div key={i} className="beta-card h-72 animate-pulse" />)}
                    </div>
                ) : !summary ? (
                    <div className="beta-card p-6">
                        <CardError message={`Couldn't load fermentation data${summaryError ? `: ${summaryError.message}` : ''}.`} />
                    </div>
                ) : (
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-5 items-start">
                        <div className="space-y-5">
                            <BatchCard s={summary} onSync={sync} syncing={syncing} />
                            <FermentationCard s={summary} />
                        </div>
                        <div className="space-y-5">
                            <FermentChart history={history} summary={summary} error={historyError} />
                            <VitalsCard s={summary} />
                        </div>
                        <JournalCard entries={entries} error={journalError} onAdded={() => mutateJournal()} />
                    </div>
                )}
            </div>
        </div>
    );
}
