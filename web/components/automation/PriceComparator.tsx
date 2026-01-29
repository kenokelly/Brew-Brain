'use client';

import { useState, useEffect } from 'react';
import { Scale, TrendingDown, Award, RefreshCw, AlertTriangle } from 'lucide-react';
import { cn } from '@/lib/utils';

// ============================================
// TYPE DEFINITIONS WITH STRICT SCHEMA
// ============================================

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
    stack_trace?: string;
    debug_info?: string;
}

interface Recipe {
    _id: string;
    name: string;
}

// ============================================
// SAFE FETCH UTILITIES
// ============================================

/**
 * Safely fetches JSON from an API endpoint with comprehensive error handling.
 * Validates response status, content-type, and JSON parsing before returning.
 */
async function safeFetchJson<T>(
    url: string,
    options?: RequestInit
): Promise<{ data: T | null; error: string | null; rawText?: string }> {
    try {
        const res = await fetch(url, options);

        // 1. Check HTTP status
        if (!res.ok) {
            // Try to get error details from response body
            let errorDetails = '';
            try {
                const text = await res.text();
                // If it's JSON with an error field, extract it
                if (text.startsWith('{')) {
                    const json = JSON.parse(text);
                    errorDetails = json.error || json.message || text.substring(0, 200);
                } else {
                    errorDetails = text.substring(0, 200);
                }
            } catch {
                errorDetails = `HTTP ${res.status}`;
            }

            return {
                data: null,
                error: `Server error (${res.status}): ${errorDetails}`,
                rawText: errorDetails
            };
        }

        // 2. Check Content-Type header
        const contentType = res.headers.get('content-type') || '';
        if (!contentType.includes('application/json')) {
            const text = await res.text();
            console.warn('[safeFetchJson] Non-JSON response:', text.substring(0, 500));
            return {
                data: null,
                error: `Expected JSON but received ${contentType || 'unknown content type'}`,
                rawText: text.substring(0, 200)
            };
        }

        // 3. Parse JSON safely
        const text = await res.text();
        if (!text || text.trim() === '') {
            return {
                data: null,
                error: 'Empty response from server'
            };
        }

        let data: T;
        try {
            data = JSON.parse(text);
        } catch (parseError: any) {
            console.error('[safeFetchJson] JSON parse error:', parseError.message, 'Raw:', text.substring(0, 200));
            return {
                data: null,
                error: `Invalid JSON response: ${parseError.message}`,
                rawText: text.substring(0, 200)
            };
        }

        return { data, error: null };

    } catch (networkError: any) {
        console.error('[safeFetchJson] Network error:', networkError);
        return {
            data: null,
            error: `Network error: ${networkError.message || 'Failed to connect'}`
        };
    }
}

/**
 * Validates that a ComparisonResult has the expected schema.
 * Returns a sanitized result with defaults for missing fields.
 */
function validateComparisonResult(data: any): ComparisonResult {
    // Handle explicit error from backend
    if (data?.error) {
        return {
            breakdown: [],
            total_tmm: 0,
            total_geb: 0,
            winner: '',
            error: String(data.error)
        };
    }

    // Validate breakdown array
    let breakdown: ComparisonItem[] = [];
    if (Array.isArray(data?.breakdown)) {
        breakdown = data.breakdown.map((item: any) => ({
            name: String(item?.name || 'Unknown'),
            amount: item?.amount ? String(item.amount) : undefined,
            tmm_price: sanitizePrice(item?.tmm_price),
            geb_price: sanitizePrice(item?.geb_price),
            tmm_cost: item?.tmm_cost,
            geb_cost: item?.geb_cost,
            best_vendor: validateVendor(item?.best_vendor)
        }));
    }

    // Validate totals - can be number or string like "Inc" (Inconclusive)
    const total_tmm = sanitizeTotal(data?.total_tmm);
    const total_geb = sanitizeTotal(data?.total_geb);

    // Validate winner
    const winner = typeof data?.winner === 'string' ? data.winner : '';

    return {
        breakdown,
        total_tmm,
        total_geb,
        winner,
        error: undefined
    };
}

function sanitizePrice(value: any): number | string | null {
    if (value === null || value === undefined) return null;
    if (value === 'N/A' || value === '?') return value;
    if (typeof value === 'number') return value;
    if (typeof value === 'string') {
        const num = parseFloat(value);
        return isNaN(num) ? value : num;
    }
    return null;
}

function sanitizeTotal(value: any): number | string {
    if (typeof value === 'number') return value;
    if (typeof value === 'string') {
        const num = parseFloat(value);
        return isNaN(num) ? value : num;
    }
    return 0;
}

