'use client';

import { useState } from 'react';
import { Calculator } from 'lucide-react';

export function IBUCalculator() {
    const [inputs, setInputs] = useState({
        amount: 50,
        alpha: 13.0,
        time: 60,
        volume: 23,
        gravity: 1.050
    });
    const [result, setResult] = useState<number | null>(null);

    const calc = async () => {
        try {
            const res = await fetch('/api/automation/calc_ibu', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(inputs)
            });
            const data = await res.json();
            if (data.ibu) setResult(data.ibu);
        } catch (e) {
            console.error(e);
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

            <button
                onClick={calc}
                className="w-full py-4 bg-primary text-primary-foreground font-bold text-lg rounded-xl hover:opacity-90 transition-opacity"
            >
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
