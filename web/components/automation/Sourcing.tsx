'use client';

import { useState } from 'react';
import { ShoppingCart, Search, ExternalLink } from 'lucide-react';

export function Sourcing() {
    const [query, setQuery] = useState('');
    const [results, setResults] = useState<any[]>([]);
    const [loading, setLoading] = useState(false);
    const [shoppingList, setShoppingList] = useState<any>(null);

    const search = async () => {
        if (!query) return;
        setLoading(true);
        try {
            const res = await fetch('/api/automation/sourcing/search', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query })
            });
            const data = await res.json();
            setResults(Array.isArray(data) ? data : []);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    const generateList = async () => {
        // Placeholder for full logic
        // Need access to current recipe context or inputs
        setLoading(true);
        try {
            // Mock call for now
            const res = await fetch('/api/automation/sourcing/list', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ hops: [], fermentables: [] })
            });
            const data = await res.json();
            setShoppingList(data);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4">
            <div className="bg-card/50 p-6 rounded-2xl border border-white/5">
                <h3 className="text-xl font-bold mb-4 flex items-center gap-2">
                    <ShoppingCart className="w-5 h-5 text-emerald-400" /> Sourcing & Shopping List
                </h3>

                <div className="flex gap-4 mb-6">
                    <input
                        type="text"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        placeholder="Quick Search (e.g. Maris Otter)"
                        className="flex-1 p-3 rounded-xl bg-secondary/30 border border-border/50 text-lg"
                        onKeyDown={(e) => e.key === 'Enter' && search()}
                    />
                    <button
                        onClick={search}
                        className="px-6 bg-emerald-500 text-white font-bold rounded-xl hover:bg-emerald-600 transition-colors"
                    >
                        Search
                    </button>
                </div>

                <div className="space-y-2">
                    {results.map((item, i) => (
                        <div key={i} className="flex justify-between items-center p-3 bg-white/5 rounded-lg border border-white/5">
                            <div>
                                <div className="font-bold">{item.title}</div>
                                <div className="text-xs text-muted-foreground">{item.source}</div>
                            </div>
                            <div className="font-mono font-bold text-emerald-400">{item.price}</div>
                        </div>
                    ))}
                </div>
            </div>

            <div className="bg-card/50 p-6 rounded-2xl border border-white/5 opacity-50 pointer-events-none">
                <h4 className="text-lg font-bold mb-2">Recipe Auto-Shopper</h4>
                <p className="text-sm text-muted-foreground mb-4">Generate TMM/GEB baskets based on active recipe vs inventory.</p>
                <div className="p-4 border border-dashed border-white/10 rounded-xl text-center">
                    Select a recipe in "Recipes" tab to enable.
                </div>
            </div>

            {/* Create Brew Log */}
            <div className="bg-card/50 p-6 rounded-2xl border border-emerald-500/20">
                <h4 className="text-lg font-bold mb-2 flex items-center gap-2">
                    <ExternalLink className="w-5 h-5 text-emerald-400" /> GitHub Brew Log
                </h4>
                <p className="text-sm text-muted-foreground mb-4">Create a new brew log entry in your GitHub repository.</p>
                <button
                    onClick={async () => {
                        if (!confirm('Create GitHub Brew Log?')) return;
                        try {
                            const res = await fetch('/api/automation/logger/create', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({
                                    name: 'Brew Log (Auto)',
                                    batch: { og: 1.050, fg: 1.010, volume: 23, time: 60 },
                                    water: { name: 'Default', calcium: 80, chloride: 100, sulfate: 50 }
                                })
                            });
                            const data = await res.json();
                            alert(data.message || data.error || 'Log created');
                        } catch (e: any) {
                            alert('Error: ' + e.message);
                        }
                    }}
                    className="px-6 py-3 bg-emerald-500 text-white font-bold rounded-xl hover:bg-emerald-600 transition-colors"
                >
                    Create Brew Log
                </button>
            </div>
        </div>
    );
}
