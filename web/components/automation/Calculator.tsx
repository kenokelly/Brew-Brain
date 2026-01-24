'use client';

import { useState } from 'react';
import { Calculator, Gauge, Beaker, Droplets } from 'lucide-react';
import { cn } from '@/lib/utils';
import toast from 'react-hot-toast';

type CalcTab = 'ibu' | 'carbonation' | 'refractometer' | 'priming';

export function IBUCalculator() {
    const [activeTab, setActiveTab] = useState<CalcTab>('ibu');

    return (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4">
            {/* Sub-tab Navigation */}
            <div className="flex gap-2 flex-wrap">
                {[
                    { id: 'ibu' as CalcTab, label: 'IBU Calculator', icon: Calculator },
                    { id: 'carbonation' as CalcTab, label: 'Carbonation', icon: Gauge },
                    { id: 'refractometer' as CalcTab, label: 'Refractometer', icon: Beaker },
                    { id: 'priming' as CalcTab, label: 'Priming Sugar', icon: Droplets },
                ].map((tab) => (
                    <button
                        key={tab.id}
                        onClick={() => setActiveTab(tab.id)}
                        aria-label={`Switch to ${tab.label}`}
                        className={cn(
                            "flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium transition-all",
                            activeTab === tab.id
                                ? "bg-primary text-primary-foreground"
                                : "bg-secondary/30 text-muted-foreground hover:bg-secondary/50"
                        )}
                    >
                        <tab.icon className="w-4 h-4" />
                        {tab.label}
                    </button>
                ))}
            </div>

            {/* Calculator Content */}
            {activeTab === 'ibu' && <IBUCalc />}
            {activeTab === 'carbonation' && <CarbonationCalc />}
            {activeTab === 'refractometer' && <RefractometerCalc />}
            {activeTab === 'priming' && <PrimingCalc />}
        </div>
    );
}

// IBU Calculator
function IBUCalc() {
    const [inputs, setInputs] = useState({
        amount: 50,
        alpha: 13.0,
        time: 60,
        volume: 23,
        gravity: 1.050
    });
    const [result, setResult] = useState<number | null>(null);
    const [loading, setLoading] = useState(false);

    const calc = async () => {
        setLoading(true);
        try {
            const res = await fetch('/api/automation/calc_ibu', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(inputs)
            });
            const data = await res.json();
            if (data.error) {
                toast.error(data.error);
            } else if (data.ibu) {
                setResult(data.ibu);
                toast.success(`IBU calculated: ${data.ibu.toFixed(1)}`);
            }
        } catch (e) {
            toast.error('Calculation failed');
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        setInputs({ ...inputs, [e.target.name]: parseFloat(e.target.value) });
    };

    return (
        <div className="max-w-2xl mx-auto bg-card/50 backdrop-blur-md rounded-3xl border border-white/5 p-8">
            <h2 className="text-2xl font-bold mb-6 flex items-center gap-2">
                <Calculator className="w-6 h-6 text-primary" />
                IBU Calculator (G40 Tuned)
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
                <div>
                    <label className="block text-sm text-muted-foreground mb-2">Hop Amount (g)</label>
                    <input type="number" name="amount" value={inputs.amount} onChange={handleChange} className="w-full p-3 rounded-xl bg-secondary/30 border border-border/50 text-lg" />
                </div>
                <div>
                    <label className="block text-sm text-muted-foreground mb-2">Alpha Acid (%)</label>
                    <input type="number" name="alpha" value={inputs.alpha} onChange={handleChange} className="w-full p-3 rounded-xl bg-secondary/30 border border-border/50 text-lg" />
                </div>
                <div>
                    <label className="block text-sm text-muted-foreground mb-2">Boil Time (min)</label>
                    <input type="number" name="time" value={inputs.time} onChange={handleChange} className="w-full p-3 rounded-xl bg-secondary/30 border border-border/50 text-lg" />
                </div>
                <div>
                    <label className="block text-sm text-muted-foreground mb-2">Batch Volume (L)</label>
                    <input type="number" name="volume" value={inputs.volume} onChange={handleChange} className="w-full p-3 rounded-xl bg-secondary/30 border border-border/50 text-lg" />
                </div>
                <div className="md:col-span-2">
                    <label className="block text-sm text-muted-foreground mb-2">Original Gravity (SG)</label>
                    <input type="number" name="gravity" value={inputs.gravity} step="0.001" onChange={handleChange} className="w-full p-3 rounded-xl bg-secondary/30 border border-border/50 text-lg" />
                </div>
            </div>

            <button onClick={calc} className="w-full py-4 bg-primary text-primary-foreground font-bold text-lg rounded-xl hover:opacity-90 transition-opacity">
                Calculate IBU
            </button>

            {result !== null && (
                <div className="mt-8 text-center animate-in zoom-in duration-300">
                    <div className="text-sm text-muted-foreground uppercase tracking-widest mb-1">Result</div>
                    <div className="text-5xl font-extrabold text-primary">{result} IBU</div>
                </div>
            )}
        </div>
    );
}

