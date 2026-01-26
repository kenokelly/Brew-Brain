'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import {
    Save,
    Bell,
    Beer,
    Database,
    Clock,
    RefreshCcw,
    ChevronLeft,
    Send,
    AlertTriangle,
    Hash,
    Trash2,
    Plus,
    Scale
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useSettings, useTaps, useStatus } from '@/lib/hooks';
import toast from 'react-hot-toast';

export default function SettingsPage() {
    const router = useRouter();
    const { data: initialSettings, mutate } = useSettings();
    const { data: taps, mutate: mutateTaps } = useTaps();
    const { data: status } = useStatus();

    // Form State
    const [settings, setSettings] = useState<Record<string, any>>({});
    const [saving, setSaving] = useState(false);
    const [calibrating, setCalibrating] = useState(false);
    const [manualSg, setManualSg] = useState('');

    // Modal State
    const [activeModal, setActiveModal] = useState<'manual' | 'snapshot' | null>(null);
    const [selectedTap, setSelectedTap] = useState<string | null>(null);

    // Manual Form State
    const [manualForm, setManualForm] = useState({
        name: '', style: '', abv: '5.0', srm: '5', ibu: '20',
        keg_total: '19', keg_remaining: '19', unit: 'L'
    });

    // Snapshot Form State
    const [snapshotForm, setSnapshotForm] = useState({
        unit: 'L',
        keg_total: '19'
    });

    useEffect(() => {
        if (initialSettings) {
            setSettings(initialSettings);
        }
    }, [initialSettings]);

    const handleChange = (key: string, value: any) => {
        setSettings(prev => ({ ...prev, [key]: value }));
    };

    const handleSave = async (e?: React.FormEvent) => {
        if (e) e.preventDefault();
        setSaving(true);
        try {
            const res = await fetch('/api/settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(settings)
            });
            if (res.ok) {
                toast.success('Settings saved successfully');
                mutate();
            } else {
                toast.error('Failed to save settings');
            }
        } catch (err) {
            toast.error('Connection error');
        } finally {
            setSaving(false);
        }
    };

    // --- Tap Logic ---

    const openManualTap = (tapId: string) => {
        setSelectedTap(tapId);
        setManualForm({
            name: '', style: '', abv: '5.0', srm: '5', ibu: '20',
            keg_total: '19', keg_remaining: '19', unit: 'L'
        });
        setActiveModal('manual');
    };

    const openSnapshotTap = (tapId: string) => {
        setSelectedTap(tapId);
        setSnapshotForm({ unit: 'L', keg_total: '19' });
        setActiveModal('snapshot');
    };

    const submitManualTap = async () => {
        if (!selectedTap) return;
        try {
            await fetch(`/api/taps/${selectedTap}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    action: 'manual',
                    name: manualForm.name,
                    style: manualForm.style,
                    abv: manualForm.abv,
                    srm: manualForm.srm,
                    ibu: manualForm.ibu,
                    keg_total: manualForm.keg_total,
                    keg_remaining: manualForm.keg_remaining,
                    volume_unit: manualForm.unit
                })
            });
            toast.success(`Tap ${selectedTap.replace('tap_', '')} updated`);
            mutateTaps();
            setActiveModal(null);
        } catch (e) { toast.error("Failed to update tap"); }
    };

    const submitSnapshotTap = async () => {
        if (!selectedTap) return;
        try {
            await fetch(`/api/taps/${selectedTap}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    action: 'assign_current',
                    keg_total: snapshotForm.keg_total,
                    keg_remaining: snapshotForm.keg_total,
                    volume_unit: snapshotForm.unit
                })
            });
            toast.success(`Snapshot assigned to ${selectedTap.replace('tap_', '')}`);
            mutateTaps();
            setActiveModal(null);
        } catch (e) { toast.error("Failed to assign snapshot"); }
    };

    const clearTap = async (tapId: string) => {
        if (!confirm('Are you sure you want to clear this tap?')) return;
        try {
            await fetch(`/api/taps/${tapId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action: 'clear' })
            });
            toast.success("Tap cleared");
            mutateTaps();
        } catch (e) { toast.error("Failed to clear tap"); }
    };

    // --- Legacy Actions ---

    const handleCalibrate = async () => {
        const val = parseFloat(manualSg);
        if (!val || val < 0.900 || val > 1.200) {
            toast.error("Invalid gravity reading (0.900 - 1.200)");
            return;
        }
        setCalibrating(true);
        try {
            const res = await fetch('/api/calibrate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ sg: val, source: "Manual Entry" })
            });
            const d = await res.json();
            if (d.status === 'success' || d.status === 'synced' || d.new_offset !== undefined) {
                toast.success(`Calibrated! New offset: ${d.new_offset || 'Updated'}`);
                mutate();
                setManualSg('');
            } else {
                toast.error(d.message || d.error || "Calibration failed");
            }
        } catch (e) {
            toast.error("Calibration request failed");
        } finally {
            setCalibrating(false);
        }
    };

    const handleSyncBrewfather = async () => {
        const toastId = toast.loading("Syncing with Brewfather...");
        try {
            const res = await fetch('/api/sync_brewfather', { method: 'POST' });
            const d = await res.json();
            if (d.status === 'synced') {
                toast.success(`Synced batch: ${d.data.name}`, { id: toastId });
                mutate();
            } else {
                toast.error(`Sync error: ${d.error || 'Unknown'}`, { id: toastId });
            }
        } catch (e) {
            toast.error("Connection failed", { id: toastId });
        }
    };

    const toggleTestMode = () => {
        const newVal = settings['test_mode'] === 'true' ? 'false' : 'true';
        handleChange('test_mode', newVal);
        setTimeout(() => handleSave(), 100);
    };

    return (
        <main className="min-h-screen bg-background text-foreground p-4 md:p-8 pb-32">
            <div className="max-w-4xl mx-auto space-y-8">

                {/* Header */}
                <header className="flex items-center justify-between sticky top-0 z-50 bg-background/80 backdrop-blur-md py-4 border-b border-border/50">
                    <div className="flex items-center gap-4">
                        <button
                            onClick={() => router.push('/')}
                            className="p-2 rounded-full hover:bg-secondary/80 transition-colors"
                        >
                            <ChevronLeft className="w-6 h-6" />
                        </button>
                        <div>
                            <h1 className="text-2xl md:text-3xl font-bold tracking-tight">System Settings</h1>
                            <p className="text-muted-foreground text-sm">One-stop configuration panel</p>
                        </div>
                    </div>
                    <div className="flex gap-2">
                        <button
                            onClick={handleSyncBrewfather}
                            className="hidden md:flex items-center gap-2 px-4 py-2 rounded-xl bg-blue-600/10 text-blue-500 hover:bg-blue-600/20 transition-all font-bold text-sm"
                        >
                            <RefreshCcw className="w-4 h-4" /> Sync BF
                        </button>
                        <button
                            onClick={(e) => handleSave(e)}
                            disabled={saving}
                            className="flex items-center gap-2 px-6 py-2 rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 transition-all font-bold shadow-lg disabled:opacity-50"
                        >
                            {saving ? <RefreshCcw className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                            <span className="hidden md:inline">{saving ? 'Saving...' : 'Save Changes'}</span>
                            <span className="md:hidden">Save</span>
                        </button>
                    </div>
                </header>

                {/* --- TAP MANAGEMENT (NEW) --- */}
                <section className="space-y-4">
                    <div className="flex items-center gap-2 text-primary font-semibold">
                        <Beer className="w-5 h-5" />
                        <h2>Tap Management</h2>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 bg-card border border-border/50 p-6 rounded-3xl">
                        {[1, 2, 3, 4].map(idx => {
                            const tapKey = `tap_${idx}`;
                            const tap = taps?.[tapKey];
                            const isActive = tap?.active;

                            return (
                                <div key={tapKey} className="bg-secondary/20 border border-border/50 rounded-xl p-4 flex flex-col justify-between min-h-[140px]">
                                    <div className="flex justify-between items-start mb-2">
                                        <span className="text-xs font-bold text-muted-foreground uppercase tracking-widest">Tap {idx}</span>
                                        {isActive ? (
                                            <span className="text-[10px] bg-green-500/20 text-green-400 px-2 py-0.5 rounded-full font-medium">Active</span>
                                        ) : (
                                            <span className="text-[10px] bg-secondary text-muted-foreground px-2 py-0.5 rounded-full font-medium">Empty</span>
                                        )}
                                    </div>

                                    {isActive ? (
                                        <>
                                            <div className="space-y-1 mb-4">
                                                <h4 className="font-bold text-lg truncate">{tap.name}</h4>
                                                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                                    <span className="text-amber-500 font-medium">{tap.abv}% ABV</span>
                                                    <span>•</span>
                                                    <span>{tap.style}</span>
                                                </div>
                                                <div className="text-xs text-muted-foreground">
                                                    Keg: {tap.keg_remaining}/{tap.keg_total} {tap.volume_unit}
                                                </div>
                                            </div>
                                            <button
                                                onClick={() => clearTap(tapKey)}
                                                className="w-full text-xs bg-red-500/10 hover:bg-red-500/20 text-red-400 py-2 rounded-lg transition-colors flex items-center justify-center gap-2"
                                            >
                                                <Trash2 className="w-3 h-3" /> Clear Tap
                                            </button>
                                        </>
                                    ) : (
                                        <div className="flex flex-col gap-2 mt-auto">
                                            <button
                                                onClick={() => openSnapshotTap(tapKey)}
                                                className="w-full text-xs bg-blue-600 hover:bg-blue-500 text-white py-2 rounded-lg transition-colors flex items-center justify-center gap-2"
                                            >
                                                <RefreshCcw className="w-3 h-3" /> Snapshot Current
                                            </button>
                                            <button
                                                onClick={() => openManualTap(tapKey)}
                                                className="w-full text-xs bg-secondary hover:bg-secondary/80 text-foreground py-2 rounded-lg transition-colors flex items-center justify-center gap-2"
                                            >
                                                <Plus className="w-3 h-3" /> Manual Entry
                                            </button>
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                </section>

                {/* Batch Profile */}
                <section className="space-y-4">
                    <div className="flex items-center gap-2 text-primary font-semibold">
                        <Database className="w-5 h-5" />
                        <h2>Batch Profile</h2>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 bg-card border border-border/50 p-6 rounded-3xl">
                        <div className="space-y-2">
                            <label className="text-sm font-medium text-muted-foreground">Batch Name</label>
                            <input
                                type="text"
                                value={settings['batch_name'] || ''}
                                onChange={(e) => handleChange('batch_name', e.target.value)}
                                className="w-full bg-secondary/30 border border-border/50 rounded-xl px-4 py-3 focus:ring-2 focus:ring-primary/20 outline-none"
                            />
                        </div>
                        <div className="space-y-2">
                            <label className="text-sm font-medium text-muted-foreground">Start Date</label>
                            <input
                                type="date"
                                value={settings['start_date'] || ''}
                                onChange={(e) => handleChange('start_date', e.target.value)}
                                className="w-full bg-secondary/30 border border-border/50 rounded-xl px-4 py-3 focus:ring-2 focus:ring-primary/20 outline-none"
                            />
                        </div>
                        <div className="space-y-2">
                            <label className="text-sm font-medium text-muted-foreground">Original Gravity (OG)</label>
                            <input
                                type="number" step="0.001"
                                value={settings['og'] || ''}
                                onChange={(e) => handleChange('og', e.target.value)}
                                className="w-full bg-secondary/30 border border-border/50 rounded-xl px-4 py-3 focus:ring-2 focus:ring-primary/20 outline-none"
                            />
                        </div>
                        <div className="space-y-2">
                            <label className="text-sm font-medium text-muted-foreground">Target FG</label>
                            <input
                                type="number" step="0.001"
                                value={settings['target_fg'] || ''}
                                onChange={(e) => handleChange('target_fg', e.target.value)}
                                className="w-full bg-secondary/30 border border-border/50 rounded-xl px-4 py-3 focus:ring-2 focus:ring-primary/20 outline-none"
                            />
                        </div>
                        <div className="md:col-span-2 space-y-2">
                            <label className="text-sm font-medium text-muted-foreground">Notes</label>
                            <textarea
                                value={settings['batch_notes'] || ''}
                                onChange={(e) => handleChange('batch_notes', e.target.value)}
                                className="w-full bg-secondary/30 border border-border/50 rounded-xl px-4 py-3 min-h-[100px] focus:ring-2 focus:ring-primary/20 outline-none"
                            />
                        </div>
                        <div className="md:col-span-2 pt-2">
                            <a
                                href="/api/label"
                                target="_blank"
                                className="flex items-center justify-center gap-2 w-full bg-amber-600/10 text-amber-500 hover:bg-amber-600/20 border border-amber-500/20 py-3 rounded-xl font-medium transition-colors"
                            >
                                <Hash className="w-4 h-4" /> Download Keg Label
                            </a>
                        </div>
                    </div>
                </section>

                {/* Calibration */}
                <section className="space-y-4">
                    <div className="flex items-center gap-2 text-primary font-semibold">
                        <RefreshCcw className="w-5 h-5" />
                        <h2>Sensor Calibration</h2>
                    </div>
                    <div className="bg-card border border-border/50 p-6 rounded-3xl space-y-6">
                        <div className="flex items-center justify-between p-4 bg-secondary/30 rounded-xl">
                            <span className="text-sm font-medium">Current Offset</span>
                            <code className="bg-background px-3 py-1 rounded-lg border border-border font-mono text-amber-500">
                                {settings['offset'] || '0.000'}
                            </code>
                        </div>
                        <div className="flex gap-4">
                            <input
                                type="number" step="0.001"
                                placeholder="Hydrometer Reading (e.g. 1.050)"
                                value={manualSg}
                                onChange={(e) => setManualSg(e.target.value)}
                                className="flex-1 bg-secondary/30 border border-border/50 rounded-xl px-4 py-3 focus:ring-2 focus:ring-primary/20 outline-none"
                            />
                            <button
                                onClick={handleCalibrate}
                                disabled={calibrating}
                                className="bg-blue-600 hover:bg-blue-500 text-white px-6 rounded-xl font-bold transition-colors disabled:opacity-50"
                            >
                                {calibrating ? '...' : 'Calibrate'}
                            </button>
                        </div>
                        <p className="text-xs text-muted-foreground">
                            Enter a manual hydrometer reading. The system will automatically calculate and save the new offset.
                        </p>
                    </div>
                </section>

                {/* Integrations */}
                <section className="space-y-4">
                    <div className="flex items-center gap-2 text-primary font-semibold">
                        <Scale className="w-5 h-5" />
                        <h2>Integrations</h2>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 bg-card border border-border/50 p-6 rounded-3xl">

                        {/* Brewfather */}
                        <div className="space-y-4 p-4 rounded-2xl bg-secondary/20 border border-border/30">
                            <h3 className="font-semibold text-sm flex items-center gap-2">
                                <span className="w-2 h-2 rounded-full bg-blue-500"></span> Brewfather
                            </h3>
                            <div className="space-y-2">
                                <input
                                    type="text" placeholder="User ID"
                                    value={settings['bf_user'] || ''}
                                    onChange={(e) => handleChange('bf_user', e.target.value)}
                                    className="w-full bg-background border border-border/50 rounded-lg px-3 py-2 text-sm"
                                />
                                <input
                                    type="password" placeholder="API Key"
                                    value={settings['bf_key'] || ''}
                                    onChange={(e) => handleChange('bf_key', e.target.value)}
                                    className="w-full bg-background border border-border/50 rounded-lg px-3 py-2 text-sm"
                                />
                            </div>
                            <button onClick={handleSyncBrewfather} className="w-full text-xs bg-blue-600/10 text-blue-500 py-2 rounded-lg font-bold hover:bg-blue-600/20">
                                Sync Now
                            </button>
                        </div>

                        {/* Telegram */}
                        <div className="space-y-4 p-4 rounded-2xl bg-secondary/20 border border-border/30">
                            <h3 className="font-semibold text-sm flex items-center gap-2">
                                <span className="w-2 h-2 rounded-full bg-sky-500"></span> Telegram
                            </h3>
                            <div className="space-y-2">
                                <input
                                    type="password" placeholder="Bot Token"
                                    value={settings['alert_telegram_token'] || ''}
                                    onChange={(e) => handleChange('alert_telegram_token', e.target.value)}
                                    className="w-full bg-background border border-border/50 rounded-lg px-3 py-2 text-sm"
                                />
                                <input
                                    type="text" placeholder="Chat ID"
                                    value={settings['alert_telegram_chat'] || ''}
                                    onChange={(e) => handleChange('alert_telegram_chat', e.target.value)}
                                    className="w-full bg-background border border-border/50 rounded-lg px-3 py-2 text-sm"
                                />
                            </div>
                        </div>

                        <div className="md:col-span-2 space-y-2">
                            <label className="text-sm font-medium text-muted-foreground">Shopping (SerpApi Key)</label>
                            <input
                                type="password" placeholder="API Key"
                                value={settings['serp_api_key'] || ''}
                                onChange={(e) => handleChange('serp_api_key', e.target.value)}
                                className="w-full bg-secondary/30 border border-border/50 rounded-xl px-4 py-2"
                            />
                        </div>
                    </div>
                </section>

                {/* Automation & Alerts */}
                <section className="space-y-4">
                    <div className="flex items-center gap-2 text-primary font-semibold">
                        <Clock className="w-5 h-5" />
                        <h2>Automation & Alerts</h2>
                    </div>
                    <div className="bg-card border border-border/50 p-6 rounded-3xl space-y-6">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <label className="text-sm font-medium text-muted-foreground">Active Hours Start</label>
                                <input
                                    type="time"
                                    value={settings['alert_start_time'] || '08:00'}
                                    onChange={(e) => handleChange('alert_start_time', e.target.value)}
                                    className="w-full bg-secondary/30 border border-border/50 rounded-xl px-4 py-2"
                                />
                            </div>
                            <div className="space-y-2">
                                <label className="text-sm font-medium text-muted-foreground">Active Hours End</label>
                                <input
                                    type="time"
                                    value={settings['alert_end_time'] || '22:00'}
                                    onChange={(e) => handleChange('alert_end_time', e.target.value)}
                                    className="w-full bg-secondary/30 border border-border/50 rounded-xl px-4 py-2"
                                />
                            </div>
                            <div className="space-y-2">
                                <label className="text-sm font-medium text-muted-foreground">Tilt Timeout (min)</label>
                                <input
                                    type="number"
                                    value={settings['tilt_timeout_min'] || '60'}
                                    onChange={(e) => handleChange('tilt_timeout_min', e.target.value)}
                                    className="w-full bg-secondary/30 border border-border/50 rounded-xl px-4 py-2"
                                />
                            </div>
                            <div className="space-y-2">
                                <label className="text-sm font-medium text-muted-foreground">Max Temp (°C)</label>
                                <input
                                    type="number" step="0.1"
                                    value={settings['temp_max'] || '28.0'}
                                    onChange={(e) => handleChange('temp_max', e.target.value)}
                                    className="w-full bg-secondary/30 border border-border/50 rounded-xl px-4 py-2"
                                />
                            </div>
                            <div className="md:col-span-2 space-y-2">
                                <label className="text-sm font-medium text-muted-foreground">TiltPi / Webhook URL</label>
                                <input
                                    type="text" placeholder="http://tiltpi.local/webhook"
                                    value={settings['tiltpi_url'] || ''}
                                    onChange={(e) => handleChange('tiltpi_url', e.target.value)}
                                    className="w-full bg-secondary/30 border border-border/50 rounded-xl px-4 py-2"
                                />
                            </div>
                        </div>
                    </div>
                </section>

                {/* System / Test Mode */}
                <section className="space-y-4">
                    <div className="flex items-center gap-2 text-primary font-semibold">
                        <AlertTriangle className="w-5 h-5" />
                        <h2>System Control</h2>
                    </div>
                    <div className="bg-card border border-border/50 p-6 rounded-3xl space-y-6">
                        <div className="flex items-center justify-between p-4 bg-secondary/30 rounded-xl">
                            <div>
                                <h3 className="font-bold">Test Mode</h3>
                                <p className="text-xs text-muted-foreground">Simulate sensor data for verification</p>
                            </div>
                            <button
                                onClick={toggleTestMode}
                                className={cn(
                                    "px-4 py-2 rounded-lg font-bold text-sm transition-all",
                                    settings['test_mode'] === 'true'
                                        ? "bg-amber-500 text-black hover:bg-amber-400"
                                        : "bg-secondary text-muted-foreground hover:bg-secondary/80"
                                )}
                            >
                                {settings['test_mode'] === 'true' ? 'Enabled' : 'Disabled'}
                            </button>
                        </div>

                        {settings['test_mode'] === 'true' && (
                            <div className="grid grid-cols-2 gap-4 animate-in fade-in slide-in-from-top-4">
                                <div className="space-y-2">
                                    <label className="text-sm font-medium text-muted-foreground">Sim Start SG</label>
                                    <input
                                        type="number" step="0.001"
                                        value={settings['test_sg_start'] || ''}
                                        onChange={(e) => handleChange('test_sg_start', e.target.value)}
                                        className="w-full bg-secondary/30 border border-border/50 rounded-xl px-4 py-2"
                                    />
                                </div>
                                <div className="space-y-2">
                                    <label className="text-sm font-medium text-muted-foreground">Sim Base Temp</label>
                                    <input
                                        type="number" step="0.1"
                                        value={settings['test_temp_base'] || ''}
                                        onChange={(e) => handleChange('test_temp_base', e.target.value)}
                                        className="w-full bg-secondary/30 border border-border/50 rounded-xl px-4 py-2"
                                    />
                                </div>
                                <button
                                    onClick={(e) => handleSave(e)}
                                    className="col-span-2 w-full bg-slate-800 text-slate-300 py-2 rounded-lg hover:bg-slate-700 font-medium"
                                >
                                    Update Simulation Parameters
                                </button>
                            </div>
                        )}
                    </div>
                </section>

                {/* --- MODALS --- */}
                {activeModal && (
                    <div className="fixed inset-0 z-[100] bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
                        <div className="bg-card w-full max-w-md rounded-2xl border border-border/50 shadow-2xl p-6 space-y-4 animate-in fade-in zoom-in-95">
                            <h3 className="text-xl font-bold">
                                {activeModal === 'manual' ? 'Manual Tap Entry' : 'Snapshot Current Batch'}
                            </h3>

                            {activeModal === 'manual' && (
                                <div className="space-y-4">
                                    <input
                                        placeholder="Batch Name"
                                        value={manualForm.name}
                                        onChange={e => setManualForm({ ...manualForm, name: e.target.value })}
                                        className="w-full bg-secondary/50 rounded-lg px-4 py-2 border border-border/50"
                                    />
                                    <div className="grid grid-cols-2 gap-3">
                                        <input placeholder="Style" value={manualForm.style} onChange={e => setManualForm({ ...manualForm, style: e.target.value })} className="bg-secondary/50 rounded-lg px-4 py-2 border border-border/50" />
                                        <input placeholder="ABV %" type="number" step="0.1" value={manualForm.abv} onChange={e => setManualForm({ ...manualForm, abv: e.target.value })} className="bg-secondary/50 rounded-lg px-4 py-2 border border-border/50" />
                                        <input placeholder="IBU" type="number" value={manualForm.ibu} onChange={e => setManualForm({ ...manualForm, ibu: e.target.value })} className="bg-secondary/50 rounded-lg px-4 py-2 border border-border/50" />
                                        <input placeholder="SRM" type="number" value={manualForm.srm} onChange={e => setManualForm({ ...manualForm, srm: e.target.value })} className="bg-secondary/50 rounded-lg px-4 py-2 border border-border/50" />
                                    </div>
                                    <div className="grid grid-cols-2 gap-3">
                                        <input placeholder="Total Vol" type="number" value={manualForm.keg_total} onChange={e => setManualForm({ ...manualForm, keg_total: e.target.value })} className="bg-secondary/50 rounded-lg px-4 py-2 border border-border/50" />
                                        <select value={manualForm.unit} onChange={e => setManualForm({ ...manualForm, unit: e.target.value })} className="bg-secondary/50 rounded-lg px-4 py-2 border border-border/50">
                                            <option value="L">Litres</option>
                                            <option value="oz">Ounces</option>
                                        </select>
                                    </div>
                                    <div className="flex gap-2">
                                        <button onClick={() => setActiveModal(null)} className="flex-1 py-2 rounded-xl text-muted-foreground hover:bg-secondary">Cancel</button>
                                        <button onClick={submitManualTap} className="flex-1 py-2 rounded-xl bg-primary text-primary-foreground font-bold hover:bg-primary/90">Save Tap</button>
                                    </div>
                                </div>
                            )}

                            {activeModal === 'snapshot' && (
                                <div className="space-y-4">
                                    <p className="text-muted-foreground text-sm">
                                        Assigning a snapshot of the current active batch to this tap.
                                    </p>
                                    <div className="space-y-2">
                                        <label className="text-xs font-bold uppercase text-muted-foreground">Volume Unit</label>
                                        <div className="flex gap-2">
                                            <button
                                                onClick={() => setSnapshotForm({ ...snapshotForm, unit: 'L', keg_total: '19' })}
                                                className={cn("flex-1 py-2 rounded-lg border", snapshotForm.unit === 'L' ? "bg-primary/20 border-primary text-primary" : "border-border hover:bg-secondary")}
                                            >Litres (L)</button>
                                            <button
                                                onClick={() => setSnapshotForm({ ...snapshotForm, unit: 'oz', keg_total: '640' })}
                                                className={cn("flex-1 py-2 rounded-lg border", snapshotForm.unit === 'oz' ? "bg-primary/20 border-primary text-primary" : "border-border hover:bg-secondary")}
                                            >Gallons/Oz</button>
                                        </div>
                                    </div>
                                    <div className="space-y-2">
                                        <label className="text-xs font-bold uppercase text-muted-foreground">Keg Volume</label>
                                        <input
                                            type="number"
                                            value={snapshotForm.keg_total}
                                            onChange={e => setSnapshotForm({ ...snapshotForm, keg_total: e.target.value })}
                                            className="w-full bg-secondary/50 rounded-lg px-4 py-2 border border-border/50"
                                        />
                                    </div>
                                    <div className="flex gap-2 pt-2">
                                        <button onClick={() => setActiveModal(null)} className="flex-1 py-2 rounded-xl text-muted-foreground hover:bg-secondary">Cancel</button>
                                        <button onClick={submitSnapshotTap} className="flex-1 py-2 rounded-xl bg-blue-600 text-white font-bold hover:bg-blue-500">Assign Snapshot</button>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                )}

            </div>
        </main>
    );
}
