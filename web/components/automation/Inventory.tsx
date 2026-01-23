'use client';

import { useState, useEffect } from 'react';
import { RefreshCw, Save, Package } from 'lucide-react';
import { cn } from '@/lib/utils';

export function Inventory() {
    const [inventory, setInventory] = useState<any>(null);
    const [loading, setLoading] = useState(false);
    const [syncing, setSyncing] = useState(false);
    const [activeCategory, setActiveCategory] = useState<'hops' | 'fermentables' | 'yeast' | 'miscs'>('hops');

    useEffect(() => {
        fetchInventory();
    }, []);

    const fetchInventory = async () => {
        setLoading(true);
        try {
            const res = await fetch('/api/automation/inventory');
            const data = await res.json();
            setInventory(data);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    const handleSync = async () => {
        setSyncing(true);
        try {
            const res = await fetch('/api/automation/inventory/sync', { method: 'POST' });
            const data = await res.json();
            if (data.inventory) setInventory(data.inventory);
        } catch (e) {
            console.error(e);
        } finally {
            setSyncing(false);
        }
    };

    const getItems = () => {
        if (!inventory) return [];
        // Map Brewfather categories to our keys if needed
        // Assuming API returns structure { hops: [], fermentables: [], ... }
        return inventory[activeCategory] || [];
    };

    return (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4">
            <div className="flex justify-between items-center bg-card/50 p-6 rounded-2xl border border-white/5">
                <div>
                    <h3 className="text-xl font-bold flex items-center gap-2">
                        <Package className="w-6 h-6 text-primary" /> Inventory
                    </h3>
                    <p className="text-sm text-muted-foreground">Manage stock via Brewfather Sync</p>
                </div>
                <button
                    onClick={handleSync}
                    disabled={syncing}
                    className="flex items-center gap-2 px-4 py-2 bg-primary/10 text-primary border border-primary/20 rounded-xl hover:bg-primary/20 transition-colors disabled:opacity-50"
                >
                    <RefreshCw className={cn("w-4 h-4", syncing && "animate-spin")} />
                    {syncing ? 'Syncing...' : 'Sync Brewfather'}
                </button>
            </div>

            {/* Category Tabs */}
            <div className="flex gap-2 overflow-x-auto pb-2">
                {['hops', 'fermentables', 'yeast', 'miscs'].map((cat) => (
                    <button
                        key={cat}
                        onClick={() => setActiveCategory(cat as any)}
                        className={cn(
                            "px-6 py-2 rounded-full border text-sm font-medium capitalize transition-all",
                            activeCategory === cat
                                ? "bg-primary text-primary-foreground border-primary"
                                : "bg-secondary/20 border-white/5 hover:bg-secondary/40 text-muted-foreground"
                        )}
                    >
                        {cat}
                    </button>
                ))}
            </div>

            {/* Items Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {loading ? (
                    <div className="col-span-full py-12 text-center text-muted-foreground">Loading inventory...</div>
                ) : getItems().length > 0 ? (
                    getItems().map((item: any, i: number) => (
                        <div key={i} className="p-4 bg-black/20 rounded-xl border border-white/5 flex justify-between items-center group hover:border-white/10 transition-colors">
                            <div>
                                <div className="font-bold">{item.name}</div>
                                <div className="text-xs text-muted-foreground">{item.origin} {item.alpha ? `• ${item.alpha}% AA` : ''}</div>
                            </div>
                            <div className="text-right">
                                <div className={cn("text-lg font-mono font-bold", item.amount > 0 ? "text-primary" : "text-red-500")}>
                                    {item.amount} {item.unit || 'g'}
                                </div>
                            </div>
                        </div>
                    ))
                ) : (
                    <div className="col-span-full py-12 text-center text-muted-foreground border-2 border-dashed border-white/5 rounded-2xl">
                        No items found in {activeCategory}. Sync to populate.
                    </div>
                )}
            </div>
        </div>
    );
}
