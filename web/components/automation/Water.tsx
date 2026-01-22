'use client';

import { useState, useEffect } from 'react';
import { Droplets, Pizza, AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

export function Water() {
    const [profile, setProfile] = useState('neipa');
    const [stats, setStats] = useState<any>(null);
    const [loading, setLoading] = useState(false);
    const [pizzaOpen, setPizzaOpen] = useState(false);

    useEffect(() => {
        fetchWaterProfile();
    }, [profile]);

    const fetchWaterProfile = async () => {
        setLoading(true);
        try {
            const res = await fetch(`/api/automation/water/${profile}`);
            const data = await res.json();
            setStats(data);
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
                <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4">
                    {Object.entries(MAPPING).map(([key, label]) => (
                        <div key={key} className="bg-card/50 p-4 rounded-2xl border border-white/5 text-center">
                            <div className="text-2xl font-bold text-primary">{stats[key]}</div>
                            <div className="text-xs text-muted-foreground uppercase mt-1">{label}</div>
                        </div>
                    ))}
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