function validateVendor(value: any): 'TMM' | 'GEB' | 'Tie' | 'None' {
    if (value === 'TMM' || value === 'GEB' || value === 'Tie') return value;
    return 'None';
}

// ============================================
// MAIN COMPONENT
// ============================================

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

        const { data, error } = await safeFetchJson<Recipe[]>('/api/automation/brewfather/recipes');

        if (error) {
            console.error('[PriceComparator] Failed to fetch recipes:', error);
            // Don't show error for recipes - just leave dropdown empty
        } else if (Array.isArray(data)) {
            setRecipes(data);
        }

        setLoadingRecipes(false);
    };

    const runComparison = async () => {
        if (!selectedRecipe) return;

        setLoading(true);
        setResult(null);

        const { data, error, rawText } = await safeFetchJson<any>(
            '/api/automation/sourcing/compare',
            {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ recipe_id: selectedRecipe })
            }
        );

        if (error) {
            // Create a user-friendly error result
            setResult({
                breakdown: [],
                total_tmm: 0,
                total_geb: 0,
                winner: '',
                error: error,
                debug_info: rawText
            });
        } else if (data) {
            // Validate and sanitize the response
            const validated = validateComparisonResult(data);
            setResult(validated);
        } else {
            setResult({
                breakdown: [],
                total_tmm: 0,
                total_geb: 0,
                winner: '',
                error: 'No data received from server'
            });
        }

        setLoading(false);
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

            {/* Error Display with Stack Trace */}
            {result?.error && (
                <div className="p-4 bg-red-500/10 text-red-400 rounded-xl border border-red-500/20">
                    <div className="flex items-start gap-3">
                        <AlertTriangle className="w-5 h-5 mt-0.5 flex-shrink-0" />
                        <div className="flex-1">
                            <div className="font-medium">{result.error}</div>
                            {result.stack_trace && (
                                <details className="mt-2" open>
                                    <summary className="text-xs cursor-pointer opacity-80 hover:opacity-100 font-bold text-yellow-400">
                                        📍 STACK TRACE (Line numbers)
                                    </summary>
                                    <pre className="mt-2 text-xs bg-black/50 p-3 rounded overflow-x-auto whitespace-pre-wrap font-mono border border-red-500/30">
                                        {result.stack_trace}
                                    </pre>
                                </details>
                            )}
                            {result.debug_info && !result.stack_trace && (
                                <details className="mt-2">
                                    <summary className="text-xs cursor-pointer opacity-60 hover:opacity-100">
                                        Show debug info
                                    </summary>
                                    <pre className="mt-2 text-xs bg-black/30 p-2 rounded overflow-x-auto">
                                        {result.debug_info}
                                    </pre>
                                </details>
                            )}
                        </div>
                    </div>
                </div>
            )}

            {result && !result.error && (
                <div className="space-y-4 animate-in fade-in zoom-in-95">
                    {/* Total Comparison Cards */}
                    <div className="grid grid-cols-2 gap-4">
                        <div className={cn(
                            "p-6 rounded-2xl border text-center transition-all",
                            result.winner === 'The Malt Miller' || result.winner === 'TMM'
                                ? "bg-emerald-500/10 border-emerald-500/30"
                                : "bg-black/20 border-white/5"
                        )}>
                            <div className="text-sm text-muted-foreground mb-1">The Malt Miller</div>
                            <div className="text-3xl font-bold text-white">
                                {formatPrice(result.total_tmm)}
                            </div>
                            {(result.winner === 'The Malt Miller' || result.winner === 'TMM') && (
                                <div className="mt-2 flex items-center justify-center gap-1 text-emerald-400 text-sm">
                                    <Award className="w-4 h-4" /> WINNER
                                </div>
                            )}
                        </div>
                        <div className={cn(
                            "p-6 rounded-2xl border text-center transition-all",
                            result.winner === 'Get Er Brewed' || result.winner === 'GEB'
                                ? "bg-emerald-500/10 border-emerald-500/30"
                                : "bg-black/20 border-white/5"
                        )}>
                            <div className="text-sm text-muted-foreground mb-1">Get Er Brewed</div>
                            <div className="text-3xl font-bold text-white">
                                {formatPrice(result.total_geb)}
                            </div>
                            {(result.winner === 'Get Er Brewed' || result.winner === 'GEB') && (
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
                    {result.breakdown && result.breakdown.length > 0 && (
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
                                    {result.breakdown.map((item: ComparisonItem, i: number) => (
                                        <tr key={i} className="hover:bg-white/5 transition-colors">
                                            <td className="p-4 font-medium">
                                                {item.name}
                                                {item.amount && <span className="text-xs text-muted-foreground ml-1">({item.amount})</span>}
                                            </td>
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
                    )}
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