// Carbonation Calculator
function CarbonationCalc() {
    const [inputs, setInputs] = useState({ temp_c: 4, volumes_co2: 2.4 });
    const [result, setResult] = useState<{
        psi?: number;
        bar?: number;
        kpa?: number;
        style_suggestion?: string;
        error?: string;
    } | null>(null);
    const [loading, setLoading] = useState(false);

    const calc = async () => {
        setLoading(true);
        try {
            const res = await fetch('/api/automation/calc/carbonation', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(inputs)
            });
            const data = await res.json();
            if (data.error) {
                toast.error(data.error);
            } else {
                setResult(data);
                toast.success(`Carbonation: ${data.psi?.toFixed(1)} PSI`);
            }
        } catch (e) {
            toast.error('Calculation failed');
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="max-w-2xl mx-auto bg-card/50 backdrop-blur-md rounded-3xl border border-white/5 p-8">
            <h2 className="text-2xl font-bold mb-6 flex items-center gap-2">
                <Gauge className="w-6 h-6 text-blue-400" />
                Forced Carbonation Calculator
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
                <div>
                    <label className="block text-sm text-muted-foreground mb-2">Beer Temperature (°C)</label>
                    <input type="number" value={inputs.temp_c} onChange={(e) => setInputs({ ...inputs, temp_c: parseFloat(e.target.value) })} className="w-full p-3 rounded-xl bg-secondary/30 border border-border/50 text-lg" />
                </div>
                <div>
                    <label className="block text-sm text-muted-foreground mb-2">Target CO2 Volumes</label>
                    <input type="number" step="0.1" value={inputs.volumes_co2} onChange={(e) => setInputs({ ...inputs, volumes_co2: parseFloat(e.target.value) })} className="w-full p-3 rounded-xl bg-secondary/30 border border-border/50 text-lg" />
                </div>
            </div>

            <div className="mb-6 p-4 bg-blue-500/10 border border-blue-500/20 rounded-xl text-sm text-muted-foreground">
                <div className="font-bold text-blue-400 mb-2">CO2 Volume Guidelines:</div>
                <ul className="grid grid-cols-2 gap-1">
                    <li>British Cask: 1.5-2.0</li>
                    <li>American Ale: 2.2-2.7</li>
                    <li>Lager/Pilsner: 2.5-2.8</li>
                    <li>Hefeweizen: 3.0-4.0</li>
                </ul>
            </div>

            <button onClick={calc} className="w-full py-4 bg-blue-500 text-white font-bold text-lg rounded-xl hover:bg-blue-600 transition-colors">
                Calculate PSI
            </button>

            {result && !result.error && (
                <div className="mt-8 grid grid-cols-3 gap-4 text-center animate-in zoom-in">
                    <div className="bg-black/20 p-4 rounded-xl">
                        <div className="text-3xl font-bold text-blue-400">{result.psi}</div>
                        <div className="text-xs text-muted-foreground">PSI</div>
                    </div>
                    <div className="bg-black/20 p-4 rounded-xl">
                        <div className="text-3xl font-bold text-blue-400">{result.bar}</div>
                        <div className="text-xs text-muted-foreground">BAR</div>
                    </div>
                    <div className="bg-black/20 p-4 rounded-xl">
                        <div className="text-3xl font-bold text-blue-400">{result.kpa}</div>
                        <div className="text-xs text-muted-foreground">kPa</div>
                    </div>
                    <div className="col-span-3 mt-2 text-sm text-muted-foreground">
                        Style Match: <span className="text-blue-400">{result.style_suggestion}</span>
                    </div>
                </div>
            )}
        </div>
    );
}

