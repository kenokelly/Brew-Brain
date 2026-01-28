'use client';

import { useState, useRef } from 'react';
import { Search, ExternalLink, FileJson, Brain, Wand2, Upload, AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

interface RecipeResult {
    name: string;
    og: number;
    ibu: number;
    abv: string;
    batch_size_l: number;
    style?: string;
    hops_summary?: string;
    grain_breakdown?: string[];
    est_ph?: string;
    target_ph?: string;
    hardware_valid?: boolean;
    hardware_warnings?: string[];
    source_url?: string;
    is_scaled?: boolean;
}

interface AnalysisResult {
    count: number;
    avg_og: number;
    avg_ibu: number;
    avg_abv: string;
    common_hops: Record<string, number>;
    common_dry_hops?: Record<string, number>;
    common_malts: Record<string, number>;
    recipes: RecipeResult[];
}

export function Recipes() {
    const [query, setQuery] = useState('');
    const [results, setResults] = useState<RecipeResult[]>([]);
    const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [auditResults, setAuditResults] = useState<Record<string, any>>({});
    const fileInputRef = useRef<HTMLInputElement>(null);

    const handleSearch = async () => {
        if (!query.trim()) return;
        setLoading(true);
        setError(null);
        setResults([]);
        setAnalysis(null);

        try {
            const res = await fetch('/api/automation/recipes', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: query.trim() })
            });
            const data = await res.json();

            if (data.error) {
                setError(data.error);
            } else if (Array.isArray(data)) {
                setResults(data);
            }
        } catch (e: any) {
            setError(e.message || 'Search failed');
        } finally {
            setLoading(false);
        }
    };

    const handleXmlAnalysis = async () => {
        if (!query.trim()) return;
        setLoading(true);
        setError(null);
        setAnalysis(null);
        setResults([]);

        try {
            const res = await fetch('/api/automation/recipes/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: query.trim() })
            });
            const data = await res.json();

            if (data.error) {
                setError(data.error);
            } else {
                setAnalysis(data);
            }
        } catch (e: any) {
            setError(e.message || 'Analysis failed');
        } finally {
            setLoading(false);
        }
    };

    const runAiAudit = async (recipe: RecipeResult) => {
        const key = recipe.name.replace(/\s/g, '');
        setAuditResults(prev => ({ ...prev, [key]: { loading: true } }));

        try {
            const res = await fetch('/api/automation/learning/audit', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    style: recipe.style || 'Ale',
                    og: recipe.og,
                    name: recipe.name
                })
            });
            const data = await res.json();
            setAuditResults(prev => ({ ...prev, [key]: data }));
        } catch (e) {
            setAuditResults(prev => ({ ...prev, [key]: { error: 'Audit failed' } }));
        }
    };

    const scaleRecipe = async (recipe: RecipeResult) => {
        try {
            const res = await fetch('/api/automation/recipes/scale', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(recipe)
            });
            const data = await res.json();
            if (!data.error) {
                // Update the recipe in results
                if (analysis) {
                    setAnalysis({
                        ...analysis,
                        recipes: analysis.recipes.map(r =>
                            r.name === recipe.name ? { ...r, ...data } : r
                        )
                    });
                }
            }
        } catch (e) {
            console.error('Scale failed:', e);
        }
    };

    return (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4">
            {/* Search Section */}
            <div className="bg-card/50 p-6 rounded-2xl border border-white/5">
                <h3 className="text-xl font-bold mb-4 flex items-center gap-2">
                    <Search className="w-5 h-5 text-primary" /> Recipe Finder
                </h3>

                <div className="flex gap-4 mb-4">
                    <input
                        type="text"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        placeholder="Search Beer Styles or Names (e.g. Pliny, NEIPA)"
                        className="flex-1 p-3 rounded-xl bg-secondary/30 border border-border/50 text-lg"
                        onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                    />
                </div>

                <div className="flex gap-4">
                    <button
                        onClick={handleSearch}
                        disabled={loading || !query.trim()}
                        className="px-8 py-3 bg-primary text-black font-bold rounded-xl hover:bg-primary/90 transition-colors disabled:opacity-50"
                    >
                        {loading ? 'Searching...' : 'Find Recipes'}
                    </button>
                    <button
                        onClick={handleXmlAnalysis}
                        disabled={loading || !query.trim()}
                        className="px-6 py-3 bg-transparent border border-primary text-primary font-bold rounded-xl hover:bg-primary/10 transition-colors disabled:opacity-50 flex items-center gap-2"
                    >
                        <FileJson className="w-4 h-4" />
                        Analyze BeerXML
                    </button>
                </div>
            </div>

            {error && (
                <div className="p-4 bg-red-500/10 text-red-400 rounded-xl border border-red-500/20">
                    {error}
                </div>
            )}

            {/* Analysis Results */}
            {analysis && (
                <div className="bg-card/50 p-6 rounded-2xl border border-primary/30 animate-in fade-in">
                    <h4 className="text-lg font-bold text-primary mb-4 text-center">
                        XML Consensus ({analysis.count} recipes)
                    </h4>

                    <div className="grid grid-cols-3 gap-4 mb-6">
                        <div className="bg-black/20 p-4 rounded-xl text-center">
                            <div className="text-2xl font-bold text-primary">{analysis.avg_og}</div>
                            <div className="text-xs text-muted-foreground">Avg OG</div>
                        </div>
                        <div className="bg-black/20 p-4 rounded-xl text-center">
                            <div className="text-2xl font-bold text-primary">{analysis.avg_ibu}</div>
                            <div className="text-xs text-muted-foreground">Avg IBU</div>
                        </div>
                        <div className="bg-black/20 p-4 rounded-xl text-center">
                            <div className="text-2xl font-bold text-primary">{analysis.avg_abv}%</div>
                            <div className="text-xs text-muted-foreground">Avg ABV</div>
                        </div>
                    </div>

                    <div className="grid md:grid-cols-3 gap-4 mb-6">
                        <div>
                            <h5 className="text-sm text-muted-foreground mb-2 border-b border-white/10 pb-1">Top Hops</h5>
                            {Object.entries(analysis.common_hops || {}).map(([hop, count]) => (
                                <div key={hop} className="flex justify-between text-sm py-1">
                                    <span>{hop}</span>
                                    <span className="text-muted-foreground">{count}</span>
                                </div>
                            ))}
                        </div>
                        <div>
                            <h5 className="text-sm text-muted-foreground mb-2 border-b border-white/10 pb-1">Top Dry Hops</h5>
                            {Object.entries(analysis.common_dry_hops || {}).map(([hop, count]) => (
                                <div key={hop} className="flex justify-between text-sm py-1 text-amber-400">
                                    <span>{hop}</span>
                                    <span>{count}</span>
                                </div>
                            ))}
                        </div>
                        <div>
                            <h5 className="text-sm text-muted-foreground mb-2 border-b border-white/10 pb-1">Top Malts</h5>
                            {Object.entries(analysis.common_malts || {}).map(([malt, count]) => (
                                <div key={malt} className="flex justify-between text-sm py-1">
                                    <span>{malt}</span>
                                    <span className="text-muted-foreground">{count}</span>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Recipe Cards */}
                    <h4 className="text-lg font-bold text-primary mb-4">Found Recipes</h4>
                    <div className="space-y-4">
                        {analysis.recipes.map((recipe, i) => (
                            <RecipeCard
                                key={i}
                                recipe={recipe}
                                onAudit={() => runAiAudit(recipe)}
                                onScale={() => scaleRecipe(recipe)}
                                auditResult={auditResults[recipe.name.replace(/\s/g, '')]}
                            />
                        ))}
                    </div>
                </div>
            )}

            {/* Simple Search Results */}
            {results.length > 0 && !analysis && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {results.map((r, i) => (
                        <div key={i} className="p-4 bg-black/20 rounded-xl border border-white/5 hover:border-primary/50 transition-colors">
                            <div className="font-bold text-lg">{r.name}</div>
                            <div className="text-sm text-muted-foreground">
                                {r.style} • {r.abv}% ABV • {r.ibu} IBU
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {!analysis && results.length === 0 && !loading && !error && (
                <div className="py-16 text-center text-muted-foreground border-2 border-dashed border-white/5 rounded-3xl">
                    <Search className="w-12 h-12 mx-auto mb-4 opacity-50" />
                    <p>Search for recipes or analyze BeerXML files.</p>
                </div>
            )}
        </div>
    );
}

function RecipeCard({
    recipe,
    onAudit,
    onScale,
    auditResult
}: {
    recipe: RecipeResult;
    onAudit: () => void;
    onScale: () => void;
    auditResult?: any;
}) {
    const key = recipe.name.replace(/\s/g, '');

    return (
        <div className="p-4 bg-black/20 rounded-xl border border-white/5">
            <div className="flex justify-between items-start mb-3">
                <div>
                    <div className="flex items-center gap-2 mb-1">
                        <span className="font-bold text-white">{recipe.name}</span>
                        {recipe.is_scaled && (
                            <span className="text-xs bg-primary text-black px-2 py-0.5 rounded">SCALED</span>
                        )}
                    </div>
                    <div className="text-sm text-muted-foreground">
                        OG: <b>{recipe.og}</b> | IBU: <b>{recipe.ibu}</b> | ABV: <b>{recipe.abv}%</b> | Vol: <b>{recipe.batch_size_l}L</b>
                    </div>
                </div>

                <div className="flex gap-2">
                    {!recipe.hardware_valid && (
                        <button
                            onClick={onScale}
                            className="px-3 py-1.5 text-xs font-bold rounded-lg bg-amber-500 text-black hover:bg-amber-400"
                        >
                            <Wand2 className="w-3 h-3 inline mr-1" /> Fit G40
                        </button>
                    )}
                    <button
                        onClick={onAudit}
                        className="px-3 py-1.5 text-xs font-bold rounded-lg bg-gradient-to-r from-indigo-500 to-purple-500 text-white"
                    >
                        <Brain className="w-3 h-3 inline mr-1" /> AI Audit
                    </button>
                    {recipe.source_url && (
                        <button
                            onClick={async () => {
                                try {
                                    const res = await fetch('/api/automation/brewfather/import', {
                                        method: 'POST',
                                        headers: { 'Content-Type': 'application/json' },
                                        body: JSON.stringify({ url: recipe.source_url, name: recipe.name })
                                    });
                                    const data = await res.json();
                                    alert(data.message || data.error || 'Imported!');
                                } catch (e: any) {
                                    alert('Import failed: ' + e.message);
                                }
                            }}
                            className="px-3 py-1.5 text-xs font-bold rounded-lg bg-emerald-500 text-white hover:bg-emerald-600"
                        >
                            <Upload className="w-3 h-3 inline mr-1" /> Import
                        </button>
                    )}
                </div>
            </div>

            {recipe.grain_breakdown && (
                <div className="text-sm text-muted-foreground mb-2">
                    🌾 {recipe.grain_breakdown.join(' | ')}
                </div>
            )}
            {recipe.hops_summary && (
                <div className="text-sm text-muted-foreground">
                    🌿 {recipe.hops_summary}
                </div>
            )}

            {!recipe.hardware_valid && recipe.hardware_warnings && (
                <div className="mt-2 text-sm text-red-400 flex items-center gap-1">
                    <AlertCircle className="w-4 h-4" />
                    {recipe.hardware_warnings.join(' ')}
                </div>
            )}

            {auditResult && !auditResult.loading && (
                <div className="mt-3 p-3 bg-white/5 rounded-lg border-l-2 border-primary">
                    {auditResult.error ? (
                        <span className="text-red-400">{auditResult.error}</span>
                    ) : auditResult.status === 'No Data' ? (
                        <span className="text-muted-foreground">{auditResult.message}</span>
                    ) : (
                        <>
                            <div className="text-sm font-bold text-primary mb-2">
                                Performance Audit (vs {auditResult.peer_count} {recipe.style}s)
                            </div>
                            {auditResult.tips?.length > 0 ? (
                                auditResult.tips.map((tip: string, i: number) => (
                                    <div key={i} className="text-sm text-muted-foreground">⚠️ {tip}</div>
                                ))
                            ) : (
                                <div className="text-sm text-green-400">✅ Matches your successful profiles!</div>
                            )}
                            <div className="text-xs text-muted-foreground mt-2">
                                Avg OG: {auditResult.avg_peer_og} | Avg Att: {auditResult.avg_peer_att}%
                            </div>
                        </>
                    )}
                </div>
            )}

            {auditResult?.loading && (
                <div className="mt-3 p-3 bg-white/5 rounded-lg text-sm text-muted-foreground">
                    Auditing history...
                </div>
            )}
        </div>
    );
}
