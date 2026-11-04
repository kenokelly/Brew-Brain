'use client';

import { useState } from 'react';
import { Droplets, Check } from 'lucide-react';
import { toast } from 'react-hot-toast';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';
import type { FermentationSummary, WaterCalibration } from '@/types/api';
import { BetaCard } from './BetaCard';
import { num, sg3 } from './format';

const STATUS_STYLE: Record<WaterCalibration['status'], string> = {
    ready: 'text-[var(--b-accent)] bg-[var(--b-tile)]',
    calibrated: 'text-[var(--b-good)] bg-[var(--b-good)]/15',
    settling: 'text-[var(--b-warn)] bg-[var(--b-warn)]/15',
    waiting: 'text-[var(--b-muted)] bg-[var(--b-card-hi)]',
    implausible: 'text-[var(--b-bad)] bg-[var(--b-bad)]/15',
    error: 'text-[var(--b-bad)] bg-[var(--b-bad)]/15',
};

/** Replaces the fermentation card while the Tilt is in plain water. */
export function WaterTestCard({ s, onChanged }: { s: FermentationSummary; onChanged: () => void }) {
    const cal: WaterCalibration = s.calibration ?? { status: 'waiting', message: 'Collecting readings…' };
    const [applying, setApplying] = useState(false);
    const off = cal.raw_mean != null ? (cal.raw_mean - 1) * 1000 : null; // points off 1.000, raw

    const apply = async () => {
        setApplying(true);
        try {
            await api.post('/api/fermentation/water-test', { action: 'apply_offset' });
            toast.success(`Calibrated: offset ${cal.suggested_offset != null ? (cal.suggested_offset >= 0 ? '+' : '') + cal.suggested_offset.toFixed(3) : ''}`);
            onChanged();
        } catch (e) {
            toast.error(`Couldn't calibrate: ${e instanceof Error ? e.message : String(e)}`);
        } finally {
            setApplying(false);
        }
    };

    return (
        <BetaCard
            icon={Droplets}
            title="Water test"
            subtitle="Tilt in plain water · calibration check"
            live={(s.sensor.last_reading_age_min ?? Infinity) <= 60}
            badge={<span className={cn('px-3 py-1 rounded-full text-xs font-bold tracking-wider uppercase', STATUS_STYLE[cal.status])}>{cal.status}</span>}
        >
            <div className="flex items-baseline gap-3 flex-wrap">
                <span className="beta-mono text-6xl md:text-7xl font-bold tracking-tighter">{sg3(cal.raw_mean ?? s.sg)}</span>
                <span className="text-[var(--b-muted)]">raw · expected <span className="beta-mono text-[var(--b-text)]">1.000</span></span>
            </div>

            <div className="grid grid-cols-3 gap-2 mt-5">
                <Stat label="Off by" value={off == null ? '--' : `${off >= 0 ? '+' : ''}${num(off, 0)} pts`} />
                <Stat label="Wobble" value={cal.spread != null ? `${num(cal.spread * 1000, 0)} pts` : '--'} />
                <Stat label="Water °C" value={num(s.temp)} />
            </div>

            <p className={cn('mt-4 text-sm', cal.status === 'implausible' ? 'text-[#fca5a5]' : 'text-[var(--b-muted)]')}>{cal.message}</p>

            <div className="flex items-center justify-between gap-3 mt-4 text-sm">
                <span className="text-[var(--b-muted)]">
                    Offset now <span className="beta-mono text-[var(--b-text)]">{cal.current_offset != null ? (cal.current_offset >= 0 ? '+' : '') + cal.current_offset.toFixed(3) : '--'}</span>
                    {cal.status === 'ready' && cal.suggested_offset != null && (
                        <> → <span className="beta-mono text-[var(--b-accent)]">{(cal.suggested_offset >= 0 ? '+' : '') + cal.suggested_offset.toFixed(3)}</span></>
                    )}
                </span>
                {cal.status === 'ready' && (
                    <button
                        type="button"
                        onClick={apply}
                        disabled={applying}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full whitespace-nowrap bg-[var(--b-tile)] text-[var(--b-accent)] font-semibold disabled:opacity-50"
                    >
                        <Check className="w-4 h-4" /> Apply offset
                    </button>
                )}
            </div>
        </BetaCard>
    );
}

function Stat({ value, label }: { value: string; label: string }) {
    return (
        <div className="rounded-xl bg-[var(--b-card-hi)] py-3 px-2 text-center">
            <div className="beta-mono text-xl font-bold">{value}</div>
            <div className="text-[10px] md:text-xs font-semibold tracking-wider uppercase text-[var(--b-muted)] mt-1">{label}</div>
        </div>
    );
}
