'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import {
    Send, User, Flame, ChevronLeft, ChevronRight, Loader2,
    Play, Square, Plus, Beaker, Clock, Sparkles, Timer, AlertTriangle,
} from 'lucide-react';
import Link from 'next/link';
import toast from 'react-hot-toast';
import { cn } from '@/lib/utils';
import { apiFetch, ApiClientError } from '@/lib/api';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface BrewDaySession {
    batch_id: string;
    batch_name: string;
    recipe: {
        name: string;
        target_og: number;
        target_fg?: number;
        target_volume_l: number;
    };
    phase: string;
    phase_index: number;
    started_at: string;
    phase_started_at: string;
    gravity_readings: GravityReading[];
    corrections_applied: Correction[];
}

interface GravityReading {
    sg: number;
    volume_l: number;
    stage: string;
    timestamp: string;
}

interface Correction {
    type: string;
    amount: number;
    unit: string;
    stage: string;
    timestamp: string;
}

interface BrewTimer {
    name: string;
    duration_min: number;
    started_at: string;
    addition_type: string;
}

interface ChatMessage {
    role: 'user' | 'assistant';
    content: string;
}

interface CorrectionResult {
    type: string;
    amount: number;
    unit: string;
    explanation: string;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const PHASES = ['Setup', 'Strike', 'Mash', 'Sparge', 'Boil', 'Knockout', 'Complete'] as const;

const TIMER_DURATIONS = [5, 10, 15, 30, 45, 60] as const;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatElapsed(startIso: string): string {
    const elapsed = Math.max(0, Math.floor((Date.now() - new Date(startIso).getTime()) / 1000));
    const h = Math.floor(elapsed / 3600);
    const m = Math.floor((elapsed % 3600) / 60);
    const s = elapsed % 60;
    return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

function timerRemainingSec(timer: BrewTimer): number {
    const endMs = new Date(timer.started_at).getTime() + timer.duration_min * 60_000;
    return Math.max(0, Math.floor((endMs - Date.now()) / 1000));
}

function formatMMSS(totalSec: number): string {
    const m = Math.floor(totalSec / 60);
    const s = totalSec % 60;
    return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function PhaseIndicatorPill({ phase }: { phase: string }) {
    return (
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-purple-600/15 text-purple-400 border border-purple-500/20">
            <span className="w-1.5 h-1.5 rounded-full bg-purple-400 animate-pulse" />
            {phase}
        </span>
    );
}

function PhaseStepper({ currentIndex }: { currentIndex: number }) {
    return (
        <div className="flex items-center gap-1 overflow-x-auto pb-2">
            {PHASES.map((p, i) => {
                const isComplete = i < currentIndex;
                const isCurrent = i === currentIndex;
                return (
                    <div key={p} className="flex items-center gap-1 shrink-0">
                        <div
                            className={cn(
                                'flex items-center justify-center w-7 h-7 rounded-full text-[10px] font-bold transition-all duration-300',
                                isComplete && 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30',
                                isCurrent && 'bg-purple-600/20 text-purple-400 border border-purple-500/40 ring-2 ring-purple-500/20',
                                !isComplete && !isCurrent && 'bg-secondary/30 text-muted-foreground border border-border/30'
                            )}
                        >
                            {i + 1}
                        </div>
                        <span
                            className={cn(
                                'text-[10px] font-medium hidden sm:inline',
                                isComplete && 'text-emerald-400',
                                isCurrent && 'text-purple-400',
                                !isComplete && !isCurrent && 'text-muted-foreground/60'
                            )}
                        >
                            {p}
                        </span>
                        {i < PHASES.length - 1 && (
                            <div className={cn(
                                'w-3 h-px',
                                isComplete ? 'bg-emerald-500/40' : 'bg-border/30'
                            )} />
                        )}
                    </div>
                );
            })}
        </div>
    );
}

function TimerCard({ timer, remaining }: { timer: BrewTimer; remaining: number }) {
    const totalSec = timer.duration_min * 60;
    const pct = totalSec > 0 ? ((totalSec - remaining) / totalSec) * 100 : 100;
    const isUrgent = remaining > 0 && remaining < 60;
    const isDone = remaining === 0;

    return (
        <div
            className={cn(
                'relative bg-card/50 backdrop-blur-sm border rounded-2xl p-4 transition-all duration-300',
                isUrgent && 'border-amber-500/60 animate-pulse shadow-[0_0_15px_rgba(245,158,11,0.15)]',
                isDone && 'border-emerald-500/40 opacity-70',
                !isUrgent && !isDone && 'border-border/50'
            )}
        >
            <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                    <Timer className={cn('w-4 h-4', isUrgent ? 'text-amber-400' : isDone ? 'text-emerald-400' : 'text-muted-foreground')} />
                    <span className="text-sm font-medium truncate">{timer.name}</span>
                </div>
                <span className={cn(
                    'text-lg font-mono font-bold tabular-nums',
                    isUrgent ? 'text-amber-400' : isDone ? 'text-emerald-400' : 'text-foreground'
                )}>
                    {isDone ? 'DONE' : formatMMSS(remaining)}
                </span>
            </div>
            <div className="h-1.5 bg-secondary/40 rounded-full overflow-hidden">
                <div
                    className={cn(
                        'h-full rounded-full transition-all duration-1000',
                        isUrgent ? 'bg-amber-500' : isDone ? 'bg-emerald-500' : 'bg-purple-500'
                    )}
                    style={{ width: `${Math.min(100, pct)}%` }}
                />
            </div>
            <span className="text-[10px] text-muted-foreground mt-1 block">
                {timer.duration_min} min total
                {timer.addition_type && ` · ${timer.addition_type}`}
            </span>
        </div>
    );
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function BrewDayPage() {
    // ── Session State ──
    const [session, setSession] = useState<BrewDaySession | null>(null);
    const [sessionLoading, setSessionLoading] = useState(true);

    // ── Start Form ──
    const [startForm, setStartForm] = useState({
        batch_id: '',
        recipe_name: '',
        target_og: '1.050',
        target_volume: '20',
    });
    const [starting, setStarting] = useState(false);

    // ── Timers ──
    const [timers, setTimers] = useState<BrewTimer[]>([]);
    const [timerRemainings, setTimerRemainings] = useState<Record<string, number>>({});
    const [newTimerName, setNewTimerName] = useState('');
    const [newTimerDuration, setNewTimerDuration] = useState<number>(15);

    // ── Gravity ──
    const [gravityForm, setGravityForm] = useState({ sg: '1.050', volume: '20', stage: 'pre_boil' });
    const [correctionResult, setCorrectionResult] = useState<CorrectionResult | null>(null);
    const [checkingGravity, setCheckingGravity] = useState(false);

    // ── Chat ──
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [chatInput, setChatInput] = useState('');
    const [chatLoading, setChatLoading] = useState(false);
    const chatScrollRef = useRef<HTMLDivElement>(null);

    // ── Session Timer Display ──
    const [elapsed, setElapsed] = useState('00:00:00');

    // ── Phase advancing ──
    const [advancing, setAdvancing] = useState(false);

    // ── Fired timer alerts (track by name to avoid duplicate toasts) ──
    const firedTimerAlerts = useRef<Set<string>>(new Set());

    // ────────────────────────────────────────────────────────────────────
    // Effects
    // ────────────────────────────────────────────────────────────────────

    // Check for active session on mount
    useEffect(() => {
        let cancelled = false;
        (async () => {
            try {
                const res = await apiFetch<{ data: BrewDaySession }>('/api/brewday/state?batch_id=last');
                if (!cancelled) {
                    const s = res.data || (res as unknown as BrewDaySession);
                    setSession(s);
                    setMessages([{ role: 'assistant', content: `Brew day started! I'll guide you through each phase. What are we brewing today?` }]);
                }
            } catch (err) {
                // 404 = no active session, that's fine
                if (err instanceof ApiClientError && err.status !== 404) {
                    console.error('Failed to load brew day state:', err);
                }
            } finally {
                if (!cancelled) setSessionLoading(false);
            }
        })();
        return () => { cancelled = true; };
    }, []);

    // Elapsed clock
    useEffect(() => {
        if (!session) return;
        const tick = () => setElapsed(formatElapsed(session.started_at));
        tick();
        const id = setInterval(tick, 1000);
        return () => clearInterval(id);
    }, [session]);

    // Poll timers
    useEffect(() => {
        if (!session) return;
        let cancelled = false;
        const poll = async () => {
            try {
                const res = await apiFetch<{ data: BrewTimer[] }>(`/api/brewday/timers?batch_id=${encodeURIComponent(session.batch_id)}`);
                if (!cancelled) {
                    const t = res.data || (res as unknown as BrewTimer[]);
                    setTimers(Array.isArray(t) ? t : []);
                }
            } catch {
                // Ignore polling errors
            }
        };
        poll();
        const id = setInterval(poll, 10_000);
        return () => { cancelled = true; clearInterval(id); };
    }, [session]);

    // Timer countdown tick
    useEffect(() => {
        if (timers.length === 0) return;
        const tick = () => {
            const map: Record<string, number> = {};
            timers.forEach(t => {
                const rem = timerRemainingSec(t);
                map[t.name] = rem;
                // Fire toast when timer hits 0
                if (rem === 0 && !firedTimerAlerts.current.has(t.name)) {
                    firedTimerAlerts.current.add(t.name);
                    toast(`⏰ Timer "${t.name}" is done!`, { icon: '🔔', duration: 8000 });
                }
            });
            setTimerRemainings(map);
        };
        tick();
        const id = setInterval(tick, 1000);
        return () => clearInterval(id);
    }, [timers]);

    // Auto-scroll chat
    useEffect(() => {
        if (chatScrollRef.current) {
            chatScrollRef.current.scrollTop = chatScrollRef.current.scrollHeight;
        }
    }, [messages]);

    // ────────────────────────────────────────────────────────────────────
    // Actions
    // ────────────────────────────────────────────────────────────────────

    const startSession = async () => {
        if (!startForm.batch_id.trim() || !startForm.recipe_name.trim()) {
            toast.error('Batch ID and recipe name are required.');
            return;
        }
        setStarting(true);
        try {
            const res = await apiFetch<{ data: BrewDaySession }>('/api/brewday/start', {
                method: 'POST',
                body: {
                    batch_id: startForm.batch_id.trim(),
                    recipe: {
                        name: startForm.recipe_name.trim(),
                        target_og: parseFloat(startForm.target_og) || 1.050,
                        target_volume_l: parseFloat(startForm.target_volume) || 20,
                    },
                },
            });
            const s = res.data || (res as unknown as BrewDaySession);
            setSession(s);
            setMessages([{ role: 'assistant', content: `Brew day started! I'll guide you through each phase. What are we brewing today?` }]);
            toast.success('Brew day session started!');
        } catch (err) {
            toast.error('Failed to start session. Is the backend running?');
            console.error(err);
        } finally {
            setStarting(false);
        }
    };

    const advancePhase = async () => {
        if (!session) return;
        setAdvancing(true);
        try {
            const res = await apiFetch<{ data: BrewDaySession }>('/api/brewday/action', {
                method: 'POST',
                body: { batch_id: session.batch_id, action_type: 'next_phase', message: '' },
            });
            const s = res.data || (res as unknown as BrewDaySession);
            setSession(s);
            toast.success(`Advanced to ${s.phase}`);
        } catch {
            toast.error('Failed to advance phase');
        } finally {
            setAdvancing(false);
        }
    };

    const endSession = async () => {
        if (!session) return;
        try {
            await apiFetch('/api/brewday/complete', {
                method: 'POST',
                body: { batch_id: session.batch_id },
            });
            setSession(null);
            setTimers([]);
            setMessages([]);
            setCorrectionResult(null);
            firedTimerAlerts.current.clear();
            toast.success('Brew day session ended!');
        } catch {
            toast.error('Failed to end session');
        }
    };

    const addTimer = async () => {
        if (!session || !newTimerName.trim()) return;
        try {
            await apiFetch('/api/brewday/action', {
                method: 'POST',
                body: {
                    batch_id: session.batch_id,
                    action_type: 'add_timer',
                    message: JSON.stringify({ name: newTimerName.trim(), duration_min: newTimerDuration }),
                },
            });
            setNewTimerName('');
            // Re-fetch timers
            const res = await apiFetch<{ data: BrewTimer[] }>(`/api/brewday/timers?batch_id=${encodeURIComponent(session.batch_id)}`);
            const t = res.data || (res as unknown as BrewTimer[]);
            setTimers(Array.isArray(t) ? t : []);
            toast.success('Timer added');
        } catch {
            toast.error('Failed to add timer');
        }
    };

    const checkGravity = async () => {
        if (!session) return;
        setCheckingGravity(true);
        setCorrectionResult(null);
        try {
            const res = await apiFetch<{ data: CorrectionResult }>('/api/brewday/correct', {
                method: 'POST',
                body: {
                    batch_id: session.batch_id,
                    measured_sg: parseFloat(gravityForm.sg),
                    measured_volume: parseFloat(gravityForm.volume),
                    stage: gravityForm.stage,
                },
            });
            const c = res.data || (res as unknown as CorrectionResult);
            setCorrectionResult(c);
        } catch {
            toast.error('Failed to check gravity');
        } finally {
            setCheckingGravity(false);
        }
    };

    const sendChat = useCallback(async () => {
        if (!chatInput.trim() || chatLoading || !session) return;
        const userMsg = chatInput.trim();
        setChatInput('');
        setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
        setChatLoading(true);
        try {
            const res = await apiFetch<{ data: { response: string } }>('/api/brewday/action', {
                method: 'POST',
                body: { batch_id: session.batch_id, action_type: 'chat', message: userMsg },
            });
            const data = res.data || (res as unknown as { response: string });
            setMessages(prev => [...prev, { role: 'assistant', content: data.response || 'No response from coach.' }]);
        } catch {
            setMessages(prev => [...prev, { role: 'assistant', content: 'Connection to Brew Day Coach failed. Is the backend running?' }]);
        } finally {
            setChatLoading(false);
        }
    }, [chatInput, chatLoading, session]);

    // ────────────────────────────────────────────────────────────────────
    // Render
    // ────────────────────────────────────────────────────────────────────

    return (
        <main className="flex flex-col h-[calc(100vh-4rem)] md:h-screen bg-background text-foreground overflow-hidden">
            {/* ── Header ── */}
            <header className="flex items-center justify-between p-4 border-b border-border/50 bg-background/80 backdrop-blur-md sticky top-0 z-10 shrink-0">
                <div className="flex items-center gap-3">
                    <Link href="/" className="p-2 rounded-full hover:bg-secondary transition-colors md:hidden">
                        <ChevronLeft className="w-5 h-5" />
                    </Link>
                    <div className="bg-amber-500/10 p-2 rounded-xl">
                        <Flame className="w-6 h-6 text-amber-500" />
                    </div>
                    <div>
                        <h1 className="font-bold tracking-tight">Brew Day Coach</h1>
                        <div className="flex items-center gap-2">
                            {session ? (
                                <>
                                    <PhaseIndicatorPill phase={session.phase} />
                                    <span className="text-xs text-muted-foreground font-mono tabular-nums">{elapsed}</span>
                                </>
                            ) : (
                                <span className="text-xs text-muted-foreground">No active session</span>
                            )}
                        </div>
                    </div>
                </div>
            </header>

            {/* ── Body ── */}
            <div className="flex-1 flex flex-col md:flex-row overflow-hidden">
                {/* ═══════════ LEFT PANEL — Controls ═══════════ */}
                <div className="md:w-[40%] md:border-r border-border/50 overflow-y-auto p-4 md:p-6 space-y-5">
                    {sessionLoading ? (
                        <div className="flex items-center justify-center h-40">
                            <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
                        </div>
                    ) : !session ? (
                        /* ── Start Session Form ── */
                        <div className="animate-in fade-in slide-in-from-bottom-2 duration-300">
                            <div className="bg-card/50 backdrop-blur-sm border border-border/50 rounded-2xl p-6 space-y-5">
                                <div className="flex items-center gap-3 mb-2">
                                    <div className="bg-amber-500/10 p-2 rounded-xl">
                                        <Play className="w-5 h-5 text-amber-500" />
                                    </div>
                                    <div>
                                        <h2 className="font-bold text-lg">Start Brew Day</h2>
                                        <p className="text-xs text-muted-foreground">Configure your session and let's get brewing</p>
                                    </div>
                                </div>

                                <div className="space-y-3">
                                    <div>
                                        <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1.5 block">Batch ID</label>
                                        <input
                                            type="text"
                                            value={startForm.batch_id}
                                            onChange={e => setStartForm(f => ({ ...f, batch_id: e.target.value }))}
                                            placeholder="e.g. BATCH-042"
                                            className="w-full bg-secondary/50 border border-border/50 rounded-xl px-4 py-3 text-sm focus:ring-2 focus:ring-amber-500/20 outline-none transition-all"
                                        />
                                    </div>
                                    <div>
                                        <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1.5 block">Recipe Name</label>
                                        <input
                                            type="text"
                                            value={startForm.recipe_name}
                                            onChange={e => setStartForm(f => ({ ...f, recipe_name: e.target.value }))}
                                            placeholder="e.g. West Coast IPA"
                                            className="w-full bg-secondary/50 border border-border/50 rounded-xl px-4 py-3 text-sm focus:ring-2 focus:ring-amber-500/20 outline-none transition-all"
                                        />
                                    </div>
                                    <div className="grid grid-cols-2 gap-3">
                                        <div>
                                            <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1.5 block">Target OG</label>
                                            <input
                                                type="number"
                                                step="0.001"
                                                value={startForm.target_og}
                                                onChange={e => setStartForm(f => ({ ...f, target_og: e.target.value }))}
                                                className="w-full bg-secondary/50 border border-border/50 rounded-xl px-4 py-3 text-sm focus:ring-2 focus:ring-amber-500/20 outline-none transition-all"
                                            />
                                        </div>
                                        <div>
                                            <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1.5 block">Target Vol (L)</label>
                                            <input
                                                type="number"
                                                step="0.5"
                                                value={startForm.target_volume}
                                                onChange={e => setStartForm(f => ({ ...f, target_volume: e.target.value }))}
                                                className="w-full bg-secondary/50 border border-border/50 rounded-xl px-4 py-3 text-sm focus:ring-2 focus:ring-amber-500/20 outline-none transition-all"
                                            />
                                        </div>
                                    </div>
                                </div>

                                <button
                                    onClick={startSession}
                                    disabled={starting}
                                    className="w-full flex items-center justify-center gap-2 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold py-3 rounded-xl transition-colors disabled:opacity-50"
                                >
                                    {starting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                                    Start Session
                                </button>
                            </div>
                        </div>
                    ) : (
                        /* ── Active Session Controls ── */
                        <div className="space-y-5 animate-in fade-in slide-in-from-bottom-2 duration-300">
                            {/* Phase Stepper */}
                            <div className="bg-card/50 backdrop-blur-sm border border-border/50 rounded-2xl p-4">
                                <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Phase Progress</h3>
                                <PhaseStepper currentIndex={session.phase_index} />
                                <button
                                    onClick={advancePhase}
                                    disabled={advancing || session.phase_index >= PHASES.length - 1}
                                    className="mt-3 w-full flex items-center justify-center gap-2 bg-purple-600/15 hover:bg-purple-600/25 text-purple-400 font-semibold py-2.5 rounded-xl transition-colors disabled:opacity-40 border border-purple-500/20"
                                >
                                    {advancing ? <Loader2 className="w-4 h-4 animate-spin" /> : <ChevronRight className="w-4 h-4" />}
                                    Next Phase
                                </button>
                            </div>

                            {/* Timers */}
                            <div className="bg-card/50 backdrop-blur-sm border border-border/50 rounded-2xl p-4">
                                <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3 flex items-center gap-2">
                                    <Clock className="w-3.5 h-3.5" /> Active Timers
                                </h3>
                                {timers.length === 0 ? (
                                    <p className="text-sm text-muted-foreground/60 text-center py-4">No active timers</p>
                                ) : (
                                    <div className="space-y-3 mb-4">
                                        {timers.map(t => (
                                            <TimerCard key={t.name} timer={t} remaining={timerRemainings[t.name] ?? timerRemainingSec(t)} />
                                        ))}
                                    </div>
                                )}

                                {/* Add Timer */}
                                <div className="flex gap-2 mt-3">
                                    <input
                                        type="text"
                                        value={newTimerName}
                                        onChange={e => setNewTimerName(e.target.value)}
                                        placeholder="Timer name…"
                                        className="flex-1 min-w-0 bg-secondary/50 border border-border/50 rounded-xl px-3 py-2 text-sm focus:ring-2 focus:ring-amber-500/20 outline-none"
                                    />
                                    <select
                                        value={newTimerDuration}
                                        onChange={e => setNewTimerDuration(Number(e.target.value))}
                                        className="bg-secondary/50 border border-border/50 rounded-xl px-3 py-2 text-sm focus:ring-2 focus:ring-amber-500/20 outline-none"
                                    >
                                        {TIMER_DURATIONS.map(d => (
                                            <option key={d} value={d}>{d} min</option>
                                        ))}
                                    </select>
                                    <button
                                        onClick={addTimer}
                                        disabled={!newTimerName.trim()}
                                        className="p-2 rounded-xl bg-amber-600/15 text-amber-400 hover:bg-amber-600/25 transition-colors disabled:opacity-40 border border-amber-500/20"
                                    >
                                        <Plus className="w-4 h-4" />
                                    </button>
                                </div>
                            </div>

                            {/* Gravity Reading */}
                            <div className="bg-card/50 backdrop-blur-sm border border-border/50 rounded-2xl p-4">
                                <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3 flex items-center gap-2">
                                    <Beaker className="w-3.5 h-3.5" /> Gravity Reading
                                </h3>
                                <div className="grid grid-cols-2 gap-3 mb-3">
                                    <div>
                                        <label className="text-[10px] font-semibold text-muted-foreground uppercase mb-1 block">Measured SG</label>
                                        <input
                                            type="number"
                                            step="0.001"
                                            value={gravityForm.sg}
                                            onChange={e => setGravityForm(f => ({ ...f, sg: e.target.value }))}
                                            className="w-full bg-secondary/50 border border-border/50 rounded-xl px-3 py-2 text-sm focus:ring-2 focus:ring-amber-500/20 outline-none"
                                        />
                                    </div>
                                    <div>
                                        <label className="text-[10px] font-semibold text-muted-foreground uppercase mb-1 block">Volume (L)</label>
                                        <input
                                            type="number"
                                            step="0.5"
                                            value={gravityForm.volume}
                                            onChange={e => setGravityForm(f => ({ ...f, volume: e.target.value }))}
                                            className="w-full bg-secondary/50 border border-border/50 rounded-xl px-3 py-2 text-sm focus:ring-2 focus:ring-amber-500/20 outline-none"
                                        />
                                    </div>
                                </div>
                                <div className="mb-3">
                                    <label className="text-[10px] font-semibold text-muted-foreground uppercase mb-1 block">Stage</label>
                                    <select
                                        value={gravityForm.stage}
                                        onChange={e => setGravityForm(f => ({ ...f, stage: e.target.value }))}
                                        className="w-full bg-secondary/50 border border-border/50 rounded-xl px-3 py-2 text-sm focus:ring-2 focus:ring-amber-500/20 outline-none"
                                    >
                                        <option value="pre_boil">Pre-Boil</option>
                                        <option value="post_boil">Post-Boil</option>
                                    </select>
                                </div>
                                <button
                                    onClick={checkGravity}
                                    disabled={checkingGravity}
                                    className="w-full flex items-center justify-center gap-2 bg-amber-600/15 hover:bg-amber-600/25 text-amber-400 font-semibold py-2.5 rounded-xl transition-colors disabled:opacity-40 border border-amber-500/20"
                                >
                                    {checkingGravity ? <Loader2 className="w-4 h-4 animate-spin" /> : <Beaker className="w-4 h-4" />}
                                    Check Gravity
                                </button>

                                {/* Correction Result */}
                                {correctionResult && (
                                    <div className={cn(
                                        'mt-4 p-4 rounded-xl border animate-in fade-in slide-in-from-bottom-2 duration-300',
                                        correctionResult.amount === 0
                                            ? 'bg-emerald-500/10 border-emerald-500/30'
                                            : 'bg-amber-500/10 border-amber-500/30'
                                    )}>
                                        <div className="flex items-center gap-2 mb-2">
                                            {correctionResult.amount === 0 ? (
                                                <span className="text-emerald-400 text-sm font-bold">✓ On Target</span>
                                            ) : (
                                                <>
                                                    <AlertTriangle className="w-4 h-4 text-amber-400" />
                                                    <span className="text-amber-400 text-sm font-bold">{correctionResult.type}</span>
                                                </>
                                            )}
                                        </div>
                                        {correctionResult.amount > 0 && (
                                            <p className="text-2xl font-bold font-mono tabular-nums mb-1">
                                                {correctionResult.amount.toFixed(1)} {correctionResult.unit}
                                            </p>
                                        )}
                                        {correctionResult.explanation && (
                                            <p className="text-xs text-muted-foreground leading-relaxed">{correctionResult.explanation}</p>
                                        )}
                                    </div>
                                )}
                            </div>

                            {/* End Session */}
                            <button
                                onClick={endSession}
                                className="w-full flex items-center justify-center gap-2 bg-red-600/15 hover:bg-red-600/25 text-red-400 font-semibold py-3 rounded-xl transition-colors border border-red-500/20"
                            >
                                <Square className="w-4 h-4" />
                                End Session
                            </button>
                        </div>
                    )}
                </div>

                {/* ═══════════ RIGHT PANEL — AI Coach Chat ═══════════ */}
                <div className="flex-1 flex flex-col overflow-hidden border-t md:border-t-0 border-border/50">
                    {/* Chat Header */}
                    <div className="flex items-center gap-3 p-4 border-b border-border/50 bg-background/60 backdrop-blur-sm shrink-0">
                        <div className="bg-amber-500/10 p-2 rounded-xl">
                            <Flame className="w-5 h-5 text-amber-500" />
                        </div>
                        <div>
                            <h2 className="font-bold text-sm">Brew Day Coach</h2>
                            <div className="flex items-center gap-1.5">
                                <div className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse" />
                                <span className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider">
                                    {session ? 'Active Session' : 'Standby'}
                                </span>
                            </div>
                        </div>
                    </div>

                    {/* Chat Messages */}
                    <div
                        ref={chatScrollRef}
                        className="flex-1 overflow-y-auto p-4 md:p-6 space-y-6"
                    >
                        {!session && messages.length === 0 && (
                            <div className="flex flex-col items-center justify-center h-full text-center space-y-4">
                                <div className="bg-amber-500/10 p-4 rounded-2xl">
                                    <Flame className="w-10 h-10 text-amber-500/60" />
                                </div>
                                <div>
                                    <h3 className="font-bold text-lg mb-1">Ready to Brew?</h3>
                                    <p className="text-sm text-muted-foreground max-w-xs">
                                        Start a brew day session on the left to activate your AI coaching assistant.
                                    </p>
                                </div>
                            </div>
                        )}

                        {messages.map((msg, i) => (
                            <div
                                key={i}
                                className={cn(
                                    'flex items-start gap-3 max-w-[85%] animate-in fade-in slide-in-from-bottom-2 duration-300',
                                    msg.role === 'user' ? 'ml-auto flex-row-reverse' : ''
                                )}
                            >
                                <div className={cn(
                                    'p-2 rounded-xl shrink-0',
                                    msg.role === 'user' ? 'bg-primary/10' : 'bg-amber-500/10'
                                )}>
                                    {msg.role === 'user'
                                        ? <User className="w-5 h-5 text-primary" />
                                        : <Sparkles className="w-5 h-5 text-amber-500" />}
                                </div>
                                <div className={cn(
                                    'p-4 rounded-2xl text-sm leading-relaxed',
                                    msg.role === 'user'
                                        ? 'bg-primary text-primary-foreground rounded-tr-none'
                                        : 'bg-card border border-border/50 rounded-tl-none shadow-sm'
                                )}>
                                    {msg.content}
                                </div>
                            </div>
                        ))}

                        {chatLoading && (
                            <div className="flex items-start gap-3 max-w-[85%] animate-pulse">
                                <div className="bg-amber-500/10 p-2 rounded-xl">
                                    <Flame className="w-5 h-5 text-amber-500" />
                                </div>
                                <div className="bg-card border border-border/50 p-4 rounded-2xl rounded-tl-none">
                                    <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Chat Input */}
                    <div className="p-4 md:p-6 border-t border-border/50 bg-background/80 backdrop-blur-md shrink-0">
                        <div className="max-w-4xl mx-auto relative">
                            <input
                                type="text"
                                value={chatInput}
                                onChange={e => setChatInput(e.target.value)}
                                onKeyDown={e => e.key === 'Enter' && sendChat()}
                                placeholder={session ? 'Ask the Brew Day Coach…' : 'Start a session first…'}
                                disabled={!session}
                                className="w-full bg-secondary/50 border border-border/50 rounded-2xl px-5 py-4 pr-14 focus:ring-2 focus:ring-amber-500/20 outline-none transition-all shadow-inner disabled:opacity-50"
                            />
                            <button
                                onClick={sendChat}
                                disabled={!chatInput.trim() || chatLoading || !session}
                                className="absolute right-2 top-2 bottom-2 px-4 rounded-xl bg-amber-600 text-white hover:bg-amber-500 transition-colors disabled:opacity-50 disabled:grayscale"
                            >
                                <Send className="w-4 h-4" />
                            </button>
                        </div>
                        <p className="text-[10px] text-center text-muted-foreground mt-3">
                            Brew Day Coach uses your live session data to provide real-time brewing guidance.
                        </p>
                    </div>
                </div>
            </div>
        </main>
    );
}
