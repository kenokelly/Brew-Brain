'use client';

import { useState, useEffect } from 'react';
import { Droplets, Pizza, AlertCircle, FlaskConical, Plus, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { apiFetch } from '@/lib/api';

interface GrainRow {
    name: string;
    weight_kg: string;
    lovibond: string;
}

export function Water() {
    const [profile, setProfile] = useState('neipa');
    const [stats, setStats] = useState<any>(null);
    const [loading, setLoading] = useState(false);
    const [pizzaOpen, setPizzaOpen] = useState(false);

    // Mash pH prediction state
    const [grains, setGrains] = useState<GrainRow[]>([
        { name: 'Pale Malt', weight_kg: '5', lovibond: '2.5' }
    ]);
    const [targetPh, setTargetPh] = useState('5.4');
    const [mashVolume, setMashVolume] = useState('20');
    const [mashPhResult, setMashPhResult] = useState<any>(null);
    const [mashPhLoading, setMashPhLoading] = useState(false);
    const [mashPhError, setMashPhError] = useState<string | null>(null);

    useEffect(() => {
        fetchWaterProfile();
    }, [profile]);

    const fetchWaterProfile = async () => {
        setLoading(true);
        try {
            const data = await apiFetch<any>(`/api/water/${profile}`);
            if (data.data) {
                setStats(data.data);
            } else {
                setStats(data);
            }
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    const MAPPING: { [key: string]: string } = {
        'calcium': 'Calcium (Ca)',
        'magnesium': 'Magnesium (Mg)',
        'sodium': 'Sodium (Na)',
        'chloride': 'Chloride (Cl)',
        'sulfate': 'Sulfate (SO4)',
        'bicarbonate': 'Bicarbonate (HCO3)',
        'ph': 'Target pH'
    };

    // Smart Recommendations Logic
    const getRecommendations = () => {
        if (!stats) return [];
        const isBrun = ['yellow', 'black', 'neipa_juicy', 'bru'].some(k => profile.includes(k));

        if (isBrun) {
            const ratio = stats.chloride > 0 ? (stats.sulfate / stats.chloride).toFixed(1) : 'High';
            let ratioDesc = 'Balanced';
            if (Number(ratio) > 2) ratioDesc = 'Very Bitter / Crisp';
            else if (Number(ratio) > 1.3) ratioDesc = 'Bitter Buildup';
            else if (Number(ratio) < 0.8) ratioDesc = 'Malty / Soft';

            return [
                { type: 'info', text: `Target Sulfate/Chloride Ratio: ${ratio} (${ratioDesc})` },
                { type: 'action', text: stats.sulfate > 100 ? 'Gypsum (CaSO4) required.' : null },
                { type: 'action', text: stats.chloride > 80 ? 'Calcium Chloride (CaCl2) required.' : null }
            ].filter(x => x.text);
        } else {
            // Simple rules
            if (profile.includes('neipa')) return [{ type: 'action', text: 'Tip: 2:1 Chloride to Sulfate ratio generally preferred for haze.' }];
            if (profile.includes('west')) return [{ type: 'action', text: 'Tip: High Sulfate enhances hop bitterness.' }];
            return [{ type: 'info', text: 'Balanced profile suitable for most ales.' }];
        }
    };

    // Mash pH prediction — uses the currently selected water profile's ion
    // values (bicarbonate/calcium/magnesium) plus a user-entered grain bill.
    const addGrainRow = () => {
        setGrains(prev => [...prev, { name: '', weight_kg: '', lovibond: '' }]);
    };

    const removeGrainRow = (index: number) => {
        setGrains(prev => prev.filter((_, i) => i !== index));
    };

    const updateGrainRow = (index: number, field: keyof GrainRow, value: string) => {
        setGrains(prev => prev.map((g, i) => i === index ? { ...g, [field]: value } : g));
    };

    const calculateMashPh = async () => {
        if (!stats) return;
        setMashPhLoading(true);
        setMashPhError(null);
        setMashPhResult(null);
        try {
            const payload = {
                grains: grains
                    .filter(g => g.weight_kg && g.lovibond)
                    .map(g => ({
                        name: g.name || 'Grain',
                        weight_kg: parseFloat(g.weight_kg),
                        lovibond: parseFloat(g.lovibond)
                    })),
                water_profile: {
                    bicarbonate: stats.bicarbonate ?? 0,
                    calcium: stats.calcium ?? 0,
                    magnesium: stats.magnesium ?? 0
                },
                target_ph: parseFloat(targetPh) || 5.4,
                mash_volume_l: parseFloat(mashVolume) || 20
            };
            if (payload.grains.length === 0) {
                setMashPhError('Add at least one grain with weight and color (°L).');
                return;
            }
            const res = await apiFetch<any>('/api/water/mash-ph', { method: 'POST', body: payload });
            if (res.status === 'success') {
                setMashPhResult(res.data);
            } else {
                setMashPhError(res.message || 'Calculation failed');
            }
        } catch (e: any) {
            setMashPhError(e.message || 'Calculation failed');
        } finally {
            setMashPhLoading(false);
        }
    };

    return (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4">
            <div className="flex flex-col md:flex-row gap-4 items-end">
                <div className="w-full md:w-1/3">
                    <label className="block text-sm text-muted-foreground mb-2">Water Profile</label>
                    <select
                        value={profile}
                        onChange={(e) => setProfile(e.target.value)}
                        className="w-full p-3 rounded-xl bg-secondary/30 border border-border/50 text-lg"
                    >
                        <option value="neipa">NEIPA (Juicy)</option>
                        <option value="west_coast">West Coast IPA</option>
                        <option value="balanced">Balanced</option>
                        <option value="ro">RO Water Base</option>
                        <option value="yellow_dry">Yellow Dry</option>
                        <option value="black_full">Black Full</option>
                    </select>
                </div>
            </div>

            {loading ? (
                <div className="h-40 flex items-center justify-center text-muted-foreground">Loading Profile...</div>
            ) : stats && (
                <div className="space-y-6">
                    {/* Ion Concentration Grid */}
                    <div>
                        <h4 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-3">Target Ion Profile (ppm)</h4>
                        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4">
                            {Object.entries(MAPPING).map(([key, label]) => {
                                const val = stats[key] !== undefined ? stats[key] : (stats[`final_${key}`] !== undefined ? stats[`final_${key}`] : '0');
                                return (
                                    <div key={key} className="bg-card/50 p-4 rounded-2xl border border-white/5 text-center">
                                        <div className="text-2xl font-bold text-primary">{val}</div>
                                        <div className="text-xs text-muted-foreground uppercase mt-1">{label}</div>
                                    </div>
                                );
                            })}
                        </div>
                    </div>

                    {/* Salt Additions Summary */}
                    {(stats.gypsum_g !== undefined || stats.calcium_chloride_g !== undefined) && (
                        <div className="bg-card/40 p-6 rounded-2xl border border-primary/20">
                            <h4 className="text-lg font-bold text-foreground mb-4 flex items-center gap-2">
                                🧂 Recommended Salt Additions ({stats.volume_liters || 23}L Batch)
                            </h4>
                            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                                <div className="bg-black/30 p-3 rounded-xl border border-white/5 text-center">
                                    <div className="text-xl font-bold text-amber-400">{stats.gypsum_g ?? 0}g</div>
                                    <div className="text-xs text-muted-foreground mt-1">Gypsum (CaSO4)</div>
                                </div>
                                <div className="bg-black/30 p-3 rounded-xl border border-white/5 text-center">
                                    <div className="text-xl font-bold text-amber-400">{stats.calcium_chloride_g ?? 0}g</div>
                                    <div className="text-xs text-muted-foreground mt-1">CaCl2 (Calcium Chloride)</div>
                                </div>
                                <div className="bg-black/30 p-3 rounded-xl border border-white/5 text-center">
                                    <div className="text-xl font-bold text-amber-400">{stats.epsom_g ?? 0}g</div>
                                    <div className="text-xs text-muted-foreground mt-1">Epsom Salt (MgSO4)</div>
                                </div>
                                <div className="bg-black/30 p-3 rounded-xl border border-white/5 text-center">
                                    <div className="text-xl font-bold text-amber-400">{stats.baking_soda_g ?? 0}g</div>
                                    <div className="text-xs text-muted-foreground mt-1">Baking Soda (NaHCO3)</div>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Mash pH Prediction */}
                    <div className="bg-card/40 p-6 rounded-2xl border border-primary/20">
                        <h4 className="text-lg font-bold text-foreground mb-1 flex items-center gap-2">
                            <FlaskConical className="w-5 h-5 text-primary" /> Mash pH Prediction
                        </h4>
                        <p className="text-xs text-muted-foreground mb-4">
                            Kolbach Residual Alkalinity, using this profile&apos;s Ca/Mg/HCO3 above.
                        </p>

                        <div className="space-y-2 mb-4">
                            {grains.map((g, i) => (
                                <div key={i} className="flex gap-2 items-center">
                                    <input
                                        placeholder="Grain name"
                                        value={g.name}
                                        onChange={e => updateGrainRow(i, 'name', e.target.value)}
                                        className="flex-1 bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-sm"
                                    />
                                    <input
                                        type="number" step="0.1" placeholder="kg"
                                        value={g.weight_kg}
                                        onChange={e => updateGrainRow(i, 'weight_kg', e.target.value)}
                                        className="w-20 bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-sm"
                                    />
                                    <input
                                        type="number" step="0.1" placeholder="°L"
                                        value={g.lovibond}
                                        onChange={e => updateGrainRow(i, 'lovibond', e.target.value)}
                                        className="w-20 bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-sm"
                                    />
                                    <button
                                        type="button"
                                        onClick={() => removeGrainRow(i)}
                                        disabled={grains.length === 1}
                                        className="text-muted-foreground hover:text-red-400 disabled:opacity-30 p-2"
                                    >
                                        <X className="w-4 h-4" />
                                    </button>
                                </div>
                            ))}
                            <button
                                type="button"
                                onClick={addGrainRow}
                                className="flex items-center gap-1 text-xs text-primary hover:text-primary/80 font-medium"
                            >
                                <Plus className="w-3 h-3" /> Add Grain
                            </button>
                        </div>

                        <div className="flex flex-wrap gap-4 items-end mb-4">
                            <div>
                                <label className="block text-xs text-muted-foreground mb-1">Target pH</label>
                                <input
                                    type="number" step="0.1"
                                    value={targetPh}
                                    onChange={e => setTargetPh(e.target.value)}
                                    className="w-24 bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-sm"
                                />
                            </div>
                            <div>
                                <label className="block text-xs text-muted-foreground mb-1">Mash Volume (L)</label>
                                <input
                                    type="number" step="0.5"
                                    value={mashVolume}
                                    onChange={e => setMashVolume(e.target.value)}
                                    className="w-28 bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-sm"
                                />
                            </div>
                            <button
                                type="button"
                                onClick={calculateMashPh}
                                disabled={mashPhLoading}
                                className="bg-primary text-primary-foreground px-5 py-2 rounded-lg font-bold text-sm hover:bg-primary/90 disabled:opacity-50"
                            >
                                {mashPhLoading ? 'Calculating...' : 'Predict Mash pH'}
                            </button>
                        </div>

                        {mashPhError && (
                            <p className="text-sm text-red-400 flex items-center gap-2">
                                <AlertCircle className="w-4 h-4" /> {mashPhError}
                            </p>
                        )}

                        {mashPhResult && (
                            <div className="bg-black/30 p-4 rounded-xl border border-white/5 space-y-3">
                                <div className="flex items-baseline gap-3">
                                    <span className="text-3xl font-bold text-primary">{mashPhResult.predicted_ph}</span>
                                    <span className="text-sm text-muted-foreground">predicted mash pH (target {mashPhResult.target_ph})</span>
                                </div>
                                <p className="text-sm text-muted-foreground">{mashPhResult.notes}</p>
                                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs pt-2 border-t border-white/10">
                                    <div>
                                        <div className="text-muted-foreground uppercase tracking-wider text-[10px]">Grain Effect</div>
                                        <div className="font-mono">{mashPhResult.grain_contribution}</div>
                                    </div>
                                    <div>
                                        <div className="text-muted-foreground uppercase tracking-wider text-[10px]">Water Effect</div>
                                        <div className="font-mono">{mashPhResult.water_contribution}</div>
                                    </div>
                                    {mashPhResult.lactic_acid_ml > 0 && (
                                        <div>
                                            <div className="text-muted-foreground uppercase tracking-wider text-[10px]">Lactic Acid (88%)</div>
                                            <div className="font-mono text-amber-400">{mashPhResult.lactic_acid_ml}ml</div>
                                        </div>
                                    )}
                                    {mashPhResult.calcium_carbite_g > 0 && (
                                        <div>
                                            <div className="text-muted-foreground uppercase tracking-wider text-[10px]">Chalk (CaCO3)</div>
                                            <div className="font-mono text-amber-400">{mashPhResult.calcium_carbite_g}g</div>
                                        </div>
                                    )}
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* Recommendations */}
            <div className="bg-blue-500/5 border border-blue-500/20 rounded-xl p-6">
                <h3 className="text-blue-400 font-bold mb-4 flex items-center gap-2">
                    <Droplets className="w-5 h-5" /> Chemistry Notes
                </h3>
                <ul className="space-y-2">
                    {getRecommendations().map((rec: any, i) => (
                        <li key={i} className="flex items-center gap-2 text-sm text-muted-foreground">
                            <div className="w-1.5 h-1.5 rounded-full bg-blue-500" />
                            {rec.text}
                        </li>
                    ))}
                </ul>
            </div>

            {/* Pizza Pairing - Because why not */}
            <div className="border border-amber-500/20 bg-amber-500/5 rounded-xl overflow-hidden">
                <button
                    onClick={() => setPizzaOpen(!pizzaOpen)}
                    className="w-full flex items-center justify-between p-4 text-amber-500 hover:bg-amber-500/10 transition-colors"
                >
                    <span className="font-bold flex items-center gap-2">
                        <Pizza className="w-5 h-5" /> Pizza Pairing Schedule
                    </span>
                    <span className={cn("transition-transform", pizzaOpen && "rotate-180")}>▼</span>
                </button>
                {pizzaOpen && (
                    <div className="p-4 pt-0 text-sm text-muted-foreground">
                        <p>Recommended pairing calculated based on water profile salinity and beer style:</p>
                        <ul className="mt-2 space-y-1 list-disc list-inside">
                            {profile.includes('neipa') ? (
                                <li><strong>Spicy Pepperoni:</strong> Cuts through the juice.</li>
                            ) : profile.includes('west') ? (
                                <li><strong>BBQ Chicken:</strong> Complements the resinous hops.</li>
                            ) : (
                                <li><strong>Margherita:</strong> Balanced classic for a balanced water profile.</li>
                            )}
                        </ul>
                    </div>
                )}
            </div>
        </div>
    );
}
