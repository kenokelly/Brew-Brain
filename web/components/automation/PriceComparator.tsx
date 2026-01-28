'use client';

import { useState, useEffect } from 'react';
import { Scale, TrendingDown, Award, RefreshCw } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ComparisonItem {
    name: string;
    amount?: string;
    tmm_price: number | string | null;
    geb_price: number | string | null;
    tmm_cost?: number | string;
    geb_cost?: number | string;
    best_vendor?: 'TMM' | 'GEB' | 'Tie' | 'None';
}

interface ComparisonResult {
    breakdown?: ComparisonItem[];
    total_tmm: number | string;
    total_geb: number | string;
    winner: string;
    error?: string;
}

interface Recipe {
    _id: string;
    name: string;
}

export function PriceComparator() {
    const [recipes, setRecipes] = useState<Recipe[]>([]);
    const [selectedRecipe, setSelectedRecipe] = useState('');
    const [result, setResult] = useState<ComparisonResult | null>(null);
    const [loading, setLoading] = useState(false);
    const [loadingRecipes, setLoadingRecipes] = useState(true);

    useEffect(() => {
        fetchRecipes();
    }, []);

    const fetchRecipes = async () => {
        setLoadingRecipes(true);
        try {
            const res = await fetch('/api/automation/brewfather/recipes');
            const data = await res.json();
            if (Array.isArray(data)) {
                setRecipes(data);
            }
        } catch (e) {
            console.error('Failed to fetch recipes:', e);
        } finally {
            setLoadingRecipes(false);
        }
    };

    const runComparison = async () => {
        if (!selectedRecipe) return;
        setLoading(true);
        setResult(null);

        try {
            const res = await fetch('/api/automation/sourcing/compare', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ recipe_id: selectedRecipe })
            });
            const data = await res.json();

            if (data.error) {
                setResult({ breakdown: [], total_tmm: 0, total_geb: 0, winner: '', error: data.error });
            } else {
                setResult(data);
            }
        } catch (e: any) {
            setResult({ breakdown: [], total_tmm: 0, total_geb: 0, winner: '', error: e.message });
        } finally {
            setLoading(false);
        }
    };

    const formatPrice = (price: number | string | null | undefined) => {
        if (price === null || price === undefined || price === 'N/A' || price === '?') return 'N/A';
        const num = typeof price === 'string' ? parseFloat(price) : price;
        if (isNaN(num)) return 'N/A';
        return `£${num.toFixed(2)}`;
    };

    return (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4">
            <div className="bg-card/50 p-6 rounded-2xl border border-white/5">
                <h3 className="text-xl font-bold mb-4 flex items-center gap-2">
                    <Scale className="w-6 h-6 text-emerald-400" />
                    Recipe Price Comparison (TMM vs GEB)
                </h3>

                <div className="flex gap-4 items-end">
                    <div className="flex-1">
                        <label className="block text-sm text-muted-foreground mb-2">Select Brewfather Recipe</label>
                        <select
                            value={selectedRecipe}
                            onChange={(e) => setSelectedRecipe(e.target.value)}
                            disabled={loadingRecipes}
                            className="w-full p-3 rounded-xl bg-secondary/30 border border-border/50 text-lg"
                        >
                            <option value="">
                                {loadingRecipes ? 'Loading recipes...' : 'Select a recipe...'}
                            </option>
                            {recipes.map((r) => (
                                <option key={r._id} value={r._id}>
                                    {r.name}
                                </option>
                            ))}
                        </select>
                    </div>
                    <button
                        onClick={runComparison}
                        disabled={!selectedRecipe || loading}
                        className="px-8 py-3 bg-emerald-500 hover:bg-emerald-600 text-white font-bold rounded-xl transition-colors disabled:opacity-50 flex items-center gap-2"
                    >
                        {loading ? (
                            <>
                                <RefreshCw className="w-4 h-4 animate-spin" />
                                Comparing...
                            </>
                        ) : (
                            'Compare Prices'
                        )}
                    </button>
                </div>
            </div>

            {result?.error && (
                <div className="p-4 bg-red-500/10 text-red-400 rounded-xl border border-red-500/20">
                    {result.error}
                </div>
            )}

            {result && !result.error && (
                <div className="space-y-4 animate-in fade-in zoom-in-95">
                    {/* Total Comparison Cards */}
                    <div className="grid grid-cols-2 gap-4">
                        <div className={cn(
                            "p-6 rounded-2xl border text-center transition-all",
                            result.winner === 'TMM'
                                ? "bg-emerald-500/10 border-emerald-500/30"
                                : "bg-black/20 border-white/5"
                        )}>
                            <div className="text-sm text-muted-foreground mb-1">The Malt Miller</div>
                            <div className="text-3xl font-bold text-white">
                                {formatPrice(result.total_tmm)}
                            </div>
                            {result.winner === 'TMM' && (
                                <div className="mt-2 flex items-center justify-center gap-1 text-emerald-400 text-sm">
                                    <Award className="w-4 h-4" /> WINNER
                                </div>
                            )}
                        </div>
                        <div className={cn(
                            "p-6 rounded-2xl border text-center transition-all",
                            result.winner === 'GEB'
                                ? "bg-emerald-500/10 border-emerald-500/30"
                                : "bg-black/20 border-white/5"
                        )}>
                            <div className="text-sm text-muted-foreground mb-1">Get Er Brewed</div>
                            <div className="text-3xl font-bold text-white">
                                {formatPrice(result.total_geb)}
                            </div>
                            {result.winner === 'GEB' && (
                                <div className="mt-2 flex items-center justify-center gap-1 text-emerald-400 text-sm">
                                    <Award className="w-4 h-4" /> WINNER
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Savings Banner */}
                    {result.winner && typeof result.total_tmm === 'number' && typeof result.total_geb === 'number' && result.total_tmm > 0 && result.total_geb > 0 && (
                        <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-xl p-4 text-center">
                            <span className="text-muted-foreground">You save </span>
                            <span className="text-emerald-400 font-bold text-lg">
                                £{Math.abs(result.total_tmm - result.total_geb).toFixed(2)}
                            </span>
                            <span className="text-muted-foreground"> with {result.winner}</span>
                        </div>
                    )}

                    {/* Item Breakdown Table */}
                    <div className="bg-black/20 rounded-2xl border border-white/5 overflow-hidden">
                        <table className="w-full text-sm">
                            <thead className="bg-white/5">
                                <tr className="text-left text-muted-foreground">
                                    <th className="p-4">Ingredient</th>
                                    <th className="p-4 text-right">TMM</th>
                                    <th className="p-4 text-right">GEB</th>
                                    <th className="p-4 text-center">Best</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-white/5">
                                {(result.breakdown || []).map((item: ComparisonItem, i: number) => (
                                    <tr key={i} className="hover:bg-white/5 transition-colors">
                                        <td className="p-4 font-medium">{item.name} {item.amount && <span className="text-xs text-muted-foreground">({item.amount})</span>}</td>
                                        <td className={cn(
                                            "p-4 text-right font-mono",
                                            item.best_vendor === 'TMM' && "text-emerald-400"
                                        )}>
                                            {formatPrice(item.tmm_price)}
                                        </td>
                                        <td className={cn(
                                            "p-4 text-right font-mono",
                                            item.best_vendor === 'GEB' && "text-emerald-400"
                                        )}>
                                            {formatPrice(item.geb_price)}
                                        </td>
                                        <td className="p-4 text-center">
                                            <span className={cn(
                                                "px-2 py-1 rounded text-xs font-bold",
                                                item.best_vendor === 'TMM' && "bg-blue-500/20 text-blue-400",
                                                item.best_vendor === 'GEB' && "bg-purple-500/20 text-purple-400",
                                                item.best_vendor === 'Tie' && "bg-gray-500/20 text-gray-400",
                                                item.best_vendor === 'None' && "bg-gray-500/20 text-gray-400"
                                            )}>
                                                {item.best_vendor || 'N/A'}
                                            </span>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {!result && !loading && (
                <div className="py-16 text-center text-muted-foreground border-2 border-dashed border-white/5 rounded-3xl">
                    <TrendingDown className="w-12 h-12 mx-auto mb-4 opacity-50" />
                    <p>Select a recipe and compare prices to find the best deals.</p>
                </div>
            )}
        </div>
    );
}
