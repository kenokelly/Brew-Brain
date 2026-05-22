'use client';

import { useState } from 'react';
import { ShoppingCart, Search, ExternalLink, Loader2, AlertCircle, CheckCircle } from 'lucide-react';

export function Sourcing() {
    const [query, setQuery] = useState('');
    const [results, setResults] = useState<any[]>([]);
    const [loading, setLoading] = useState(false);
    
    const [deficitInput, setDeficitInput] = useState('{"hops": [{"name": "Citra", "deficit_g": 100}], "fermentables": [{"name": "Maris Otter", "deficit_kg": 5}]}');
    const [basket, setBasket] = useState<any>(null);
    const [basketLoading, setBasketLoading] = useState(false);
    const [basketError, setBasketError] = useState('');

    const search = async () => {
        if (!query) return;
        setLoading(true);
        try {
            const res = await fetch('/api/automation/scout', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query })
            });
            const data = await res.json();
            setResults(Array.isArray(data.data) ? data.data : []);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    const sourceBasket = async () => {
        setBasketLoading(true);
        setBasketError('');
        setBasket(null);
        try {
            const parsedDeficit = JSON.parse(deficitInput);
            const res = await fetch('/api/automation/source', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ deficit: parsedDeficit, preferred_vendors: ["The Malt Miller"] })
            });
            const data = await res.json();
            if (data.status === 'error') {
                setBasketError(data.error);
            } else {
                setBasket(data.data);
            }
        } catch (e: any) {
            setBasketError('Failed to parse input or fetch data: ' + e.message);
        } finally {
            setBasketLoading(false);
        }
    };

    return (
        <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4">
            
            {/* Price Tracker Dashboard */}
            <div className="bg-card/50 p-6 rounded-2xl border border-white/5">
                <h3 className="text-xl font-bold mb-4 flex items-center gap-2">
                    <ShoppingCart className="w-5 h-5 text-emerald-400" /> Source Ingredients (Phase 4)
                </h3>
                
                <p className="text-sm text-muted-foreground mb-4">Paste a JSON deficit object to find the cheapest basket across vendors.</p>
                <textarea 
                    className="w-full p-4 bg-black/40 border border-white/10 rounded-xl font-mono text-sm h-32 mb-4"
                    value={deficitInput}
                    onChange={(e) => setDeficitInput(e.target.value)}
                />

                <button
                    onClick={sourceBasket}
                    disabled={basketLoading}
                    className="flex items-center gap-2 px-6 py-3 bg-emerald-500 text-white font-bold rounded-xl hover:bg-emerald-600 transition-colors disabled:opacity-50"
                >
                    {basketLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Search className="w-5 h-5" />}
                    Source Basket
                </button>

                {basketError && (
                    <div className="mt-4 p-4 bg-red-500/20 border border-red-500/50 rounded-xl text-red-200 flex items-center gap-2">
                        <AlertCircle className="w-5 h-5" /> {basketError}
                    </div>
                )}

                {basket && (
                    <div className="mt-6 space-y-4">
                        <div className="flex justify-between items-center bg-white/5 p-4 rounded-xl border border-white/10">
                            <span className="text-lg font-bold">Total Estimated Cost</span>
                            <span className="text-2xl font-black text-emerald-400">£{basket.total_estimated_cost?.toFixed(2)}</span>
                        </div>
                        
                        <div className="space-y-2">
                            <h4 className="font-bold text-muted-foreground uppercase text-xs tracking-wider">Cart Details</h4>
                            {basket.cart?.map((item: any, i: number) => (
                                <div key={i} className="flex flex-col sm:flex-row justify-between items-start sm:items-center p-4 bg-white/5 rounded-xl border border-white/5 gap-4">
                                    <div>
                                        <div className="font-bold flex items-center gap-2">
                                            {item.item} 
                                            {item.vendor === 'The Malt Miller' ? (
                                                <span className="text-[10px] bg-blue-500/20 text-blue-300 px-2 py-0.5 rounded-full border border-blue-500/30">TMM</span>
                                            ) : (
                                                <span className="text-[10px] bg-purple-500/20 text-purple-300 px-2 py-0.5 rounded-full border border-purple-500/30">GEB</span>
                                            )}
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-4">
                                        <div className="font-mono font-bold text-emerald-400">£{item.price?.toFixed(2)}</div>
                                        <a href={item.link} target="_blank" rel="noreferrer" className="p-2 hover:bg-white/10 rounded-lg transition-colors">
                                            <ExternalLink className="w-4 h-4 text-muted-foreground" />
                                        </a>
                                    </div>
                                </div>
                            ))}
                            {basket.cart?.length === 0 && (
                                <div className="p-4 text-center text-muted-foreground border border-dashed border-white/10 rounded-xl">
                                    No items found.
                                </div>
                            )}
                        </div>
                    </div>
                )}
            </div>

            {/* Quick Search */}
            <div className="bg-card/50 p-6 rounded-2xl border border-white/5">
                <h3 className="text-lg font-bold mb-4">Quick Ingredient Search</h3>
                <div className="flex gap-4 mb-6">
                    <input
                        type="text"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        placeholder="e.g. Maris Otter"
                        className="flex-1 p-3 rounded-xl bg-secondary/30 border border-border/50 text-lg"
                        onKeyDown={(e) => e.key === 'Enter' && search()}
                    />
                    <button
                        onClick={search}
                        className="px-6 bg-secondary text-white font-bold rounded-xl hover:bg-secondary/80 transition-colors"
                    >
                        Search
                    </button>
                </div>

                <div className="space-y-2">
                    {loading && <div className="flex justify-center p-4"><Loader2 className="w-6 h-6 animate-spin text-emerald-500" /></div>}
                    {results.map((item, i) => (
                        <div key={i} className="flex justify-between items-center p-3 bg-white/5 rounded-lg border border-white/5">
                            <div>
                                <div className="font-bold">{item.title || item.name}</div>
                                <div className="text-xs text-muted-foreground">{item.source || item.vendor}</div>
                            </div>
                            <div className="font-mono font-bold text-emerald-400">{item.price}</div>
                        </div>
                    ))}
                </div>
            </div>

        </div>
    );
}
