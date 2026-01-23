'use client';

import { useState } from 'react';
import { FlaskConical, Play, Plus, Trash2, AlertTriangle, AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

interface Grain {
    id: number;
    weight_kg: number;
    potential: number;
}

interface SimResult {
    predicted_og: number;
    predicted_fg?: number;
    predicted_abv?: number;
    expected_fg?: string;
    yeast_found?: boolean;
    attenuation_used?: number;
    hardware_error?: string;
    hardware_warning?: string;
    error?: string;
}

export function Simulation() {
    const [config, setConfig] = useState({
        efficiency: 75,
        volume: 23,
        yeast: ''
    });
    const [grains, setGrains] = useState<Grain[]>([
        { id: 1, weight_kg: 5.0, potential: 1.037 }
    ]);
    const [result, setResult] = useState<SimResult | null>(null);
    const [loading, setLoading] = useState(false);

    const addGrain = () => {
        const newId = Math.max(0, ...grains.map(g => g.id)) + 1;
        setGrains([...grains, { id: newId, weight_kg: 0.5, potential: 1.035 }]);
    };

    const removeGrain = (id: number) => {
        if (grains.length > 1) {
            setGrains(grains.filter(g => g.id !== id));
        }
    };

    const updateGrain = (id: number, field: 'weight_kg' | 'potential', value: number) => {
        setGrains(grains.map(g => g.id === id ? { ...g, [field]: value } : g));
    };

    const runSim = async () => {
        setLoading(true);
        setResult(null);
        try {
            const res = await fetch('/api/automation/learning/simulate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    efficiency: config.efficiency,
                    volume: config.volume,
                    yeast: config.yeast || undefined,
                    grains: grains.map(g => ({ weight_kg: g.weight_kg, potential: g.potential }))
                })
            });
            const data = await res.json();
            setResult(data);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    const totalGrain = grains.reduce((sum, g) => sum + g.weight_kg, 0);

    return (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4">
            <div className="bg-card/50 p-6 rounded-2xl border border-white/5">
                <h3 className="text-xl font-bold mb-4 flex items-center gap-2">
                    <FlaskConical className="w-5 h-5 text-purple-400" /> Brew Day Simulator (AI)
                </h3>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                    <div>
                        <label className="text-xs uppercase text-muted-foreground block mb-1">Efficiency %</label>
                        <input
                            type="number"
                            value={config.efficiency}
                            onChange={(e) => setConfig({ ...config, efficiency: parseFloat(e.target.value) })}
                            className="w-full p-2 bg-secondary/20 rounded-lg border border-white/5"
                        />
                    </div>
                    <div>
                        <label className="text-xs uppercase text-muted-foreground block mb-1">Volume (L)</label>
                        <input
                            type="number"
                            value={config.volume}
                            onChange={(e) => setConfig({ ...config, volume: parseFloat(e.target.value) })}
                            className="w-full p-2 bg-secondary/20 rounded-lg border border-white/5"
                        />
                    </div>
                    <div>
                        <label className="text-xs uppercase text-muted-foreground block mb-1">Yeast (for FG Prediction)</label>
                        <input
                            type="text"
                            value={config.yeast}
                            onChange={(e) => setConfig({ ...config, yeast: e.target.value })}
                            placeholder="e.g. US-05"
                            className="w-full p-2 bg-secondary/20 rounded-lg border border-white/5"
                        />
                    </div>
                </div>

                {/* Grain Bill Section */}
                <div className="border-t border-white/10 pt-4">
                    <div className="flex justify-between items-center mb-3">
                        <h4 className="text-sm font-bold text-muted-foreground uppercase tracking-wider">Grain Bill</h4>
                        <span className="text-sm text-muted-foreground">
                            Total: <span className={cn("font-bold", totalGrain > 13 ? "text-red-400" : "text-primary")}>{totalGrain.toFixed(1)} kg</span>
                        </span>
                    </div>

                    <div className="space-y-3">
                        {grains.map((grain, index) => (
                            <div key={grain.id} className="flex gap-3 items-end p-3 bg-black/20 rounded-xl border-l-2 border-purple-500/50">
                                <div className="flex-1">
                                    <label className="text-xs text-muted-foreground block mb-1">Weight (kg)</label>
                                    <input
                                        type="number"
                                        step="0.1"
                                        value={grain.weight_kg}
                                        onChange={(e) => updateGrain(grain.id, 'weight_kg', parseFloat(e.target.value) || 0)}
                                        className="w-full p-2 bg-secondary/20 rounded-lg border border-white/5"
                                    />
                                </div>
                                <div className="flex-1">
                                    <label className="text-xs text-muted-foreground block mb-1">Potential (SG)</label>
                                    <input
                                        type="number"
                                        step="0.001"
                                        value={grain.potential}
                                        onChange={(e) => updateGrain(grain.id, 'potential', parseFloat(e.target.value) || 1)}
                                        className="w-full p-2 bg-secondary/20 rounded-lg border border-white/5"
                                    />
                                </div>
                                <button
                                    onClick={() => removeGrain(grain.id)}
                                    disabled={grains.length === 1}
                                    className="p-2 text-red-400 hover:bg-red-500/20 rounded-lg disabled:opacity-30 disabled:cursor-not-allowed"
                                >
                                    <Trash2 className="w-4 h-4" />
                                </button>
                            </div>
                        ))}
                    </div>

                    <button
                        onClick={addGrain}
                        className="mt-3 px-4 py-2 text-sm text-muted-foreground hover:text-white border border-white/10 hover:border-white/30 rounded-lg flex items-center gap-2 transition-colors"
                    >
                        <Plus className="w-4 h-4" /> Add Grain
                    </button>
                </div>

                <button
                    onClick={runSim}
                    disabled={loading}
                    className="w-full mt-6 py-3 bg-purple-500 hover:bg-purple-600 text-white font-bold rounded-xl transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
                >
                    <Play className="w-4 h-4" /> {loading ? 'Simulating...' : 'Run Simulation'}
                </button>
            </div>

            {/* Hardware Warnings */}
            {result?.hardware_error && (
                <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-xl flex items-start gap-3">
                    <AlertCircle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
                    <div>
                        <div className="font-bold text-red-400">Hardware Limit Exceeded</div>
                        <div className="text-sm text-red-300">{result.hardware_error}</div>
                    </div>
                </div>
            )}

            {result?.hardware_warning && (
                <div className="p-4 bg-amber-500/10 border border-amber-500/30 rounded-xl flex items-start gap-3">
                    <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
                    <div>
                        <div className="font-bold text-amber-400">Hardware Warning</div>
                        <div className="text-sm text-amber-300">{result.hardware_warning}</div>
                    </div>
                </div>
            )}

            {/* Simulation Results */}
            {result && !result.error && (
                <div className="bg-black/40 p-6 rounded-2xl border border-purple-500/30 animate-in fade-in zoom-in-95">
                    <h4 className="text-lg font-bold text-purple-400 mb-4">Simulation Results</h4>

                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <div className="bg-black/30 p-4 rounded-xl text-center">
                            <div className="text-3xl font-bold text-white">{result.predicted_og?.toFixed(3) || 'N/A'}</div>
                            <div className="text-xs text-muted-foreground">Predicted OG</div>
                        </div>
                        {result.expected_fg && (
                            <div className="bg-black/30 p-4 rounded-xl text-center">
                                <div className="text-3xl font-bold text-green-400">{result.expected_fg}</div>
                                <div className="text-xs text-muted-foreground">Expected FG</div>
                            </div>
                        )}
                        {result.predicted_abv && (
                            <div className="bg-black/30 p-4 rounded-xl text-center">
                                <div className="text-3xl font-bold text-amber-400">{result.predicted_abv.toFixed(1)}%</div>
                                <div className="text-xs text-muted-foreground">Predicted ABV</div>
                            </div>
                        )}
                        {result.attenuation_used && (
                            <div className="bg-black/30 p-4 rounded-xl text-center">
                                <div className="text-3xl font-bold text-blue-400">{result.attenuation_used}%</div>
                                <div className="text-xs text-muted-foreground">Attenuation Used</div>
                            </div>
                        )}
                    </div>

                    {config.yeast && !result.yeast_found && (
                        <div className="mt-4 text-sm text-muted-foreground text-center">
                            ⚠️ Yeast "{config.yeast}" not found in history. Using default attenuation.
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
