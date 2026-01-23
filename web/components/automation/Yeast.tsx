'use client';

import { useState } from 'react';
import { Search, Beaker, Thermometer, Activity, ExternalLink } from 'lucide-react';

interface YeastData {
    name: string;
    url: string;
    attenuation: string;
    flocculation: string;
    temp_range: string;
    abv_tolerance: string;
    error?: string;
}

export function Yeast() {
    const [query, setQuery] = useState('');
    const [result, setResult] = useState<YeastData | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleSearch = async () => {
        if (!query.trim()) return;
        setLoading(true);
        setError(null);
        setResult(null);

        try {
            const res = await fetch('/api/automation/yeast/search', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: query.trim() })
            });
            const data = await res.json();

            if (data.error) {
                setError(data.error);
            } else {
                setResult(data);
            }
        } catch (e: any) {
            setError(e.message || 'Failed to search');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4">
            <div className="bg-card/50 p-6 rounded-2xl border border-white/5">
                <h3 className="text-xl font-bold mb-4 flex items-center gap-2">
                    <Beaker className="w-6 h-6 text-pink-400" />
                    Yeast Metadata Scraper
                </h3>
                <p className="text-muted-foreground mb-4">
                    Enter a yeast strain (e.g. WLP001, US-05, Imperial A38) to fetch attenuation, flocculation, and temperature ranges from manufacturer websites.
                </p>

                <div className="flex gap-4">
                    <div className="relative flex-1">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground w-4 h-4" />
                        <input
                            type="text"
                            value={query}
                            onChange={(e) => setQuery(e.target.value)}
                            placeholder="e.g. WLP001"
                            className="w-full pl-10 pr-4 py-3 rounded-xl bg-secondary/30 border border-border/50 focus:outline-none focus:ring-2 focus:ring-pink-500/50"
                            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                        />
                    </div>
                    <button
                        onClick={handleSearch}
                        disabled={loading || !query.trim()}
                        className="px-6 py-3 bg-pink-500 hover:bg-pink-600 text-white font-bold rounded-xl transition-colors disabled:opacity-50"
                    >
                        {loading ? 'Searching...' : 'Scrape'}
                    </button>
                </div>
            </div>

            {error && (
                <div className="p-4 bg-red-500/10 text-red-400 rounded-xl border border-red-500/20">
                    {error}
                </div>
            )}

            {result && !result.error && (
                <div className="bg-card/50 p-6 rounded-2xl border border-white/5 animate-in fade-in zoom-in-95">
                    <div className="flex justify-between items-start mb-6">
                        <div>
                            <h4 className="text-xl font-bold text-white">{result.name}</h4>
                            {result.url && (
                                <a
                                    href={result.url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-sm text-pink-400 hover:underline flex items-center gap-1 mt-1"
                                >
                                    View Source <ExternalLink className="w-3 h-3" />
                                </a>
                            )}
                        </div>
                    </div>

                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <div className="bg-black/20 p-4 rounded-xl text-center">
                            <Activity className="w-5 h-5 mx-auto mb-2 text-pink-400" />
                            <div className="text-2xl font-bold text-white">{result.attenuation}</div>
                            <div className="text-xs text-muted-foreground uppercase mt-1">Attenuation</div>
                        </div>
                        <div className="bg-black/20 p-4 rounded-xl text-center">
                            <div className="w-5 h-5 mx-auto mb-2 text-pink-400 flex items-center justify-center font-bold">F</div>
                            <div className="text-2xl font-bold text-white">{result.flocculation}</div>
                            <div className="text-xs text-muted-foreground uppercase mt-1">Flocculation</div>
                        </div>
                        <div className="bg-black/20 p-4 rounded-xl text-center">
                            <Thermometer className="w-5 h-5 mx-auto mb-2 text-pink-400" />
                            <div className="text-2xl font-bold text-white">{result.temp_range}</div>
                            <div className="text-xs text-muted-foreground uppercase mt-1">Temp Range</div>
                        </div>
                        <div className="bg-black/20 p-4 rounded-xl text-center">
                            <div className="w-5 h-5 mx-auto mb-2 text-pink-400 flex items-center justify-center font-bold">%</div>
                            <div className="text-2xl font-bold text-white">{result.abv_tolerance}</div>
                            <div className="text-xs text-muted-foreground uppercase mt-1">ABV Tolerance</div>
                        </div>
                    </div>
                </div>
            )}

            {!result && !loading && !error && (
                <div className="py-16 text-center text-muted-foreground border-2 border-dashed border-white/5 rounded-3xl">
                    <Beaker className="w-12 h-12 mx-auto mb-4 opacity-50" />
                    <p>Enter a yeast strain to fetch metadata from manufacturer sites.</p>
                </div>
            )}
        </div>
    );
}
