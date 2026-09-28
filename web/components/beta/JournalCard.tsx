'use client';

import { useState } from 'react';
import { NotebookText, Send } from 'lucide-react';
import { toast } from 'react-hot-toast';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';
import type { JournalEntry } from '@/types/api';
import { BetaCard, CardError } from './BetaCard';
import { ago } from './format';

const KIND_ICON: Record<JournalEntry['kind'], string> = {
    alert: '⚠️',
    report: '📊',
    step: '🧭',
    phase: '🌿',
    note: '✏️',
    info: 'ℹ️',
};

const LEVEL_TEXT: Record<JournalEntry['level'], string> = {
    info: 'text-[var(--b-text)]',
    warning: 'text-[var(--b-text)]',
    critical: 'text-[#fca5a5]',
};

/** Autopilot journal: what Brew Brain noticed and did, newest first. */
export function JournalCard({ entries, error, onAdded }: {
    entries?: JournalEntry[];
    error?: unknown;
    onAdded: () => void;
}) {
    const [note, setNote] = useState('');
    const [saving, setSaving] = useState(false);

    const submit = async (e: React.FormEvent) => {
        e.preventDefault();
        const text = note.trim();
        if (!text) return;
        setSaving(true);
        try {
            await api.post('/api/fermentation/journal', { text });
            setNote('');
            onAdded();
        } catch (err) {
            toast.error(`Couldn't save note: ${err instanceof Error ? err.message : String(err)}`);
        } finally {
            setSaving(false);
        }
    };

    return (
        <BetaCard icon={NotebookText} title="Autopilot journal" subtitle="what the flow did, newest first" live={!error}>
            <form onSubmit={submit} className="flex gap-2 mb-4">
                <input
                    value={note}
                    onChange={(e) => setNote(e.target.value)}
                    maxLength={500}
                    placeholder="Add a note (dry hops in, hydrometer FG…)"
                    aria-label="Journal note"
                    className="flex-1 min-w-0 rounded-xl bg-[var(--b-card-hi)] border border-[var(--b-border)] px-3 py-2 text-sm placeholder:text-[var(--b-faint)] focus:outline-none focus:border-[var(--b-accent)]"
                />
                <button
                    type="submit"
                    disabled={saving || !note.trim()}
                    aria-label="Add note"
                    className="px-3 rounded-xl bg-[var(--b-tile)] text-[var(--b-accent)] disabled:opacity-40"
                >
                    <Send className="w-4 h-4" />
                </button>
            </form>

            {error ? (
                <CardError message="Journal unavailable." />
            ) : !entries?.length ? (
                <CardError message="Nothing logged yet. Alerts, step changes and phase changes appear here while Brew Active is on." />
            ) : (
                <ol className="divide-y divide-[var(--b-border)] max-h-[560px] overflow-y-auto pr-1 -mr-1">
                    {entries.map((e) => (
                        <li key={e.id} className="flex gap-3 py-3 first:pt-0">
                            <time
                                dateTime={e.ts}
                                title={new Date(e.ts).toLocaleString()}
                                className="w-9 shrink-0 text-sm text-[var(--b-faint)] beta-mono pt-0.5"
                            >
                                {ago(e.ts)}
                            </time>
                            <p className={cn('text-[15px] leading-snug', LEVEL_TEXT[e.level])}>
                                <span className="mr-1.5" aria-hidden>{e.text.match(/^\p{Extended_Pictographic}/u) ? '' : KIND_ICON[e.kind]}</span>
                                {e.text}
                            </p>
                        </li>
                    ))}
                </ol>
            )}
        </BetaCard>
    );
}
