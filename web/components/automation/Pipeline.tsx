'use client';

import { useState, useEffect, useRef } from 'react';
import { Network, AlertCircle, CheckCircle, Activity, RefreshCw, Thermometer, CalendarDays, Plus, FlaskConical, Beaker, Trash2, ArrowRight } from 'lucide-react';
import { cn } from '@/lib/utils';

interface Batch {
    name: string;
    number?: string;
    brewer?: string;
    status: string;
    gravity?: number;
    temp?: number;
    health_check?: {
        status: string;
        message: string;
    };
}

interface PipelineResult {
    batches: Batch[];
    error?: string;
}

interface BFBatch {
    _id: string;
    name: string;
    batchNo?: number;
}

interface AlertResult {
    status: string;
    message: string;
    avg_temp?: number;
    temp_range?: string;
    stability_score?: number;
    error?: string;
}

interface Experiment {
    id: string;
    name: string;
    status: string;
    start_date: string;
    end_date: string;
    hypothesis: string;
    results: string;
}

export function Pipeline() {
    const [activeTab, setActiveTab] = useState<'telemetry' | 'experiments'>('telemetry');

    // Telemetry state
    const [pipeline, setPipeline] = useState<PipelineResult | null>(null);
    const [loading, setLoading] = useState(false);
    const [diagOpen, setDiagOpen] = useState(false);
    const [dataSource, setDataSource] = useState<'csv' | 'bf'>('csv');
    const [bfBatches, setBfBatches] = useState<BFBatch[]>([]);
    const [selectedBatch, setSelectedBatch] = useState('');
    const [targetTemp, setTargetTemp] = useState(20.0);
    const [alertResult, setAlertResult] = useState<AlertResult | null>(null);
    const [diagLoading, setDiagLoading] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);

    // Experiments state
    const [experiments, setExperiments] = useState<Experiment[]>([]);
    const [expLoading, setExpLoading] = useState(false);
    const [showNewExp, setShowNewExp] = useState(false);
    const [newExp, setNewExp] = useState({ name: '', start_date: '', end_date: '', hypothesis: '', status: 'planned' });

    useEffect(() => {
        if (activeTab === 'telemetry' && dataSource === 'bf') {
            loadBfBatches();
        }
        if (activeTab === 'experiments') {
            loadExperiments();
        }
    }, [activeTab, dataSource]);

    // ==========================================
    // TELEMETRY FUNCTIONS
    // ==========================================
    const scanPipeline = async () => {
        setLoading(true);
        try {
            const res = await fetch('/api/automation/monitoring/scan', { method: 'POST' });
            const data = await res.json();
            setPipeline(data.data || data); // handle standard wrapper
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    const loadBfBatches = async () => {
        try {
            const res = await fetch('/api/automation/brewfather/batches');
            const data = await res.json();
            if (Array.isArray(data)) setBfBatches(data);
        } catch (e) {
            console.error(e);
        }
    };

    const runAlertAnalysis = async () => {
        setDiagLoading(true);
        setAlertResult(null);

        try {
            if (dataSource === 'csv') {
                const file = fileInputRef.current?.files?.[0];
                if (!file) {
                    setAlertResult({ status: 'error', message: 'Please select a CSV file', error: 'No file selected' });
                    setDiagLoading(false);
                    return;
                }
                const formData = new FormData();
                formData.append('file', file);
                formData.append('target', targetTemp.toString());

                const res = await fetch('/api/automation/alerts', { method: 'POST', body: formData });
                const data = await res.json();
                setAlertResult(data.data || data);
            } else {
                if (!selectedBatch) {
                    setAlertResult({ status: 'error', message: 'Please select a batch', error: 'No batch selected' });
                    setDiagLoading(false);
                    return;
                }
                const res = await fetch('/api/automation/brewfather/analyze', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ batch_id: selectedBatch, target: targetTemp })
                });
                const data = await res.json();
                setAlertResult(data.data || data);
            }
        } catch (e: any) {
            setAlertResult({ status: 'error', message: e.message, error: e.message });
        } finally {
            setDiagLoading(false);
        }
    };

    // ==========================================
    // EXPERIMENT FUNCTIONS
    // ==========================================
    const loadExperiments = async () => {
        setExpLoading(true);
        try {
            const res = await fetch('/api/automation/experiments');
            const data = await res.json();
            setExperiments(data.data?.experiments || []);
        } catch (e) {
            console.error(e);
        } finally {
            setExpLoading(false);
        }
    };

    const saveExperiment = async () => {
        if (!newExp.name || !newExp.start_date || !newExp.end_date) return;
        try {
            await fetch('/api/automation/experiments', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(newExp)
            });
            setShowNewExp(false);
            setNewExp({ name: '', start_date: '', end_date: '', hypothesis: '', status: 'planned' });
            loadExperiments();
        } catch (e) {
            console.error(e);
        }
    };

    const deleteExperiment = async (id: string) => {
        try {
            await fetch(`/api/automation/experiments/${id}`, { method: 'DELETE' });
            loadExperiments();
        } catch (e) {
            console.error(e);
        }
    };

    // Calculate Gantt positioning based on min/max dates
    const calculateGantt = () => {
        if (!experiments.length) return { minDate: new Date(), maxDate: new Date(), items: [] };
        
        let minTime = Infinity;
        let maxTime = -Infinity;
        
        experiments.forEach(exp => {
            const s = new Date(exp.start_date).getTime();
            const e = new Date(exp.end_date).getTime();
            if (s < minTime) minTime = s;
            if (e > maxTime) maxTime = e;
        });

        // Add 5% padding to the timeline ends
        const padding = (maxTime - minTime) * 0.05 || 86400000;
        minTime -= padding;
        maxTime += padding;
        const duration = maxTime - minTime;

        const items = experiments.map(exp => {
            const s = new Date(exp.start_date).getTime();
            const e = new Date(exp.end_date).getTime();
            const left = ((s - minTime) / duration) * 100;
            const width = Math.max(((e - s) / duration) * 100, 1); // min 1% width
            return { ...exp, left, width };
        });

        return {
            minDate: new Date(minTime),
            maxDate: new Date(maxTime),
            items
        };
    };

    const gantt = calculateGantt();

    return (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4">
            
            {/* Header Tabs */}
            <div className="flex justify-between items-center bg-card/50 p-6 rounded-2xl border border-white/5 backdrop-blur-xl">
                <div>
                    <h3 className="text-2xl font-bold flex items-center gap-3">
                        <Network className="w-8 h-8 text-indigo-400" /> R&D Pipeline
                    </h3>
                    <p className="text-sm text-muted-foreground mt-1">
                        Production telemetry and experimental tracking.
                    </p>
                </div>
                <div className="flex bg-black/40 p-1 rounded-xl border border-white/10">
                    <button
                        onClick={() => setActiveTab('telemetry')}
                        className={cn(
                            "px-5 py-2 rounded-lg text-sm font-bold transition-all",
                            activeTab === 'telemetry' ? "bg-indigo-500 text-white shadow-lg shadow-indigo-500/20" : "text-muted-foreground hover:text-white"
                        )}
                    >
                        Live Telemetry
                    </button>
                    <button
                        onClick={() => setActiveTab('experiments')}
                        className={cn(
                            "px-5 py-2 rounded-lg text-sm font-bold transition-all flex items-center gap-2",
                            activeTab === 'experiments' ? "bg-emerald-500 text-white shadow-lg shadow-emerald-500/20" : "text-muted-foreground hover:text-white"
                        )}
                    >
                        <CalendarDays className="w-4 h-4" /> Tracker
                    </button>
                </div>
            </div>

            {/* ===================================== */}
            {/* TAB 1: TELEMETRY */}
            {/* ===================================== */}
            {activeTab === 'telemetry' && (
                <div className="space-y-6 animate-in fade-in slide-in-from-right-4">
                    <div className="flex justify-end">
                        <button
                            onClick={scanPipeline}
                            disabled={loading}
                            className="px-6 py-2 bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 rounded-xl hover:bg-indigo-500/20 transition-all hover:scale-105 active:scale-95 disabled:opacity-50 disabled:pointer-events-none flex items-center gap-2"
                        >
                            <RefreshCw className={cn("w-4 h-4", loading && "animate-spin")} />
                            {loading ? 'Scanning...' : 'Scan Active Batches'}
                        </button>
                    </div>

                    {/* Pipeline Results */}
                    {!pipeline && !loading && (
                        <div className="py-20 text-center text-muted-foreground border-2 border-dashed border-white/5 rounded-3xl bg-black/20">
                            <Activity className="w-12 h-12 mx-auto mb-4 opacity-30" />
                            <p>Telemetry idle. Click Scan to poll Brewfather and internal DB.</p>
                        </div>
                    )}

                    {pipeline && (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            {(pipeline.batches || []).map((batch, i) => (
                                <div key={i} className="p-6 bg-gradient-to-br from-black/60 to-black/30 rounded-2xl border border-white/5 relative overflow-hidden backdrop-blur-md group hover:border-indigo-500/30 transition-all">
                                    <div className="absolute top-0 left-0 w-1 h-full bg-indigo-500 group-hover:bg-indigo-400 transition-colors" />
                                    <div className="flex justify-between items-start mb-4">
                                        <div>
                                            <h4 className="text-lg font-bold text-white flex items-center gap-2">
                                                {batch.name}
                                            </h4>
                                            <div className="text-xs text-muted-foreground mt-1">
                                                {batch.number && <span className="mr-2">#{batch.number}</span>} 
                                                {batch.brewer && <span>• {batch.brewer}</span>}
                                            </div>
                                        </div>
                                        <div className={cn(
                                            "px-3 py-1 rounded-full text-xs font-bold border",
                                            batch.status === 'Fermenting' ? "bg-green-500/10 text-green-400 border-green-500/20 shadow-[0_0_15px_rgba(34,197,94,0.1)]" : "bg-gray-500/10 text-gray-400 border-gray-500/20"
                                        )}>
                                            {batch.status}
                                        </div>
                                    </div>

                                    <div className="grid grid-cols-2 gap-4 text-sm mt-6">
                                        <div className="bg-white/5 p-3 rounded-xl border border-white/5">
                                            <div className="text-muted-foreground text-xs uppercase tracking-wider mb-1">Gravity</div>
                                            <div className="font-mono text-xl text-white">{batch.gravity || 'N/A'} SG</div>
                                        </div>
                                        <div className="bg-white/5 p-3 rounded-xl border border-white/5">
                                            <div className="text-muted-foreground text-xs uppercase tracking-wider mb-1">Temp</div>
                                            <div className="font-mono text-xl text-white">{batch.temp || 'N/A'}°C</div>
                                        </div>
                                    </div>

                                    {batch.health_check && (
                                        <div className="mt-6 pt-4 border-t border-white/5">
                                            <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider mb-2 text-white">
                                                <StatusIcon status={batch.health_check.status} />
                                                Diagnostic Profile
                                            </div>
                                            <p className="text-sm text-muted-foreground">{batch.health_check.message}</p>
                                        </div>
                                    )}
                                </div>
                            ))}

                            {(!pipeline.batches || pipeline.batches.length === 0) && (
                                <div className="col-span-full py-12 text-center text-muted-foreground bg-black/20 rounded-2xl border border-white/5">
                                    No active batches found in sync target.
                                </div>
                            )}
                        </div>
                    )}

                    {/* Manual Diagnostics Panel */}
                    <div className="bg-gradient-to-br from-card/80 to-card/30 rounded-2xl border border-white/10 overflow-hidden backdrop-blur-xl">
                        <button
                            onClick={() => setDiagOpen(!diagOpen)}
                            className="w-full p-5 flex justify-between items-center hover:bg-white/5 transition-colors"
                        >
                            <span className="font-bold flex items-center gap-3 text-lg">
                                <Thermometer className="w-6 h-6 text-amber-400" />
                                Deep-Dive Diagnostics
                            </span>
                            <span className={cn("transition-transform", diagOpen && "rotate-180")}>▼</span>
                        </button>

                        {diagOpen && (
                            <div className="p-6 border-t border-white/5 space-y-6 animate-in slide-in-from-top-2 fade-in">
                                <div>
                                    <label className="text-sm text-muted-foreground mb-3 block">Analysis Vector</label>
                                    <div className="flex gap-3">
                                        <button
                                            onClick={() => setDataSource('csv')}
                                            className={cn(
                                                "px-5 py-2.5 rounded-xl text-sm font-bold transition-all flex items-center gap-2",
                                                dataSource === 'csv'
                                                    ? "bg-amber-500/20 text-amber-400 border border-amber-500/40 shadow-[0_0_20px_rgba(245,158,11,0.15)]"
                                                    : "bg-black/40 text-muted-foreground border border-white/10 hover:border-white/20"
                                            )}
                                        >
                                            Tilt CSV Log
                                        </button>
                                        <button
                                            onClick={() => setDataSource('bf')}
                                            className={cn(
                                                "px-5 py-2.5 rounded-xl text-sm font-bold transition-all flex items-center gap-2",
                                                dataSource === 'bf'
                                                    ? "bg-amber-500/20 text-amber-400 border border-amber-500/40 shadow-[0_0_20px_rgba(245,158,11,0.15)]"
                                                    : "bg-black/40 text-muted-foreground border border-white/10 hover:border-white/20"
                                            )}
                                        >
                                            Brewfather Source
                                        </button>
                                    </div>
                                </div>

                                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                    {dataSource === 'csv' && (
                                        <div>
                                            <label className="text-sm text-muted-foreground mb-2 block">Data Payload</label>
                                            <input
                                                ref={fileInputRef}
                                                type="file"
                                                accept=".csv"
                                                className="w-full p-3 bg-black/40 rounded-xl border border-white/10 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-bold file:bg-amber-500/10 file:text-amber-400 hover:file:bg-amber-500/20 transition-all cursor-pointer"
                                            />
                                        </div>
                                    )}

                                    {dataSource === 'bf' && (
                                        <div>
                                            <label className="text-sm text-muted-foreground mb-2 block">Target Object</label>
                                            <select
                                                value={selectedBatch}
                                                onChange={(e) => setSelectedBatch(e.target.value)}
                                                className="w-full p-4 rounded-xl bg-black/40 border border-white/10 text-white focus:border-amber-500/50 outline-none transition-all"
                                            >
                                                <option value="">Select a batch ID...</option>
                                                {bfBatches.map((b) => (
                                                    <option key={b._id} value={b._id}>
                                                        {b.name} {b.batchNo && `(#${b.batchNo})`}
                                                    </option>
                                                ))}
                                            </select>
                                        </div>
                                    )}

                                    <div>
                                        <label className="text-sm text-muted-foreground mb-2 block">Control Temperature (°C)</label>
                                        <input
                                            type="number"
                                            step="0.1"
                                            value={targetTemp}
                                            onChange={(e) => setTargetTemp(parseFloat(e.target.value))}
                                            className="w-full p-4 rounded-xl bg-black/40 border border-white/10 text-white font-mono focus:border-amber-500/50 outline-none transition-all"
                                        />
                                    </div>
                                </div>

                                <button
                                    onClick={runAlertAnalysis}
                                    disabled={diagLoading}
                                    className="w-full py-4 bg-gradient-to-r from-amber-600 to-orange-500 hover:from-amber-500 hover:to-orange-400 text-white font-bold rounded-xl transition-all shadow-lg hover:shadow-amber-500/25 disabled:opacity-50 disabled:pointer-events-none flex items-center justify-center gap-2"
                                >
                                    {diagLoading ? <RefreshCw className="w-5 h-5 animate-spin" /> : <Thermometer className="w-5 h-5" />}
                                    {diagLoading ? 'Computing Vectors...' : 'Execute Stability Analysis'}
                                </button>

                                {alertResult && (
                                    <div className={cn(
                                        "p-6 rounded-xl border mt-4 animate-in zoom-in-95 fade-in",
                                        alertResult.error
                                            ? "bg-red-500/10 border-red-500/30 text-red-200"
                                            : alertResult.status === 'stable'
                                                ? "bg-green-500/10 border-green-500/30 text-green-200"
                                                : "bg-amber-500/10 border-amber-500/30 text-amber-200"
                                    )}>
                                        <div className="flex items-center gap-2 mb-3 text-lg">
                                            <StatusIcon status={alertResult.error ? 'error' : alertResult.status} />
                                            <span className="font-bold">{alertResult.error ? 'Analysis Failed' : 'Analysis Complete'}</span>
                                        </div>
                                        <p className="text-white/80 leading-relaxed">{alertResult.message}</p>
                                        {alertResult.avg_temp && (
                                            <div className="mt-4 pt-4 border-t border-white/10 flex gap-6 text-sm">
                                                <div>
                                                    <span className="text-white/40 block mb-1 uppercase tracking-wider text-[10px]">Avg Temp</span>
                                                    <span className="font-mono text-white">{alertResult.avg_temp}°C</span>
                                                </div>
                                                {alertResult.temp_range && (
                                                    <div>
                                                        <span className="text-white/40 block mb-1 uppercase tracking-wider text-[10px]">Range</span>
                                                        <span className="font-mono text-white">{alertResult.temp_range}</span>
                                                    </div>
                                                )}
                                                {alertResult.stability_score !== undefined && (
                                                    <div>
                                                        <span className="text-white/40 block mb-1 uppercase tracking-wider text-[10px]">Dev Score</span>
                                                        <span className="font-mono text-white text-emerald-400">±{alertResult.stability_score.toFixed(2)}</span>
                                                    </div>
                                                )}
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* ===================================== */}
            {/* TAB 2: EXPERIMENT TRACKER */}
            {/* ===================================== */}
            {activeTab === 'experiments' && (
                <div className="space-y-6 animate-in fade-in slide-in-from-left-4">
                    
                    <div className="flex justify-between items-center">
                        <h4 className="text-xl font-bold flex items-center gap-2 text-white">
                            <FlaskConical className="w-5 h-5 text-emerald-400" /> Research Timeline
                        </h4>
                        <button
                            onClick={() => setShowNewExp(!showNewExp)}
                            className="px-4 py-2 bg-emerald-500 hover:bg-emerald-400 text-black font-bold rounded-xl transition-all shadow-[0_0_15px_rgba(16,185,129,0.3)] hover:shadow-[0_0_25px_rgba(16,185,129,0.5)] flex items-center gap-2 hover:scale-105 active:scale-95"
                        >
                            <Plus className="w-4 h-4" /> New Experiment
                        </button>
                    </div>

                    {/* New Experiment Form */}
                    {showNewExp && (
                        <div className="bg-card/80 p-6 rounded-2xl border border-emerald-500/30 shadow-[0_0_30px_rgba(16,185,129,0.1)] backdrop-blur-xl animate-in zoom-in-95 fade-in">
                            <h5 className="font-bold mb-4 text-lg">Define R&D Vector</h5>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                                <div>
                                    <label className="text-xs text-muted-foreground mb-1 block uppercase tracking-wider">Experiment Name</label>
                                    <input
                                        type="text"
                                        value={newExp.name}
                                        onChange={e => setNewExp({...newExp, name: e.target.value})}
                                        className="w-full p-3 rounded-xl bg-black/40 border border-white/10 text-white focus:border-emerald-500/50 outline-none"
                                        placeholder="e.g. Voss Kveik Pressure Test"
                                    />
                                </div>
                                <div className="grid grid-cols-2 gap-2">
                                    <div>
                                        <label className="text-xs text-muted-foreground mb-1 block uppercase tracking-wider">Start Date</label>
                                        <input
                                            type="date"
                                            value={newExp.start_date}
                                            onChange={e => setNewExp({...newExp, start_date: e.target.value})}
                                            className="w-full p-3 rounded-xl bg-black/40 border border-white/10 text-white focus:border-emerald-500/50 outline-none [color-scheme:dark]"
                                        />
                                    </div>
                                    <div>
                                        <label className="text-xs text-muted-foreground mb-1 block uppercase tracking-wider">End Date</label>
                                        <input
                                            type="date"
                                            value={newExp.end_date}
                                            onChange={e => setNewExp({...newExp, end_date: e.target.value})}
                                            className="w-full p-3 rounded-xl bg-black/40 border border-white/10 text-white focus:border-emerald-500/50 outline-none [color-scheme:dark]"
                                        />
                                    </div>
                                </div>
                                <div className="col-span-full">
                                    <label className="text-xs text-muted-foreground mb-1 block uppercase tracking-wider">Hypothesis</label>
                                    <textarea
                                        value={newExp.hypothesis}
                                        onChange={e => setNewExp({...newExp, hypothesis: e.target.value})}
                                        className="w-full p-3 rounded-xl bg-black/40 border border-white/10 text-white focus:border-emerald-500/50 outline-none min-h-[80px]"
                                        placeholder="Fermenting at 1.5 bar will suppress ester formation by 40%..."
                                    />
                                </div>
                            </div>
                            <div className="flex justify-end gap-3">
                                <button onClick={() => setShowNewExp(false)} className="px-4 py-2 text-muted-foreground hover:text-white transition-colors">Cancel</button>
                                <button onClick={saveExperiment} className="px-6 py-2 bg-emerald-500 text-black font-bold rounded-xl hover:bg-emerald-400 transition-colors">Launch</button>
                            </div>
                        </div>
                    )}

                    {/* GANTT CHART */}
                    <div className="bg-black/30 border border-white/5 p-6 rounded-3xl overflow-x-auto relative min-h-[300px]">
                        {expLoading && (
                            <div className="absolute inset-0 flex items-center justify-center bg-black/50 backdrop-blur-sm z-10 rounded-3xl">
                                <RefreshCw className="w-8 h-8 text-emerald-500 animate-spin" />
                            </div>
                        )}
                        
                        {!expLoading && experiments.length === 0 ? (
                            <div className="h-full flex flex-col items-center justify-center text-muted-foreground opacity-50 py-12">
                                <Beaker className="w-16 h-16 mb-4" />
                                <p>No R&D experiments charted.</p>
                            </div>
                        ) : (
                            <div className="min-w-[800px]">
                                {/* Timeline Axis */}
                                <div className="flex justify-between text-xs text-white/30 font-mono mb-4 px-2 border-b border-white/5 pb-2">
                                    <span>{gantt.minDate.toISOString().split('T')[0]}</span>
                                    <span>Timeline Axis</span>
                                    <span>{gantt.maxDate.toISOString().split('T')[0]}</span>
                                </div>

                                {/* Bars */}
                                <div className="space-y-4">
                                    {gantt.items.map(exp => (
                                        <div key={exp.id} className="relative h-14 group">
                                            {/* Bar container */}
                                            <div className="absolute w-full h-full border-b border-white/5" />
                                            
                                            {/* The Bar */}
                                            <div 
                                                className={cn(
                                                    "absolute top-1 bottom-1 rounded-lg backdrop-blur-md border shadow-lg flex items-center px-4 overflow-hidden transition-all duration-500",
                                                    exp.status === 'active' ? 'bg-emerald-500/20 border-emerald-500/50 shadow-emerald-500/10' : 
                                                    exp.status === 'completed' ? 'bg-indigo-500/20 border-indigo-500/50 shadow-indigo-500/10' :
                                                    'bg-white/10 border-white/20 text-white/70'
                                                )}
                                                style={{ left: `${exp.left}%`, width: `${exp.width}%` }}
                                            >
                                                <div className="truncate font-bold text-sm w-full flex justify-between items-center z-10">
                                                    <span className={cn(
                                                        exp.status === 'active' ? 'text-emerald-400' :
                                                        exp.status === 'completed' ? 'text-indigo-400' : 'text-white/80'
                                                    )}>{exp.name}</span>
                                                    
                                                    {/* Delete button (shows on hover) */}
                                                    <button 
                                                        onClick={() => deleteExperiment(exp.id)}
                                                        className="opacity-0 group-hover:opacity-100 transition-opacity text-white/50 hover:text-red-400 p-1"
                                                    >
                                                        <Trash2 className="w-4 h-4" />
                                                    </button>
                                                </div>
                                                
                                                {/* Progress animation for active items */}
                                                {exp.status === 'active' && (
                                                    <div className="absolute top-0 left-0 h-full w-[20%] bg-gradient-to-r from-transparent via-emerald-400/20 to-transparent -translate-x-full animate-[shimmer_2s_infinite]" />
                                                )}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                    
                    {/* Experiment Details Grid */}
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                        {experiments.map(exp => (
                            <div key={`detail-${exp.id}`} className="p-5 bg-card/40 rounded-2xl border border-white/5 hover:border-emerald-500/20 transition-colors">
                                <div className="flex justify-between items-start mb-3">
                                    <h5 className="font-bold text-white">{exp.name}</h5>
                                    <span className={cn(
                                        "text-[10px] uppercase tracking-wider px-2 py-1 rounded font-bold",
                                        exp.status === 'active' ? 'bg-emerald-500/20 text-emerald-400' :
                                        exp.status === 'completed' ? 'bg-indigo-500/20 text-indigo-400' :
                                        'bg-white/10 text-white/60'
                                    )}>{exp.status}</span>
                                </div>
                                <div className="flex items-center gap-2 text-xs font-mono text-muted-foreground mb-4">
                                    <span>{exp.start_date}</span>
                                    <ArrowRight className="w-3 h-3" />
                                    <span>{exp.end_date}</span>
                                </div>
                                <div className="text-sm text-white/80 line-clamp-3">
                                    <span className="text-emerald-500 font-bold mr-2">Hypothesis:</span>
                                    {exp.hypothesis || "No hypothesis recorded."}
                                </div>
                            </div>
                        ))}
                    </div>

                </div>
            )}
        </div>
    );
}

function StatusIcon({ status }: { status: string }) {
    if (status === 'stable') return <CheckCircle className="w-4 h-4 text-emerald-500" />;
    if (status === 'warning') return <AlertCircle className="w-4 h-4 text-amber-500" />;
    if (status === 'error') return <AlertCircle className="w-4 h-4 text-red-500" />;
    return <Activity className="w-4 h-4 text-blue-500" />;
}

