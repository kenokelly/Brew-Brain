"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
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
    Scale,
    Bot,
    Sparkles,
    Server,
    Cpu,
    ArrowLeftRight,
    Settings2
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useSettings, useTaps, useStatus } from "@/lib/hooks";
import toast from "react-hot-toast";
import { apiFetch } from "@/lib/api";

export default function SettingsPage() {
    const router = useRouter();
    const { data: initialSettings, mutate } = useSettings();
    const { data: taps, mutate: mutateTaps } = useTaps();
    const { data: status } = useStatus();

    // Form State
    const [settings, setSettings] = useState<Record<string, any>>({});
    const [saving, setSaving] = useState(false);
    const [calibrating, setCalibrating] = useState(false);
    const [manualSg, setManualSg] = useState("");

    // Modal State
    const [activeModal, setActiveModal] = useState<"manual" | "snapshot" | null>(null);
    const [selectedTap, setSelectedTap] = useState<string | null>(null);

    // Manual Form State
    const [manualForm, setManualForm] = useState({
        name: "", style: "", abv: "5.0", srm: "5", ibu: "20",
        keg_total: "19", keg_remaining: "19", unit: "L", untappd_url: ""
    });
    
    // Untappd State
    const [untappdUrl, setUntappdUrl] = useState("");
    const [isFetchingUntappd, setIsFetchingUntappd] = useState(false);

    // Snapshot Form State
    const [snapshotForm, setSnapshotForm] = useState({
        unit: "L",
        keg_total: "19"
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
        const toastId = toast.loading("Saving settings...");
        try {
            await apiFetch("/api/settings", {
                method: "PATCH",
                body: settings
            });
            toast.success("Settings saved successfully", { id: toastId });
            mutate();
        } catch (err: any) {
            toast.error(`Save failed: ${err.message}`, { id: toastId });
        } finally {
            setSaving(false);
        }
    };

    const handleTestIntegration = async (integration: string) => {
        const toastId = toast.loading(`Testing ${integration}...`);
        try {
            const res = await apiFetch<any>("/api/settings/test", {
                method: "POST",
                body: { integration, config: settings }
            });
            if (res.status === "success") {
                toast.success(res.message || "Connection successful!", { id: toastId, duration: 6000 });
            } else {
                toast.error(res.error || res.message || "Connection failed", { id: toastId, duration: 10000 });
            }
        } catch (err: any) {
            toast.error(`Test failed: ${err.message}`, { id: toastId, duration: 10000 });
        }
    };

    // --- Tap Logic ---

    const openManualTap = (tapId: string) => {
        setSelectedTap(tapId);
        const existing = taps?.[tapId];
        if (existing) {
            setManualForm({
                name: existing.name || "",
                style: existing.style || "",
                abv: existing.abv?.toString() || "5.0",
                srm: existing.srm?.toString() || "5",
                ibu: existing.ibu?.toString() || "20",
                keg_total: existing.keg_total?.toString() || existing.keg_volume_l?.toString() || "19",
                keg_remaining: existing.keg_remaining?.toString() || "19",
                unit: existing.volume_unit || "L",
                untappd_url: existing.untappd_url || ""
            });
            setUntappdUrl(existing.untappd_url || "");
        } else {
            setManualForm({
                name: "", style: "", abv: "5.0", srm: "5", ibu: "20",
                keg_total: "19", keg_remaining: "19", unit: "L",
                untappd_url: ""
            });
            setUntappdUrl("");
        }
        setActiveModal("manual");
    };

    const fetchUntappdDetails = async () => {
        if (!untappdUrl) return;
        setIsFetchingUntappd(true);
        const toastId = toast.loading("Scraping Untappd...");
        try {
            const res = await apiFetch<any>("/api/untappd/fetch", {
                method: "POST",
                body: { url: untappdUrl }
            });
            if (res.status === "success" && res.data) {
                setManualForm(prev => ({
                    ...prev,
                    name: res.data.name || prev.name,
                    style: res.data.style || prev.style,
                    abv: res.data.abv?.toString() || prev.abv,
                    ibu: res.data.ibu?.toString() || prev.ibu
                }));
                toast.success("Successfully retrieved Untappd data!", { id: toastId });
            } else {
                toast.error(res.error || "Failed to retrieve data", { id: toastId });
            }
        } catch (err: any) {
            toast.error(`Error: ${err.message}`, { id: toastId });
        } finally {
            setIsFetchingUntappd(false);
        }
    };

    const openSnapshotTap = (tapId: string) => {
        setSelectedTap(tapId);
        setSnapshotForm({ unit: "L", keg_total: "19" });
        setActiveModal("snapshot");
    };

    const submitManualTap = async () => {
        if (!selectedTap) return;
        const toastId = toast.loading("Updating tap...");
        try {
            await apiFetch(`/api/taps/${selectedTap}`, {
                method: "POST",
                body: {
                    action: "manual",
                    name: manualForm.name,
                    style: manualForm.style,
                    abv: manualForm.abv,
                    srm: manualForm.srm,
                    ibu: manualForm.ibu,
                    keg_total: manualForm.keg_total,
                    keg_remaining: manualForm.keg_remaining,
                    volume_unit: manualForm.unit,
                    untappd_url: untappdUrl
                }
            });
            toast.success(`Tap ${selectedTap.replace("tap_", "")} updated`, { id: toastId });
            mutateTaps();
            setActiveModal(null);
        } catch (e: any) { 
            toast.error(`Update failed: ${e.message}`, { id: toastId }); 
        }
    };

    const submitSnapshotTap = async () => {
        if (!selectedTap) return;
        const toastId = toast.loading("Assigning snapshot...");
        try {
            await apiFetch(`/api/taps/${selectedTap}`, {
                method: "POST",
                body: {
                    action: "assign_current",
                    keg_total: snapshotForm.keg_total,
                    keg_remaining: snapshotForm.keg_total,
                    volume_unit: snapshotForm.unit
                }
            });
            toast.success(`Snapshot assigned to ${selectedTap.replace("tap_", "")}`, { id: toastId });
            mutateTaps();
            setActiveModal(null);
        } catch (e: any) { 
            toast.error(`Assignment failed: ${e.message}`, { id: toastId }); 
        }
    };

    const clearTap = async (tapId: string) => {
        if (!confirm("Are you sure you want to clear this tap?")) return;
        const toastId = toast.loading("Clearing tap...");
        try {
            await apiFetch(`/api/taps/${tapId}`, {
                method: "POST",
                body: { action: "clear" }
            });
            toast.success("Tap cleared", { id: toastId });
            mutateTaps();
        } catch (e: any) { 
            toast.error(`Clear failed: ${e.message}`, { id: toastId }); 
        }
    };

    // --- Legacy Actions ---

    const handleCalibrate = async () => {
        const val = parseFloat(manualSg);
        if (!val || val < 0.900 || val > 1.200) {
            toast.error("Invalid gravity reading (0.900 - 1.200)");
            return;
        }
        setCalibrating(true);
        const toastId = toast.loading("Calibrating...");
        try {
            const d = await apiFetch<any>("/api/calibrate", {
                method: "POST",
                body: { sg: val, source: "Manual Entry" }
            });
            if (d.status === "success" || d.status === "synced" || d.new_offset !== undefined) {
                toast.success(`Calibrated! New offset: ${d.new_offset || "Updated"}`, { id: toastId });
                mutate();
                setManualSg("");
            } else {
                toast.error(d.message || d.error || "Calibration failed", { id: toastId });
            }
        } catch (e: any) {
            toast.error(`Calibration request failed: ${e.message}`, { id: toastId });
        } finally {
            setCalibrating(false);
        }
    };

    const handleSyncBrewfather = async () => {
        const toastId = toast.loading("Syncing with Brewfather...");
        try {
            const d = await apiFetch<any>("/api/sync_brewfather", { method: "POST" });
            if (d.status === "synced") {
                toast.success(`Synced batch: ${d.data.name}`, { id: toastId });
                mutate();
            } else {
                toast.error(`Sync error: ${d.error || "Unknown"}`, { id: toastId });
            }
        } catch (e: any) {
            console.error("Brewfather Sync Failed:", e);
            const detail = e.data?.error || e.data?.message || e.message;
            toast.error(`Connection failed: ${detail}`, { id: toastId });
        }
    };

    const toggleTestMode = () => {
        const newVal = settings["test_mode"] === "true" ? "false" : "true";
        handleChange("test_mode", newVal);
        setTimeout(() => handleSave(), 100);
    };

    return (
        <div className="max-w-4xl mx-auto p-4 md:p-8 space-y-8 animate-in fade-in duration-500">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
                <div>
                    <h1 className="text-4xl font-black tracking-tight mb-2">System Configuration</h1>
                    <p className="text-muted-foreground">Manage API keys, thresholds, and environment variables.</p>
                </div>
                <div className="flex gap-2">
                    <button
                        onClick={handleSyncBrewfather}
                        className="flex items-center justify-center gap-2 bg-secondary text-secondary-foreground hover:bg-secondary/80 px-4 py-3 rounded-full font-semibold transition-all shadow-sm"
                    >
                        <RefreshCcw className="w-5 h-5" />
                        <span className="hidden md:inline">Sync BF</span>
                    </button>
                    <button
                        onClick={handleSave}
                        disabled={saving}
                        className="flex items-center justify-center gap-2 bg-primary text-primary-foreground hover:bg-primary/90 px-6 py-3 rounded-full font-semibold transition-all shadow-sm disabled:opacity-50"
                    >
                        {saving ? <RefreshCcw className="w-5 h-5 animate-spin" /> : <Save className="w-5 h-5" />}
                        {saving ? "Saving..." : "Save Changes"}
                    </button>
                </div>
            </div>

            <form className="space-y-6">
                
                {/* --- TAP MANAGEMENT (RESTORED) --- */}
                <div className="glass-card p-6 space-y-4">
                    <div className="flex items-center gap-3 mb-6 border-b border-border/50 pb-4">
                        <div className="p-2 bg-amber-500/10 rounded-xl text-amber-500">
                            <Beer className="w-5 h-5" />
                        </div>
                        <h2 className="text-xl font-bold tracking-tight">Tap Management</h2>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {[1, 2, 3, 4].map(idx => {
                            const tapKey = `tap_${idx}`;
                            const tap = taps?.[tapKey];
                            const isActive = tap?.active;

                            return (
                                <div key={tapKey} className="bg-secondary/30 border border-border/50 rounded-xl p-4 flex flex-col justify-between min-h-[140px] hover:bg-secondary/40 transition-colors">
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
                                            <div className="flex gap-2">
                                                <button
                                                    type="button"
                                                    onClick={() => openManualTap(tapKey)}
                                                    className="w-full text-xs bg-secondary hover:bg-secondary/80 text-foreground py-2 rounded-lg transition-colors flex items-center justify-center gap-2 font-medium"
                                                >
                                                    <Settings2 className="w-4 h-4" /> Edit Tap
                                                </button>
                                                <button
                                                    type="button"
                                                    onClick={() => clearTap(tapKey)}
                                                    className="w-full text-xs bg-red-500/10 hover:bg-red-500/20 text-red-400 py-2 rounded-lg transition-colors flex items-center justify-center gap-2 font-medium"
                                                >
                                                    <Trash2 className="w-4 h-4" /> Clear
                                                </button>
                                            </div>
                                        </>
                                    ) : (
                                        <div className="flex flex-col gap-2 mt-auto">
                                            <button
                                                type="button"
                                                onClick={() => openSnapshotTap(tapKey)}
                                                className="w-full text-xs bg-primary/10 hover:bg-primary/20 text-primary py-2 rounded-lg transition-colors flex items-center justify-center gap-2 font-medium"
                                            >
                                                <RefreshCcw className="w-4 h-4" /> Snapshot Current
                                            </button>
                                            <button
                                                type="button"
                                                onClick={() => openManualTap(tapKey)}
                                                className="w-full text-xs bg-secondary hover:bg-secondary/80 text-foreground py-2 rounded-lg transition-colors flex items-center justify-center gap-2 font-medium"
                                            >
                                                <Plus className="w-4 h-4" /> Manual Entry
                                            </button>
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                </div>

                {/* --- BATCH PROFILE (RESTORED) --- */}
                <div className="glass-card p-6 space-y-4">
                    <div className="flex items-center gap-3 mb-6 border-b border-border/50 pb-4">
                        <div className="p-2 bg-indigo-500/10 rounded-xl text-indigo-500">
                            <Database className="w-5 h-5" />
                        </div>
                        <h2 className="text-xl font-bold tracking-tight">Batch Profile</h2>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="space-y-2">
                            <label className="text-sm font-medium text-muted-foreground uppercase tracking-wider">Batch Name</label>
                            <input
                                type="text"
                                value={settings["batch_name"] || ""}
                                onChange={(e) => handleChange("batch_name", e.target.value)}
                                className="w-full bg-secondary/50 border border-border/50 rounded-xl px-4 py-3 text-foreground focus:ring-2 focus:ring-primary outline-none transition-all"
                            />
                        </div>
                        <div className="space-y-2">
                            <label className="text-sm font-medium text-muted-foreground uppercase tracking-wider">Start Date</label>
                            <input
                                type="date"
                                value={settings["start_date"] || ""}
                                onChange={(e) => handleChange("start_date", e.target.value)}
                                className="w-full bg-secondary/50 border border-border/50 rounded-xl px-4 py-3 text-foreground focus:ring-2 focus:ring-primary outline-none transition-all"
                            />
                        </div>
                        <div className="space-y-2">
                            <label className="text-sm font-medium text-muted-foreground uppercase tracking-wider">Original Gravity (OG)</label>
                            <input
                                type="number" step="0.001"
                                value={settings["og"] || ""}
                                onChange={(e) => handleChange("og", e.target.value)}
                                className="w-full bg-secondary/50 border border-border/50 rounded-xl px-4 py-3 text-foreground focus:ring-2 focus:ring-primary outline-none transition-all"
                            />
                        </div>
                        <div className="space-y-2">
                            <label className="text-sm font-medium text-muted-foreground uppercase tracking-wider">Target FG</label>
                            <input
                                type="number" step="0.001"
                                value={settings["target_fg"] || ""}
                                onChange={(e) => handleChange("target_fg", e.target.value)}
                                className="w-full bg-secondary/50 border border-border/50 rounded-xl px-4 py-3 text-foreground focus:ring-2 focus:ring-primary outline-none transition-all"
                            />
                        </div>
                        <div className="md:col-span-2 space-y-2">
                            <label className="text-sm font-medium text-muted-foreground uppercase tracking-wider">Notes</label>
                            <textarea
                                value={settings["batch_notes"] || ""}
                                onChange={(e) => handleChange("batch_notes", e.target.value)}
                                className="w-full bg-secondary/50 border border-border/50 rounded-xl px-4 py-3 text-foreground min-h-[100px] focus:ring-2 focus:ring-primary outline-none transition-all"
                            />
                        </div>
                        <div className="md:col-span-2 pt-2">
                            <a
                                href="/api/label"
                                target="_blank"
                                className="flex items-center justify-center gap-2 w-full bg-primary/10 text-primary hover:bg-primary/20 py-3 rounded-xl font-semibold transition-colors"
                            >
                                <Hash className="w-5 h-5" /> Download Keg Label
                            </a>
                        </div>
                    </div>
                </div>

                {/* --- CALIBRATION (RESTORED) --- */}
                <div className="glass-card p-6 space-y-4">
                    <div className="flex items-center gap-3 mb-6 border-b border-border/50 pb-4">
                        <div className="p-2 bg-emerald-500/10 rounded-xl text-emerald-500">
                            <RefreshCcw className="w-5 h-5" />
                        </div>
                        <h2 className="text-xl font-bold tracking-tight">Sensor Calibration</h2>
                    </div>
                    <div className="space-y-6">
                        <div className="flex items-center justify-between p-4 bg-secondary/50 rounded-xl border border-border/50">
                            <span className="text-sm font-bold text-muted-foreground uppercase tracking-wider">Current Offset</span>
                            <code className="bg-background px-3 py-1 rounded-lg border border-border font-mono font-bold text-emerald-500">
                                {settings["offset"] || "0.000"}
                            </code>
                        </div>
                        <div className="flex flex-col md:flex-row gap-4">
                            <input
                                type="number" step="0.001"
                                placeholder="Hydrometer Reading (e.g. 1.050)"
                                value={manualSg}
                                onChange={(e) => setManualSg(e.target.value)}
                                className="flex-1 bg-secondary/50 border border-border/50 rounded-xl px-4 py-3 text-foreground focus:ring-2 focus:ring-primary outline-none transition-all"
                            />
                            <button
                                type="button"
                                onClick={handleCalibrate}
                                disabled={calibrating}
                                className="bg-emerald-600 hover:bg-emerald-500 text-white px-8 py-3 rounded-xl font-bold transition-colors disabled:opacity-50 shadow-sm"
                            >
                                {calibrating ? "Calibrating..." : "Calibrate Offset"}
                            </button>
                        </div>
                        <p className="text-sm text-muted-foreground">
                            Enter a manual hydrometer reading. The system will automatically calculate and save the new offset against the raw sensor reading.
                        </p>
                    </div>
                </div>

                {/* --- API INTEGRATIONS (RESTORED & ENHANCED) --- */}
                <div className="glass-card p-6">
                    <div className="flex items-center gap-3 mb-6 border-b border-border/50 pb-4">
                        <div className="p-2 bg-blue-500/10 rounded-xl text-blue-500">
                            <ArrowLeftRight className="w-5 h-5" />
                        </div>
                        <h2 className="text-xl font-bold tracking-tight">API Integrations</h2>
                    </div>
                    
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                        {/* Brewfather */}
                        <div className="md:col-span-2 bg-secondary/20 p-4 rounded-2xl border border-border/50 space-y-4">
                            <div className="flex items-center justify-between">
                                <h3 className="font-bold text-sm flex items-center gap-2">
                                    <span className="w-2 h-2 rounded-full bg-blue-500"></span> Brewfather
                                </h3>
                                <button type="button" onClick={() => handleTestIntegration('brewfather')} className="text-xs bg-blue-500/10 text-blue-500 hover:bg-blue-500/20 px-3 py-1.5 rounded-lg font-bold transition-colors">Test Connection</button>
                            </div>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">User ID</label>
                                    <input 
                                        type="text"
                                        value={settings["bf_user"] || ""} 
                                        onChange={(e) => handleChange("bf_user", e.target.value)} 
                                        className="w-full bg-background border border-border/50 rounded-xl px-4 py-2 text-foreground focus:ring-2 focus:ring-primary outline-none transition-all" 
                                    />
                                </div>
                                <div className="space-y-2">
                                    <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">API Key</label>
                                    <input 
                                        type="password"
                                        value={settings["bf_key"] || ""} 
                                        onChange={(e) => handleChange("bf_key", e.target.value)} 
                                        placeholder="********"
                                        className="w-full bg-background border border-border/50 rounded-xl px-4 py-2 text-foreground focus:ring-2 focus:ring-primary outline-none transition-all" 
                                    />
                                </div>
                            </div>
                        </div>

                        {/* Telegram */}
                        <div className="bg-secondary/20 p-4 rounded-2xl border border-border/50 space-y-4">
                            <div className="flex items-center justify-between">
                                <h3 className="font-bold text-sm flex items-center gap-2">
                                    <span className="w-2 h-2 rounded-full bg-sky-500"></span> Telegram Alerts
                                </h3>
                                <button type="button" onClick={() => handleTestIntegration('telegram')} className="text-xs bg-sky-500/10 text-sky-500 hover:bg-sky-500/20 px-3 py-1.5 rounded-lg font-bold transition-colors">Test Bot</button>
                            </div>
                            <div className="space-y-4">
                                <div className="space-y-2">
                                    <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Bot Token</label>
                                    <input 
                                        type="password"
                                        value={settings["alert_telegram_token"] || ""} 
                                        onChange={(e) => handleChange("alert_telegram_token", e.target.value)} 
                                        placeholder="********"
                                        className="w-full bg-background border border-border/50 rounded-xl px-4 py-2 text-foreground focus:ring-2 focus:ring-primary outline-none transition-all" 
                                    />
                                </div>
                                <div className="space-y-2">
                                    <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Chat ID</label>
                                    <input 
                                        type="text"
                                        value={settings["alert_telegram_chat"] || ""} 
                                        onChange={(e) => handleChange("alert_telegram_chat", e.target.value)} 
                                        className="w-full bg-background border border-border/50 rounded-xl px-4 py-2 text-foreground focus:ring-2 focus:ring-primary outline-none transition-all" 
                                    />
                                </div>
                            </div>
                        </div>

                        {/* SerpApi */}
                        <div className="bg-secondary/20 p-4 rounded-2xl border border-border/50 space-y-4">
                            <div className="flex items-center justify-between">
                                <h3 className="font-bold text-sm flex items-center gap-2">
                                    <span className="w-2 h-2 rounded-full bg-emerald-500"></span> Sourcing Engine
                                </h3>
                                <button type="button" onClick={() => handleTestIntegration('serpapi')} className="text-xs bg-emerald-500/10 text-emerald-500 hover:bg-emerald-500/20 px-3 py-1.5 rounded-lg font-bold transition-colors">Test Key</button>
                            </div>
                            <div className="space-y-2">
                                <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">SerpApi Key</label>
                                <input 
                                    type="password"
                                    value={settings["serp_api_key"] || ""} 
                                    onChange={(e) => handleChange("serp_api_key", e.target.value)} 
                                    placeholder="********"
                                    className="w-full bg-background border border-border/50 rounded-xl px-4 py-2 text-foreground focus:ring-2 focus:ring-primary outline-none transition-all" 
                                />
                            </div>
                        </div>

                        {/* Ollama AI */}
                        <div className="md:col-span-2 bg-secondary/20 p-4 rounded-2xl border border-border/50 space-y-4">
                            <div className="flex items-center justify-between">
                                <h3 className="font-bold text-sm flex items-center gap-2">
                                    <Sparkles className="w-4 h-4 text-purple-500" /> Ollama AI (Local LLM)
                                </h3>
                                <button type="button" onClick={() => handleTestIntegration('ollama')} className="text-xs bg-purple-500/10 text-purple-500 hover:bg-purple-500/20 px-3 py-1.5 rounded-lg font-bold transition-colors">Test Local AI</button>
                            </div>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Ollama Host</label>
                                    <input
                                        type="text" placeholder="localhost or IP"
                                        value={settings["ollama_host"] || "localhost"}
                                        onChange={(e) => handleChange("ollama_host", e.target.value)}
                                        className="w-full bg-background border border-border/50 rounded-xl px-4 py-2 text-foreground focus:ring-2 focus:ring-primary outline-none transition-all"
                                    />
                                </div>
                                <div className="space-y-2">
                                    <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Model Name</label>
                                    <input
                                        type="text" placeholder="llama3"
                                        value={settings["ollama_model"] || "llama3"}
                                        onChange={(e) => handleChange("ollama_model", e.target.value)}
                                        className="w-full bg-background border border-border/50 rounded-xl px-4 py-2 text-foreground focus:ring-2 focus:ring-primary outline-none transition-all"
                                    />
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                {/* --- AUTOMATION & ALERTS (RESTORED) --- */}
                <div className="glass-card p-6 space-y-4">
                    <div className="flex items-center gap-3 mb-6 border-b border-border/50 pb-4">
                        <div className="p-2 bg-rose-500/10 rounded-xl text-rose-500">
                            <Clock className="w-5 h-5" />
                        </div>
                        <h2 className="text-xl font-bold tracking-tight">Automation & Limits</h2>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="space-y-2">
                            <label className="text-sm font-medium text-muted-foreground uppercase tracking-wider">Active Hours Start</label>
                            <input
                                type="time"
                                value={settings["alert_start_time"] || "08:00"}
                                onChange={(e) => handleChange("alert_start_time", e.target.value)}
                                className="w-full bg-secondary/50 border border-border/50 rounded-xl px-4 py-3 text-foreground focus:ring-2 focus:ring-primary outline-none transition-all"
                            />
                        </div>
                        <div className="space-y-2">
                            <label className="text-sm font-medium text-muted-foreground uppercase tracking-wider">Active Hours End</label>
                            <input
                                type="time"
                                value={settings["alert_end_time"] || "22:00"}
                                onChange={(e) => handleChange("alert_end_time", e.target.value)}
                                className="w-full bg-secondary/50 border border-border/50 rounded-xl px-4 py-3 text-foreground focus:ring-2 focus:ring-primary outline-none transition-all"
                            />
                        </div>
                        <div className="space-y-2">
                            <label className="text-sm font-medium text-muted-foreground uppercase tracking-wider">Tilt Timeout (min)</label>
                            <input
                                type="number"
                                value={settings["tilt_timeout_min"] || "60"}
                                onChange={(e) => handleChange("tilt_timeout_min", e.target.value)}
                                className="w-full bg-secondary/50 border border-border/50 rounded-xl px-4 py-3 text-foreground focus:ring-2 focus:ring-primary outline-none transition-all"
                            />
                        </div>
                        <div className="space-y-2">
                            <label className="text-sm font-medium text-muted-foreground uppercase tracking-wider">Max Temp (°C)</label>
                            <input
                                type="number" step="0.1"
                                value={settings["temp_max"] || "28.0"}
                                onChange={(e) => handleChange("temp_max", e.target.value)}
                                className="w-full bg-secondary/50 border border-border/50 rounded-xl px-4 py-3 text-foreground focus:ring-2 focus:ring-primary outline-none transition-all"
                            />
                        </div>
                        <div className="md:col-span-2 space-y-2">
                            <label className="text-sm font-medium text-muted-foreground uppercase tracking-wider">TiltPi / Webhook URL</label>
                            <input
                                type="text" placeholder="http://tiltpi.local/webhook"
                                value={settings["tiltpi_url"] || ""}
                                onChange={(e) => handleChange("tiltpi_url", e.target.value)}
                                className="w-full bg-secondary/50 border border-border/50 rounded-xl px-4 py-3 text-foreground focus:ring-2 focus:ring-primary outline-none transition-all"
                            />
                        </div>
                    </div>

                    <div className="mt-8 mb-4 border-t border-border/50 pt-6">
                        <h3 className="text-sm font-bold tracking-tight mb-4 flex items-center gap-2">
                            <span className="w-2 h-2 rounded-full bg-rose-500"></span> Alert Rate Limiting & Bypass
                        </h3>
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                            <div className="space-y-2">
                                <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Alert Verbosity (min)</label>
                                <input
                                    type="number"
                                    value={settings["alert_verbosity_min"] || "0"}
                                    onChange={(e) => handleChange("alert_verbosity_min", e.target.value)}
                                    className="w-full bg-background border border-border/50 rounded-xl px-4 py-2 text-foreground focus:ring-2 focus:ring-primary outline-none transition-all"
                                />
                            </div>
                            <div className="space-y-2">
                                <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Report Verbosity (min)</label>
                                <input
                                    type="number"
                                    value={settings["report_verbosity_min"] || "0"}
                                    onChange={(e) => handleChange("report_verbosity_min", e.target.value)}
                                    className="w-full bg-background border border-border/50 rounded-xl px-4 py-2 text-foreground focus:ring-2 focus:ring-primary outline-none transition-all"
                                />
                            </div>
                            <div className="space-y-2">
                                <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Bypass Temp Spike (°C)</label>
                                <input
                                    type="number" step="0.1"
                                    value={settings["bypass_temp_threshold"] || "0.5"}
                                    onChange={(e) => handleChange("bypass_temp_threshold", e.target.value)}
                                    className="w-full bg-background border border-border/50 rounded-xl px-4 py-2 text-foreground focus:ring-2 focus:ring-primary outline-none transition-all"
                                />
                            </div>
                            <div className="space-y-2">
                                <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Bypass SG Drop</label>
                                <input
                                    type="number" step="0.001"
                                    value={settings["bypass_sg_threshold"] || "0.005"}
                                    onChange={(e) => handleChange("bypass_sg_threshold", e.target.value)}
                                    className="w-full bg-background border border-border/50 rounded-xl px-4 py-2 text-foreground focus:ring-2 focus:ring-primary outline-none transition-all"
                                />
                            </div>
                        </div>
                    </div>
                </div>

                {/* --- SYSTEM CONTROL (RESTORED) --- */}
                <div className="glass-card p-6 space-y-4 border-amber-500/20">
                    <div className="flex items-center gap-3 mb-6 border-b border-border/50 pb-4">
                        <div className="p-2 bg-amber-500/10 rounded-xl text-amber-500">
                            <AlertTriangle className="w-5 h-5" />
                        </div>
                        <h2 className="text-xl font-bold tracking-tight">System Control</h2>
                    </div>
                    
                    <div className="flex items-center justify-between p-4 bg-secondary/30 rounded-xl border border-border/50">
                        <div>
                            <h3 className="font-bold">Test Mode</h3>
                            <p className="text-sm text-muted-foreground">Simulate sensor data for verification</p>
                        </div>
                        <button
                            type="button"
                            onClick={toggleTestMode}
                            className={cn(
                                "px-6 py-2 rounded-full font-bold text-sm transition-all shadow-sm",
                                settings["test_mode"] === "true"
                                    ? "bg-amber-500 text-amber-950 hover:bg-amber-400"
                                    : "bg-secondary text-muted-foreground hover:bg-secondary/80"
                            )}
                        >
                            {settings["test_mode"] === "true" ? "Enabled" : "Disabled"}
                        </button>
                    </div>

                    {settings["test_mode"] === "true" && (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 animate-in fade-in slide-in-from-top-4 bg-amber-500/5 p-6 rounded-2xl border border-amber-500/20 mt-4">
                            <div className="space-y-2">
                                <label className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">Sim Start SG</label>
                                <input
                                    type="number" step="0.001"
                                    value={settings["test_sg_start"] || ""}
                                    onChange={(e) => handleChange("test_sg_start", e.target.value)}
                                    className="w-full bg-background border border-border/50 rounded-xl px-4 py-3 text-foreground focus:ring-2 focus:ring-primary outline-none transition-all"
                                />
                            </div>
                            <div className="space-y-2">
                                <label className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">Sim Base Temp</label>
                                <input
                                    type="number" step="0.1"
                                    value={settings["test_temp_base"] || ""}
                                    onChange={(e) => handleChange("test_temp_base", e.target.value)}
                                    className="w-full bg-background border border-border/50 rounded-xl px-4 py-3 text-foreground focus:ring-2 focus:ring-primary outline-none transition-all"
                                />
                            </div>
                        </div>
                    )}
                </div>

                {/* --- DANGER ZONE --- */}
                <div className="glass-card p-6 space-y-4 border-red-500/20 bg-red-500/5">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <div className="p-2 bg-red-500/10 rounded-xl text-red-500">
                                <Trash2 className="w-5 h-5" />
                            </div>
                            <h2 className="text-xl font-bold tracking-tight text-red-500">Danger Zone</h2>
                        </div>
                        <button
                            type="button"
                            onClick={() => {
                                if(confirm("Are you sure you want to Factory Reset? This action cannot be undone.")) {
                                    if(prompt("Type YES to confirm wipe") === "YES") {
                                        toast.error("Factory Reset triggered. (Note: Backend flush required for full wipe)");
                                        // A future backend endpoint would be hit here
                                    }
                                }
                            }}
                            className="bg-red-600 hover:bg-red-500 text-white px-6 py-2 rounded-xl font-bold transition-colors shadow-sm text-sm"
                        >
                            Factory Reset
                        </button>
                    </div>
                    <p className="text-sm text-red-400/80">
                        Wiping settings will reset all API integrations, Telegram tokens, hardware limits, and system configurations back to their defaults.
                    </p>
                </div>

            </form>

            {/* --- MODALS (RESTORED) --- */}
            {activeModal && (
                <div className="fixed inset-0 z-[100] bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
                    <div className="bg-card w-full max-w-md rounded-2xl border border-border/50 shadow-2xl p-6 space-y-4 animate-in fade-in zoom-in-95">
                        <h3 className="text-xl font-bold">
                            {activeModal === "manual" ? "Manual Tap Entry" : "Snapshot Current Batch"}
                        </h3>

                        {activeModal === "manual" && (
                            <div className="space-y-4">
                                <div className="space-y-2 bg-secondary/30 p-3 rounded-lg border border-border/50">
                                    <label className="text-xs font-bold uppercase text-muted-foreground tracking-wider">Untappd Quick Fetch</label>
                                    <div className="flex gap-2">
                                        <input
                                            placeholder="https://untappd.com/b/..."
                                            value={untappdUrl}
                                            onChange={e => setUntappdUrl(e.target.value)}
                                            className="flex-1 bg-secondary/50 rounded-lg px-3 py-2 border border-border/50 focus:ring-2 focus:ring-primary outline-none text-sm"
                                        />
                                        <button 
                                            type="button" 
                                            onClick={fetchUntappdDetails}
                                            disabled={isFetchingUntappd || !untappdUrl}
                                            className="bg-primary/20 text-primary px-3 py-2 rounded-lg font-bold hover:bg-primary/30 text-sm disabled:opacity-50"
                                        >
                                            {isFetchingUntappd ? "..." : "Retrieve"}
                                        </button>
                                    </div>
                                </div>
                                
                                <div className="space-y-1">
                                    <label className="text-xs font-bold uppercase text-muted-foreground tracking-wider ml-1">Batch Name</label>
                                    <input
                                        placeholder="Batch Name"
                                        value={manualForm.name}
                                        onChange={e => setManualForm({ ...manualForm, name: e.target.value })}
                                        className="w-full bg-secondary/50 rounded-lg px-4 py-3 border border-border/50 focus:ring-2 focus:ring-primary outline-none"
                                    />
                                </div>
                                <div className="grid grid-cols-2 gap-3">
                                    <div className="space-y-1">
                                        <label className="text-xs font-bold uppercase text-muted-foreground tracking-wider ml-1">Style</label>
                                        <input placeholder="Style" value={manualForm.style} onChange={e => setManualForm({ ...manualForm, style: e.target.value })} className="w-full bg-secondary/50 rounded-lg px-4 py-2 border border-border/50 focus:ring-2 focus:ring-primary outline-none" />
                                    </div>
                                    <div className="space-y-1">
                                        <label className="text-xs font-bold uppercase text-muted-foreground tracking-wider ml-1">ABV %</label>
                                        <input placeholder="ABV %" type="number" step="0.1" value={manualForm.abv} onChange={e => setManualForm({ ...manualForm, abv: e.target.value })} className="w-full bg-secondary/50 rounded-lg px-4 py-2 border border-border/50 focus:ring-2 focus:ring-primary outline-none" />
                                    </div>
                                    <div className="space-y-1">
                                        <label className="text-xs font-bold uppercase text-muted-foreground tracking-wider ml-1">IBU</label>
                                        <input placeholder="IBU" type="number" value={manualForm.ibu} onChange={e => setManualForm({ ...manualForm, ibu: e.target.value })} className="w-full bg-secondary/50 rounded-lg px-4 py-2 border border-border/50 focus:ring-2 focus:ring-primary outline-none" />
                                    </div>
                                    <div className="space-y-1">
                                        <label className="text-xs font-bold uppercase text-muted-foreground tracking-wider ml-1">SRM</label>
                                        <input placeholder="SRM" type="number" value={manualForm.srm} onChange={e => setManualForm({ ...manualForm, srm: e.target.value })} className="w-full bg-secondary/50 rounded-lg px-4 py-2 border border-border/50 focus:ring-2 focus:ring-primary outline-none" />
                                    </div>
                                </div>
                                <div className="grid grid-cols-3 gap-3">
                                    <div className="space-y-1">
                                        <label className="text-xs font-bold uppercase text-muted-foreground tracking-wider ml-1">Total Vol</label>
                                        <input placeholder="Total" type="number" value={manualForm.keg_total} onChange={e => setManualForm({ ...manualForm, keg_total: e.target.value })} className="w-full bg-secondary/50 rounded-lg px-4 py-2 border border-border/50 focus:ring-2 focus:ring-primary outline-none" />
                                    </div>
                                    <div className="space-y-1">
                                        <label className="text-xs font-bold uppercase text-muted-foreground tracking-wider ml-1">Remaining</label>
                                        <input placeholder="Remaining" type="number" value={manualForm.keg_remaining} onChange={e => setManualForm({ ...manualForm, keg_remaining: e.target.value })} className="w-full bg-secondary/50 rounded-lg px-4 py-2 border border-border/50 focus:ring-2 focus:ring-primary outline-none" />
                                    </div>
                                    <div className="space-y-1">
                                        <label className="text-xs font-bold uppercase text-muted-foreground tracking-wider ml-1">Unit</label>
                                        <select value={manualForm.unit} onChange={e => setManualForm({ ...manualForm, unit: e.target.value })} className="w-full bg-secondary/50 rounded-lg px-4 py-2 border border-border/50 focus:ring-2 focus:ring-primary outline-none">
                                            <option value="L">Litres</option>
                                            <option value="oz">Ounces</option>
                                        </select>
                                    </div>
                                </div>
                                <div className="flex gap-2 pt-2">
                                    <button type="button" onClick={() => setActiveModal(null)} className="flex-1 py-3 rounded-xl text-muted-foreground hover:bg-secondary font-semibold">Cancel</button>
                                    <button type="button" onClick={submitManualTap} className="flex-1 py-3 rounded-xl bg-primary text-primary-foreground font-bold hover:bg-primary/90 shadow-sm">Save Tap</button>
                                </div>
                            </div>
                        )}

                        {activeModal === "snapshot" && (
                            <div className="space-y-4">
                                <p className="text-muted-foreground text-sm">
                                    Assigning a snapshot of the current active batch to this tap.
                                </p>
                                <div className="space-y-2">
                                    <label className="text-xs font-bold uppercase text-muted-foreground tracking-wider">Volume Unit</label>
                                    <div className="flex gap-2">
                                        <button
                                            type="button"
                                            onClick={() => setSnapshotForm({ ...snapshotForm, unit: "L", keg_total: "19" })}
                                            className={cn("flex-1 py-2 rounded-lg border font-semibold", snapshotForm.unit === "L" ? "bg-primary text-primary-foreground border-primary" : "border-border hover:bg-secondary/50")}
                                        >Litres (L)</button>
                                        <button
                                            type="button"
                                            onClick={() => setSnapshotForm({ ...snapshotForm, unit: "oz", keg_total: "640" })}
                                            className={cn("flex-1 py-2 rounded-lg border font-semibold", snapshotForm.unit === "oz" ? "bg-primary text-primary-foreground border-primary" : "border-border hover:bg-secondary/50")}
                                        >Ounces (oz)</button>
                                    </div>
                                </div>
                                <div className="space-y-2">
                                    <label className="text-xs font-bold uppercase text-muted-foreground tracking-wider">Keg Volume</label>
                                    <input
                                        type="number"
                                        value={snapshotForm.keg_total}
                                        onChange={e => setSnapshotForm({ ...snapshotForm, keg_total: e.target.value })}
                                        className="w-full bg-secondary/50 rounded-lg px-4 py-3 border border-border/50 focus:ring-2 focus:ring-primary outline-none"
                                    />
                                </div>
                                <div className="flex gap-2 pt-4">
                                    <button type="button" onClick={() => setActiveModal(null)} className="flex-1 py-3 rounded-xl text-muted-foreground hover:bg-secondary font-semibold">Cancel</button>
                                    <button type="button" onClick={submitSnapshotTap} className="flex-1 py-3 rounded-xl bg-blue-600 text-white font-bold hover:bg-blue-500 shadow-sm">Assign Snapshot</button>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            )}

        </div>
    );
}