// Refractometer Correction
function RefractometerCalc() {
    const [inputs, setInputs] = useState({ original_brix: 15.0, final_brix: 8.0, wort_correction_factor: 1.04 });
    const [result, setResult] = useState<any>(null);

    const calc = async () => {
        try {
            const res = await fetch('/api/automation/calc/refractometer', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(inputs)
            });
            const data = await res.json();
            setResult(data);
        } catch (e) {
            console.error(e);
        }
    };

    return (
        <div className="max-w-2xl mx-auto bg-card/50 backdrop-blur-md rounded-3xl border border-white/5 p-8">
            <h2 className="text-2xl font-bold mb-6 flex items-center gap-2">
                <Beaker className="w-6 h-6 text-purple-400" />
                Refractometer Correction
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
                <div>
                    <label className="block text-sm text-muted-foreground mb-2">Original Brix (OG)</label>
                    <input type="number" step="0.1" value={inputs.original_brix} onChange={(e) => setInputs({ ...inputs, original_brix: parseFloat(e.target.value) })} className="w-full p-3 rounded-xl bg-secondary/30 border border-border/50 text-lg" />
                </div>
                <div>
                    <label className="block text-sm text-muted-foreground mb-2">Final Brix Reading</label>
                    <input type="number" step="0.1" value={inputs.final_brix} onChange={(e) => setInputs({ ...inputs, final_brix: parseFloat(e.target.value) })} className="w-full p-3 rounded-xl bg-secondary/30 border border-border/50 text-lg" />
                </div>
                <div className="md:col-span-2">
                    <label className="block text-sm text-muted-foreground mb-2">Wort Correction Factor</label>
                    <input type="number" step="0.01" value={inputs.wort_correction_factor} onChange={(e) => setInputs({ ...inputs, wort_correction_factor: parseFloat(e.target.value) })} className="w-full p-3 rounded-xl bg-secondary/30 border border-border/50 text-lg" />
                </div>
            </div>

            <button onClick={calc} className="w-full py-4 bg-purple-500 text-white font-bold text-lg rounded-xl hover:bg-purple-600 transition-colors">
                Calculate Corrected FG
            </button>

            {result && !result.error && (
                <div className="mt-8 space-y-4 animate-in zoom-in">
                    <div className="grid grid-cols-2 gap-4 text-center">
                        <div className="bg-black/20 p-4 rounded-xl">
                            <div className="text-3xl font-bold text-purple-400">{result.original_gravity}</div>
                            <div className="text-xs text-muted-foreground">Original Gravity</div>
                        </div>
                        <div className="bg-black/20 p-4 rounded-xl">
                            <div className="text-3xl font-bold text-purple-400">{result.corrected_final_gravity}</div>
                            <div className="text-xs text-muted-foreground">Corrected FG</div>
                        </div>
                    </div>
                    <div className="grid grid-cols-2 gap-4 text-center">
                        <div className="bg-black/20 p-4 rounded-xl">
                            <div className="text-2xl font-bold text-green-400">{result.abv}%</div>
                            <div className="text-xs text-muted-foreground">ABV</div>
                        </div>
                        <div className="bg-black/20 p-4 rounded-xl">
                            <div className="text-2xl font-bold text-amber-400">{result.apparent_attenuation}%</div>
                            <div className="text-xs text-muted-foreground">Apparent Attenuation</div>
                        </div>
                    </div>
                    <div className="text-center text-xs text-muted-foreground">
                        Formula: {result.formula}
                    </div>
                </div>
            )}
        </div>
    );
}

