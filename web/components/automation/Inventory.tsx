'use client';

import { useState, useEffect } from 'react';
import { RefreshCw, Package, AlertTriangle, ShoppingCart } from 'lucide-react';
import { cn } from '@/lib/utils';
import BarcodeInventoryScanner from "./BarcodeScanner";

export function Inventory() {
    const [inventory, setInventory] = useState<any>(null);
    const [loading, setLoading] = useState(false);
    const [syncing, setSyncing] = useState(false);
    const [activeCategory, setActiveCategory] = useState<'hops' | 'fermentables' | 'yeast' | 'salts' | 'misc'>('hops');

    useEffect(() => {
        fetchInventory();
    }, []);

    const fetchInventory = async () => {
        setLoading(true);
        try {
            const res = await fetch('/api/automation/inventory');
            const json = await res.json();
            if (json.data) {
                setInventory(json.data);
            }
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
            const json = await res.json();
            if (json.data?.task_id) {
                pollTaskStatus(json.data.task_id);
            } else {
                setSyncing(false);
            }
        } catch (e) {
            console.error(e);
            setSyncing(false);
        }
    };

    const pollTaskStatus = async (taskId: string) => {
        const interval = setInterval(async () => {
            try {
                const res = await fetch(`/api/automation/inventory/sync/status/${taskId}`);
                const json = await res.json();
                
                if (json.data?.status === 'success') {
                    clearInterval(interval);
                    setSyncing(false);
                    fetchInventory(); // Refetch updated inventory
                } else if (json.status === 'error' || json.data?.status === 'FAILURE') {
                    clearInterval(interval);
                    setSyncing(false);
                    console.error("Sync failed:", json.error);
                }
            } catch (e) {
                console.error(e);
                clearInterval(interval);
                setSyncing(false);
            }
        }, 2000);
    };

    const getItems = () => {
        if (!inventory) return [];
        return inventory[activeCategory] || [];
    };
    
    const handleReorder = (item: any) => {
        const amount = item.amount_g || item.amount_kg || item.amount;
        let unit = 'g';
        if (activeCategory === 'fermentables') unit = 'kg';
        else if (activeCategory === 'yeast') unit = 'pkgs';
        else if (activeCategory === 'misc') unit = 'units';

        const deficit = {
            [item.name]: {
                amount: amount,
                unit: unit
            }
        };
        const event = new CustomEvent('reorder-deficit', { detail: deficit });
        window.dispatchEvent(event);
        alert(`Dispatched reorder for ${item.name}. (Check Sourcing Tab)`);
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
                <div className="flex gap-2">
                    <BarcodeInventoryScanner onComplete={fetchInventory} />
                    <button
                        onClick={handleSync}
                        disabled={syncing}
                        className="flex items-center gap-2 px-4 py-2 bg-primary/10 text-primary border border-primary/20 rounded-xl hover:bg-primary/20 transition-colors disabled:opacity-50"
                    >
                        <RefreshCw className={cn("w-4 h-4", syncing && "animate-spin")} />
                        {syncing ? 'Syncing...' : 'Sync Brewfather'}
                    </button>
                </div>
            </div>

            {/* Category Tabs */}
            <div className="flex gap-2 overflow-x-auto pb-2">
                {['hops', 'fermentables', 'yeast', 'salts', 'misc'].map((cat) => (
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
                    <div className="col-span-full py-12 text-center text-muted-foreground flex justify-center items-center gap-2">
                        <RefreshCw className="w-5 h-5 animate-spin"/> Loading inventory...
                    </div>
                ) : getItems().length > 0 ? (
                    getItems().map((item: any, i: number) => (
                        <div key={i} className="p-4 bg-black/20 rounded-xl border border-white/5 flex flex-col justify-between group hover:border-white/10 transition-colors">
                            <div className="flex justify-between items-start mb-4">
                                <div>
                                    <div className="font-bold flex items-center gap-2">
                                        {item.name}
                                        {item.low_stock_alert && (
                                            <span title="Low Stock"><AlertTriangle className="w-4 h-4 text-orange-500" /></span>
                                        )}
                                    </div>
                                    <div className="text-xs text-muted-foreground mt-1 space-y-1">
                                        {item.original_alpha && <div>Alpha: {item.original_alpha}% → <span className="text-orange-400">{item.current_alpha}%</span></div>}
                                        {item.freshness && <div>Freshness: {item.freshness}</div>}
                                    </div>
                                </div>
                                <div className="text-right">
                                    <div className={cn("text-lg font-mono font-bold", item.low_stock_alert ? "text-orange-500" : "text-primary")}>
                                        {item.amount_g || item.amount_kg || item.amount} {activeCategory === 'hops' ? 'g' : (activeCategory === 'fermentables' ? 'kg' : (activeCategory === 'yeast' ? 'pkgs' : 'units'))}
                                    </div>
                                </div>
                            </div>
                            
                            {item.low_stock_alert && (
                                <button 
                                    onClick={() => handleReorder(item)}
                                    className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-orange-500/10 text-orange-500 border border-orange-500/20 rounded-lg hover:bg-orange-500/20 transition-colors text-sm font-medium mt-auto"
                                >
                                    <ShoppingCart className="w-4 h-4" />
                                    Re-order Deficit
                                </button>
                            )}
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
