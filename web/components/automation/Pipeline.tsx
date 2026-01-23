'use client';

import { useState, useEffect, useRef } from 'react';
import { Network, AlertCircle, CheckCircle, Activity, Upload, RefreshCw, Thermometer } from 'lucide-react';
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

export function Pipeline() {
    const [pipeline, setPipeline] = useState<PipelineResult | null>(null);
    const [loading, setLoading] = useState(false);

    // Diagnostics state
    const [diagOpen, setDiagOpen] = useState(false);
    const [dataSource, setDataSource] = useState<'csv' | 'bf'>('csv');
    const [bfBatches, setBfBatches] = useState<BFBatch[]>([]);
    const [selectedBatch, setSelectedBatch] = useState('');
    const [targetTemp, setTargetTemp] = useState(20.0);
    const [alertResult, setAlertResult] = useState<AlertResult | null>(null);
    const [diagLoading, setDiagLoading] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const scanPipeline = async () => {
        setLoading(true);
        try {
            const res = await fetch('/api/automation/monitoring/scan', { method: 'POST' });
            const data = await res.json();
            setPipeline(data);
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
            if (Array.isArray(data)) {
                setBfBatches(data);
            }
        } catch (e) {
            console.error(e);
        }
    };

    useEffect(() => {
        if (dataSource === 'bf') {
            loadBfBatches();
        }
    }, [dataSource]);

    const runAlertAnalysis = async () => {
        setDiagLoading(true);
        setAlertResult(null);

        try {
            if (dataSource === 'csv') {
                // CSV file upload
                const file = fileInputRef.current?.files?.[0];
                if (!file) {
                    setAlertResult({ status: 'error', message: 'Please select a CSV file', error: 'No file selected' });
                    setDiagLoading(false);
                    return;
                }

                const formData = new FormData();
                formData.append('file', file);
                formData.append('target', targetTemp.toString());

                const res = await fetch('/api/automation/alerts', {
                    method: 'POST',
                    body: formData
                });
                const data = await res.json();
                setAlertResult(data);
            } else {
                // Brewfather batch
                if (!selectedBatch) {
                    setAlertResult({ status: 'error', message: 'Please select a batch', error: 'No batch selected' });
                    setDiagLoading(false);
                    return;
                }

                const res = await fetch('/api/automation/brewfather/analyze', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        batch_id: selectedBatch,
                        target: targetTemp
                    })
                });
                const data = await res.json();
                setAlertResult(data);
            }
        } catch (e: any) {
            setAlertResult({ status: 'error', message: e.message, error: e.message });
        } finally {
            setDiagLoading(false);
        }
    };

    return (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4">
            {/* Pipeline Header */}
            <div className="flex justify-between items-center bg-card/50 p-6 rounded-2xl border border-white/5">
                <div>
                    <h3 className="text-xl font-bold flex items-center gap-2">
                        <Network className="w-6 h-6 text-indigo-400" /> R&D Pipeline
                    </h3>
                    <p className="text-sm text-muted-foreground">Monitor sync status across Unitanks & Tilt Sensors</p>
                </div>
                <button
                    onClick={scanPipeline}
                    disabled={loading}
                    className="px-6 py-2 bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 rounded-xl hover:bg-indigo-500/20 transition-colors disabled:opacity-50 flex items-center gap-2"
                >
                    <RefreshCw className={cn("w-4 h-4", loading && "animate-spin")} />
                    {loading ? 'Scanning...' : 'Scan Active Batches'}
                </button>
            </div>

            {/* Pipeline Results */}
            {!pipeline && !loading && (
                <div className="py-20 text-center text-muted-foreground border-2 border-dashed border-white/5 rounded-3xl">
                    <Network className="w-12 h-12 mx-auto mb-4 opacity-50" />
                    <p>Pipeline idle. Click Scan to check active fermentations.</p>
                </div>
            )}

            {pipeline && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {(pipeline.batches || []).map((batch, i) => (
                        <div key={i} className="p-6 bg-black/30 rounded-2xl border border-white/5 relative overflow-hidden">
                            <div className="absolute top-0 left-0 w-1 h-full bg-indigo-500" />
                            <div className="flex justify-between items-start mb-4">
                                <div>
                                    <h4 className="text-lg font-bold text-white">{batch.name}</h4>
                                    <div className="text-xs text-muted-foreground">
                                        {batch.number && `Batch #${batch.number}`} {batch.brewer && `• ${batch.brewer}`}
                                    </div>
                                </div>
                                <div className={cn(
                                    "px-2 py-1 rounded text-xs font-bold",
                                    batch.status === 'Fermenting' ? "bg-green-500/20 text-green-400" : "bg-gray-500/20 text-gray-400"
                                )}>
                                    {batch.status}
                                </div>
                            </div>

                            <div className="grid grid-cols-2 gap-4 text-sm">
                                <div>
                                    <div className="text-muted-foreground">Gravity</div>
                                    <div className="font-mono font-bold">{batch.gravity || 'N/A'} SG</div>
                                </div>
                                <div>
                                    <div className="text-muted-foreground">Temp</div>
                                    <div className="font-mono font-bold">{batch.temp || 'N/A'}°C</div>
                                </div>
                            </div>

                            {batch.health_check && (
                                <div className="mt-4 pt-4 border-t border-white/5">
                                    <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider mb-2">
                                        <StatusIcon status={batch.health_check.status} />
                                        Health Check
                                    </div>
                                    <p className="text-sm text-muted-foreground">{batch.health_check.message}</p>
                                </div>
                            )}
                        </div>
                    ))}

                    {(!pipeline.batches || pipeline.batches.length === 0) && (
                        <div className="col-span-full py-12 text-center text-muted-foreground">
                            No active batches found in Brewfather.
                        </div>
                    )}
                </div>
            )}

            {/* Manual Diagnostics Panel */}
            <div className="bg-card/50 rounded-2xl border border-white/5 overflow-hidden">
                <button
                    onClick={() => setDiagOpen(!diagOpen)}
                    className="w-full p-4 flex justify-between items-center hover:bg-white/5 transition-colors"
                >
                    <span className="font-bold flex items-center gap-2">
                        <Thermometer className="w-5 h-5 text-amber-400" />
                        Manual Diagnostics
                    </span>
                    <span className={cn("transition-transform", diagOpen && "rotate-180")}>▼</span>
                </button>

                {diagOpen && (
                    <div className="p-6 border-t border-white/5 space-y-4">
                        {/* Data Source Toggle */}
                        <div>
                            <label className="text-sm text-muted-foreground mb-2 block">Data Source</label>
                            <div className="flex gap-2">
                                <button
                                    onClick={() => setDataSource('csv')}
                                    className={cn(
                                        "px-4 py-2 rounded-lg text-sm font-medium transition-colors",
                                        dataSource === 'csv'
                                            ? "bg-primary/20 text-primary border border-primary/30"
                                            : "bg-secondary/20 text-muted-foreground border border-white/5"
                                    )}
                                >
                                    CSV Upload
                                </button>
                                <button
                                    onClick={() => setDataSource('bf')}
                                    className={cn(
                                        "px-4 py-2 rounded-lg text-sm font-medium transition-colors",
                                        dataSource === 'bf'
                                            ? "bg-primary/20 text-primary border border-primary/30"
                                            : "bg-secondary/20 text-muted-foreground border border-white/5"
                                    )}
                                >
                                    Brewfather Batch
                                </button>
                            </div>
                        </div>

                        {/* CSV Input */}
                        {dataSource === 'csv' && (
                            <div>
                                <label className="text-sm text-muted-foreground mb-2 block">Upload Tilt CSV Log</label>
                                <input
                                    ref={fileInputRef}
                                    type="file"
                                    accept=".csv"
                                    className="w-full p-2 bg-secondary/20 rounded-lg border border-white/5"
                                />
                            </div>
                        )}

                        {/* Brewfather Batch Select */}
                        {dataSource === 'bf' && (
                            <div>
                                <label className="text-sm text-muted-foreground mb-2 block">Select Batch</label>
                                <select
                                    value={selectedBatch}
                                    onChange={(e) => setSelectedBatch(e.target.value)}
                                    className="w-full p-3 rounded-xl bg-secondary/30 border border-border/50"
                                >
                                    <option value="">Select a batch...</option>
                                    {bfBatches.map((b) => (
                                        <option key={b._id} value={b._id}>
                                            {b.name} {b.batchNo && `(#${b.batchNo})`}
                                        </option>
                                    ))}
                                </select>
                            </div>
                        )}

                        {/* Target Temperature */}
                        <div>
                            <label className="text-sm text-muted-foreground mb-2 block">Target Temperature (°C)</label>
                            <input
                                type="number"
                                step="0.1"
                                value={targetTemp}
                                onChange={(e) => setTargetTemp(parseFloat(e.target.value))}
                                className="w-full p-3 rounded-xl bg-secondary/30 border border-border/50"
                            />
                        </div>

                        <button
                            onClick={runAlertAnalysis}
                            disabled={diagLoading}
                            className="w-full py-3 bg-amber-500 hover:bg-amber-600 text-black font-bold rounded-xl transition-colors disabled:opacity-50"
                        >
                            {diagLoading ? 'Analyzing...' : 'Analyze Stability'}
                        </button>

                        {/* Alert Results */}
                        {alertResult && (
                            <div className={cn(
                                "p-4 rounded-xl border",
                                alertResult.error
                                    ? "bg-red-500/10 border-red-500/30"
                                    : alertResult.status === 'stable'
                                        ? "bg-green-500/10 border-green-500/30"
                                        : "bg-amber-500/10 border-amber-500/30"
                            )}>
                                <div className="flex items-center gap-2 mb-2">
                                    <StatusIcon status={alertResult.error ? 'error' : alertResult.status} />
                                    <span className="font-bold">{alertResult.status || 'Result'}</span>
                                </div>
                                <p className="text-sm text-muted-foreground">{alertResult.message}</p>
                                {alertResult.avg_temp && (
                                    <div className="mt-2 text-sm">
                                        Avg Temp: <span className="font-mono">{alertResult.avg_temp}°C</span>
                                        {alertResult.temp_range && ` (Range: ${alertResult.temp_range})`}
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}

function StatusIcon({ status }: { status: string }) {
    if (status === 'stable') return <CheckCircle className="w-4 h-4 text-green-500" />;
    if (status === 'warning') return <AlertCircle className="w-4 h-4 text-amber-500" />;
    if (status === 'error') return <AlertCircle className="w-4 h-4 text-red-500" />;
    return <Activity className="w-4 h-4 text-blue-500" />;
}