// Priming Sugar Calculator
function PrimingCalc() {
    const [inputs, setInputs] = useState({ volume_liters: 20, temp_c: 20, target_co2: 2.4, sugar_type: 'corn_sugar' });
    const [result, setResult] = useState<any>(null);

    const calc = async () => {
        try {
            const res = await fetch('/api/automation/calc/priming', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(inputs)
            });
            const data = await res.json();
            setResult(data);
        } catch (e) {
            console.error(e);
        }
    };

    return (
        <div className="max-w-2xl mx-auto bg-card/50 backdrop-blur-md rounded-3xl border border-white/5 p-8">
            <h2 className="text-2xl font-bold mb-6 flex items-center gap-2">
                <Droplets className="w-6 h-6 text-amber-400" />
                Priming Sugar Calculator
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
                <div>
                    <label className="block text-sm text-muted-foreground mb-2">Batch Volume (L)</label>
                    <input type="number" value={inputs.volume_liters} onChange={(e) => setInputs({ ...inputs, volume_liters: parseFloat(e.target.value) })} className="w-full p-3 rounded-xl bg-secondary/30 border border-border/50 text-lg" />
                </div>
                <div>
                    <label className="block text-sm text-muted-foreground mb-2">Beer Temperature (°C)</label>
                    <input type="number" value={inputs.temp_c} onChange={(e) => setInputs({ ...inputs, temp_c: parseFloat(e.target.value) })} className="w-full p-3 rounded-xl bg-secondary/30 border border-border/50 text-lg" />
                </div>
                <div>
                    <label className="block text-sm text-muted-foreground mb-2">Target CO2 Volumes</label>
                    <input type="number" step="0.1" value={inputs.target_co2} onChange={(e) => setInputs({ ...inputs, target_co2: parseFloat(e.target.value) })} className="w-full p-3 rounded-xl bg-secondary/30 border border-border/50 text-lg" />
                </div>
                <div>
                    <label className="block text-sm text-muted-foreground mb-2">Sugar Type</label>
                    <select value={inputs.sugar_type} onChange={(e) => setInputs({ ...inputs, sugar_type: e.target.value })} className="w-full p-3 rounded-xl bg-secondary/30 border border-border/50 text-lg">
                        <option value="corn_sugar">Corn Sugar (Dextrose)</option>
                        <option value="table_sugar">Table Sugar (Sucrose)</option>
                        <option value="honey">Honey</option>
                        <option value="dme">Dry Malt Extract</option>
                        <option value="brown_sugar">Brown Sugar</option>
                        <option value="maple_syrup">Maple Syrup</option>
                    </select>
                </div>
            </div>

            <button onClick={calc} className="w-full py-4 bg-amber-500 text-black font-bold text-lg rounded-xl hover:bg-amber-400 transition-colors">
                Calculate Priming
            </button>

            {result && !result.error && (
                <div className="mt-8 space-y-4 animate-in zoom-in">
                    <div className="text-center">
                        <div className="text-5xl font-bold text-amber-400">{result.total_grams}g</div>
                        <div className="text-sm text-muted-foreground mt-1">Total {result.sugar_type}</div>
                    </div>
                    <div className="grid grid-cols-2 gap-4 text-center">
                        <div className="bg-black/20 p-4 rounded-xl">
                            <div className="text-2xl font-bold text-white">{result.per_500ml_bottle}g</div>
                            <div className="text-xs text-muted-foreground">Per 500ml Bottle</div>
                        </div>
                        <div className="bg-black/20 p-4 rounded-xl">
                            <div className="text-2xl font-bold text-white">{result.per_330ml_bottle}g</div>
                            <div className="text-xs text-muted-foreground">Per 330ml Bottle</div>
                        </div>
                    </div>
                    <div className="text-center text-sm text-muted-foreground">
                        Residual CO2: {result.residual_co2} vol | Adding: {result.added_co2} vol
                    </div>
                    <div className="text-center text-xs text-muted-foreground">
                        {result.conditioning_time}
                    </div>
                </div>
            )}
        </div>
    );
}
