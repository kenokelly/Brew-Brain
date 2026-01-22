'use client';

import { useState } from 'react';
import { Search, ExternalLink, Star } from 'lucide-react';
import { cn } from '@/lib/utils';

export function Scout() {
    const [query, setQuery] = useState('');
    const [results, setResults] = useState<any[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleSearch = async () => {
        if (!query) return;
        setLoading(true);
        setError(null);
        try {
            const res = await fetch('/api/automation/scout', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query })
            });
            const data = await res.json();
            if (data.error) throw new Error(data.error);
            setResults(data);
        } catch (e: any) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="space-y-6">
            <div className="flex gap-4">
                <div className="relative flex-1">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground w-4 h-4" />
                    <input
                        type="text"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        placeholder="Search ingredients (e.g. Citra Hops)"
                        className="w-full pl-10 pr-4 py-3 rounded-xl bg-secondary/30 border border-border/50 focus:outline-none focus:ring-2 focus:ring-primary/50"
                        onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                    />
                </div>
                <button
                    onClick={handleSearch}
                    disabled={loading}
                    className="px-6 py-3 bg-primary text-primary-foreground font-semibold rounded-xl hover:opacity-90 transition-opacity disabled:opacity-50"
                >
                    {loading ? 'Searching...' : 'Scout'}
                </button>
            </div>

            {error && <div className="p-4 bg-red-500/10 text-red-500 rounded-xl border border-red-500/20">{error}</div>}

            <div className="space-y-3">
                {results.map((item, i) => (
                    <div key={i} className="flex items-center justify-between p-4 rounded-xl bg-card border border-border/50 hover:bg-secondary/20 transition-colors group">
                        <div className="flex flex-col gap-1">
                            <div className="flex items-center gap-2">
                                {item.is_preferred && <Star className="w-4 h-4 text-amber-500 fill-amber-500" />}
                                <a href={item.link} target="_blank" rel="noopener noreferrer" className="font-semibold hover:text-primary transition-colors flex items-center gap-2">
                                    {item.title}
                                    <ExternalLink className="w-3 h-3 opacity-0 group-hover:opacity-50" />
                                </a>
                            </div>
                            <span className="text-xs text-muted-foreground">{item.source}</span>
                        </div>
                        <div className="font-mono font-bold text-primary">{item.price}</div>
                    </div>
                ))}
                {results.length === 0 && !loading && !error && (
                    <div className="text-center text-muted-foreground py-10">No results yet. Try searching.</div>
                )}
            </div>
        </div>
    );
}
