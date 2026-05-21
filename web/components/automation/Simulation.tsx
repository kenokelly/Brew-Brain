'use client';

import { useState } from 'react';
import { FlaskConical, Play, Plus, Trash2, AlertTriangle, AlertCircle, CalendarClock, Brain } from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine
} from 'recharts';

interface Grain {
    id: number;
    weight_kg: number;
    potential: number;
}

interface TimelineEvent {
    day: number;
    expected_sg: number;
    phase: string;
}

interface SimResult {
    timeline?: TimelineEvent[];
    llm_analysis?: string;
    error?: string;
    status?: string;
}

export function Simulation() {
    const [config, setConfig] = useState({
        efficiency: 75,
        volume: 23,
        yeast: 'US-05'
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
            // Using the new timeline API instead of the basic simulation
            const res = await fetch('/api/automation/simulate/timeline', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    efficiency: config.efficiency,
                    volume: config.volume,
                    yeast: config.yeast || undefined,
                    grains: grains.map(g => ({ weight_kg: g.weight_kg, potential: g.potential }))
                })
            });
            const { data, status, error } = await res.json();
            if (status === 'error') {
                setResult({ error });
            } else {
                setResult(data);
            }
        } catch (e) {
            setResult({ error: 'Failed to connect to simulation API' });
        } finally {
            setLoading(false);
        }
    };

    const totalGrain = grains.reduce((sum, g) => sum + g.weight_kg, 0);

    return (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4">
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                {/* Configuration Panel */}
                <div className="lg:col-span-4 space-y-6">
                    <div className="bg-card/50 p-6 rounded-2xl border border-white/5 backdrop-blur-xl">
                        <h3 className="text-xl font-bold mb-4 flex items-center gap-2">
                            <FlaskConical className="w-5 h-5 text-purple-400" /> Brew Config
                        </h3>

                        <div className="space-y-4 mb-6">
                            <div>
                                <label className="text-xs uppercase text-muted-foreground block mb-1">Efficiency %</label>
                                <input
                                    type="number"
                                    value={config.efficiency}
                                    onChange={(e) => setConfig({ ...config, efficiency: parseFloat(e.target.value) })}
                                    className="w-full p-2 bg-secondary/20 rounded-lg border border-white/5 focus:border-purple-500/50 outline-none transition-colors"
                                />
                            </div>
                            <div>
                                <label className="text-xs uppercase text-muted-foreground block mb-1">Volume (L)</label>
                                <input
                                    type="number"
                                    value={config.volume}
                                    onChange={(e) => setConfig({ ...config, volume: parseFloat(e.target.value) })}
                                    className="w-full p-2 bg-secondary/20 rounded-lg border border-white/5 focus:border-purple-500/50 outline-none transition-colors"
                                />
                            </div>
                            <div>
                                <label className="text-xs uppercase text-muted-foreground block mb-1">Yeast Strain</label>
                                <input
                                    type="text"
                                    value={config.yeast}
                                    onChange={(e) => setConfig({ ...config, yeast: e.target.value })}
                                    placeholder="e.g. US-05"
                                    className="w-full p-2 bg-secondary/20 rounded-lg border border-white/5 focus:border-purple-500/50 outline-none transition-colors"
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
                                {grains.map((grain) => (
                                    <div key={grain.id} className="flex gap-2 items-end p-3 bg-black/20 rounded-xl border-l-2 border-purple-500/50 hover:bg-black/40 transition-colors">
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
                                            <label className="text-xs text-muted-foreground block mb-1">Potential</label>
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
                                            className="p-2 text-red-400 hover:bg-red-500/20 rounded-lg disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                                        >
                                            <Trash2 className="w-4 h-4" />
                                        </button>
                                    </div>
                                ))}
                            </div>

                            <button
                                onClick={addGrain}
                                className="w-full mt-3 px-4 py-2 text-sm text-muted-foreground hover:text-white bg-white/5 hover:bg-white/10 rounded-lg flex items-center justify-center gap-2 transition-colors"
                            >
                                <Plus className="w-4 h-4" /> Add Grain
                            </button>
                        </div>

                        <button
                            onClick={runSim}
                            disabled={loading}
                            className="w-full mt-6 py-3 bg-purple-500 hover:bg-purple-600 text-white font-bold rounded-xl transition-all hover:scale-[1.02] flex items-center justify-center gap-2 disabled:opacity-50 disabled:hover:scale-100 shadow-lg shadow-purple-500/20"
                        >
                            <Play className="w-4 h-4" /> {loading ? 'Simulating...' : 'Generate Timeline'}
                        </button>
                    </div>
                </div>

                {/* Timeline Visualization */}
                <div className="lg:col-span-8 space-y-6">
                    {result?.error && (
                        <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-xl flex items-start gap-3">
                            <AlertCircle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
                            <div>
                                <div className="font-bold text-red-400">Simulation Failed</div>
                                <div className="text-sm text-red-300">{result.error}</div>
                            </div>
                        </div>
                    )}

                    {!result && !loading && (
                        <div className="h-full min-h-[400px] flex flex-col items-center justify-center text-muted-foreground border-2 border-dashed border-white/10 rounded-2xl bg-white/5">
                            <CalendarClock className="w-12 h-12 mb-4 opacity-50" />
                            <p>Configure your brew and run the simulation to project the fermentation timeline.</p>
                        </div>
                    )}

                    {result?.timeline && (
                        <div className="bg-card/50 p-6 rounded-2xl border border-white/5 backdrop-blur-xl animate-in fade-in zoom-in-95">
                            <div className="flex justify-between items-end mb-6">
                                <div>
                                    <h4 className="text-lg font-bold text-purple-400 flex items-center gap-2">
                                        <CalendarClock className="w-5 h-5" /> Fermentation Timeline
                                    </h4>
                                    <p className="text-sm text-muted-foreground">Predicted gravity curve over 14 days</p>
                                </div>
                                <div className="text-right">
                                    <div className="text-sm text-muted-foreground uppercase">Target ABV</div>
                                    <div className="text-2xl font-bold text-green-400">
                                        {((result.timeline[0].expected_sg - result.timeline[result.timeline.length - 1].expected_sg) * 131.25).toFixed(1)}%
                                    </div>
                                </div>
                            </div>

                            <div className="h-[300px] w-full">
                                <ResponsiveContainer width="100%" height="100%">
                                    <LineChart data={result.timeline} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" vertical={false} />
                                        <XAxis 
                                            dataKey="day" 
                                            stroke="rgba(255,255,255,0.5)" 
                                            tickFormatter={(val) => `Day ${val}`}
                                        />
                                        <YAxis 
                                            domain={['dataMin - 0.005', 'dataMax + 0.005']}
                                            tickFormatter={(val) => val.toFixed(3)}
                                            stroke="rgba(255,255,255,0.5)"
                                        />
                                        <Tooltip 
                                            contentStyle={{ backgroundColor: 'rgba(0,0,0,0.8)', border: '1px solid rgba(168, 85, 247, 0.5)', borderRadius: '8px' }}
                                            formatter={(value: number) => [value.toFixed(3), 'Specific Gravity']}
                                            labelFormatter={(label) => `Day ${label}`}
                                        />
                                        <ReferenceLine y={result.timeline[result.timeline.length - 1].expected_sg} stroke="rgba(74, 222, 128, 0.5)" strokeDasharray="3 3" />
                                        <Line 
                                            type="monotone" 
                                            dataKey="expected_sg" 
                                            stroke="#a855f7" 
                                            strokeWidth={3}
                                            dot={{ r: 4, fill: '#a855f7', strokeWidth: 2, stroke: '#000' }}
                                            activeDot={{ r: 6, fill: '#a855f7' }}
                                        />
                                    </LineChart>
                                </ResponsiveContainer>
                            </div>

                            {/* Phase breakdown */}
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6 pt-6 border-t border-white/10">
                                <div className="bg-black/30 p-3 rounded-xl border-l-2 border-purple-500 text-center">
                                    <div className="text-xl font-bold text-white">{result.timeline[0].expected_sg.toFixed(3)}</div>
                                    <div className="text-xs text-muted-foreground">Original Gravity</div>
                                </div>
                                <div className="bg-black/30 p-3 rounded-xl border-l-2 border-green-500 text-center">
                                    <div className="text-xl font-bold text-white">{result.timeline[result.timeline.length - 1].expected_sg.toFixed(3)}</div>
                                    <div className="text-xs text-muted-foreground">Final Gravity</div>
                                </div>
                                <div className="bg-black/30 p-3 rounded-xl text-center md:col-span-2 flex flex-col justify-center">
                                    <div className="text-sm font-medium text-white">Yeast Selected</div>
                                    <div className="text-xs text-muted-foreground">{config.yeast}</div>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* AI Analysis Panel */}
                    {result?.llm_analysis && (
                        <div className="p-5 bg-purple-500/10 border border-purple-500/30 rounded-2xl flex items-start gap-4 animate-in fade-in slide-in-from-bottom-4">
                            <div className="p-2 bg-purple-500/20 rounded-lg shrink-0">
                                <Brain className="w-6 h-6 text-purple-400" />
                            </div>
                            <div>
                                <div className="font-bold text-purple-400 mb-1 flex items-center gap-2">
                                    AI Brewmaster Insight
                                    <span className="text-[10px] px-2 py-0.5 bg-purple-500/20 text-purple-300 rounded-full uppercase tracking-wider">Ollama</span>
                                </div>
                                <div className="text-sm text-purple-100 leading-relaxed">
                                    {result.llm_analysis}
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
