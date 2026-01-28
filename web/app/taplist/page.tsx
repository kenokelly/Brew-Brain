'use client';

import { useEffect, useState } from 'react';
import { getSrmColor } from '@/lib/beer';
import { cn } from '@/lib/utils';
import { Beer, Droplets, RefreshCw, X, ChevronRight, Activity, Thermometer, ArrowUpRight } from 'lucide-react';
import { fetcher } from '@/lib/hooks';
import toast from 'react-hot-toast';
// Assuming we have these or need to make simple modal
import { PintGlass } from '@/components/PintGlass';

// Since we might not have a UI library, I'll build a custom Modal in-file for simplicity and speed, 
// ensuring strict parity without dependency hell.

interface TapData {
    active: boolean;
    name?: string;
    style?: string;
    notes?: string;
    abv?: number;
    ibu?: number;
    og?: number;
    srm?: number;
    keg_total?: number;
    keg_remaining?: number;
    volume_unit?: string;
}

interface TapsResponse {
    [key: string]: TapData;
}

export default function TapListPage() {
    const [taps, setTaps] = useState<TapsResponse | null>(null);
    const [loading, setLoading] = useState(true);

    const fetchTaps = async () => {
        try {
            const res = await fetch('/api/taps', { cache: 'no-store' });
            if (!res.ok) throw new Error("Failed to fetch taps");
            const data = await res.json();
            setTaps(data);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchTaps();
        const interval = setInterval(fetchTaps, 10000); // Poll every 10s
        return () => clearInterval(interval);
    }, []);

    if (loading && !taps) return <div className="flex h-screen items-center justify-center text-muted-foreground">Loading Taps...</div>;

    const tapKeys = ['tap_1', 'tap_2', 'tap_3', 'tap_4'];

    return (
        <div className="p-8 max-w-7xl mx-auto space-y-8">
            <header className="flex justify-between items-center mb-8">
                <div>
                    <h1 className="text-4xl font-extrabold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-amber-500 to-orange-600">
                        Tap List
                    </h1>
                    <p className="text-muted-foreground mt-1">What's on draft right now.</p>
                </div>
                <button
                    onClick={fetchTaps}
                    className="p-2 rounded-full bg-secondary/50 hover:bg-secondary text-foreground transition-colors"
                >
                    <RefreshCw className="w-5 h-5" />
                </button>
            </header>

            <div className="space-y-4">
                {tapKeys.map((key, index) => {
                    const tap = taps ? taps[key] : null;
                    const isActive = tap?.active;
                    const tapNumber = index + 1;

                    if (!tap) return null;

                    // Calculate Keg Percentage
                    const total = tap.keg_total || 640; // Default 5gal in oz
                    const remaining = tap.keg_remaining !== undefined ? tap.keg_remaining : 0;
                    const percent = Math.max(0, Math.min(100, (remaining / total) * 100));

                    const beerColor = getSrmColor(tap.srm);

                    return (
                        <div
                            key={key}
                            className={cn(
                                "group relative overflow-hidden rounded-3xl border transition-all duration-300",
                                isActive
                                    ? "bg-card/40 backdrop-blur-md border-border/50 hover:bg-card/60 shadow-lg hover:shadow-xl"
                                    : "bg-secondary/10 border-border/10 opacity-70 grayscale hover:grayscale-0"
                            )}
                        >
                            <div className="flex flex-col md:flex-row items-stretch">
                                {/* Tap Number / Status Indicator */}
                                <div className={cn(
                                    "w-full md:w-20 flex items-center justify-center text-2xl font-bold p-4 md:p-0 border-b md:border-b-0 md:border-r border-border/50",
                                    isActive ? "bg-secondary/20 text-foreground" : "bg-muted text-muted-foreground"
                                )}>
                                    {tapNumber}
                                </div>

                                {/* Main Info */}
                                <div className="flex-1 p-6 flex flex-col justify-center">
                                    {isActive ? (
                                        <>
                                            <div className="flex items-center gap-2 mb-1">
                                                <h2 className="text-2xl font-bold tracking-tight">{tap.name}</h2>
                                                <div
                                                    className="w-4 h-4 rounded-full border border-white/20 shadow-inner"
                                                    style={{ backgroundColor: beerColor }}
                                                    title={`SRM: ${tap.srm}`}
                                                />
                                            </div>
                                            <div className="text-lg text-primary font-medium">{tap.style}</div>
                                            {tap.notes && (
                                                <p className="text-sm text-muted-foreground mt-2 line-clamp-2 md:line-clamp-1">{tap.notes}</p>
                                            )}
                                        </>
                                    ) : (
                                        <div className="text-xl font-medium text-muted-foreground flex items-center gap-2">
                                            <Droplets className="w-6 h-6" />
                                            Tap Dry / Unassigned
                                        </div>
                                    )}
                                </div>

                                {/* Stats Badges */}
                                {isActive && (
                                    <div className="p-6 flex flex-wrap gap-2 items-center md:justify-end border-t md:border-t-0 md:border-l border-border/30 bg-black/5 md:bg-transparent md:w-48">
                                        <Badge label="ABV" value={`${tap.abv}%`} color="bg-amber-500/10 text-amber-500 border-amber-500/20" />
                                        <Badge label="IBU" value={tap.ibu} color="bg-emerald-500/10 text-emerald-500 border-emerald-500/20" />
                                        <Badge label="OG" value={tap.og?.toFixed(3)} color="bg-blue-500/10 text-blue-500 border-blue-500/20" />
                                    </div>
                                )}

                                {/* Keg Visual (Right Panel) */}
                                <div className={cn(
                                    "w-full md:w-32 bg-black/20 relative flex flex-col justify-end items-center overflow-hidden h-32 md:h-auto border-t md:border-t-0 md:border-l border-border/50",
                                    !isActive && "hidden md:flex"
                                )}>
                                    {/* Liquid Level */}
                                    <div
                                        className="absolute bottom-0 left-0 right-0 transition-all duration-1000 ease-in-out"
                                        style={{
                                            height: `${percent}%`,
                                            backgroundColor: percent > 20 ? '#10b981' : '#ef4444',
                                            opacity: 0.2
                                        }}
                                    />
                                    <div
                                        className="absolute bottom-0 left-0 right-0 h-1 transition-all duration-1000 ease-in-out z-10"
                                        style={{
                                            bottom: `${percent}%`,
                                            backgroundColor: percent > 20 ? '#10b981' : '#ef4444'
                                        }}
                                    />

                                    <div className="relative z-20 mb-4 text-center">
                                        <div className="text-xs text-muted-foreground uppercase tracking-widest font-semibold">Keg</div>
                                        <div className="text-lg font-bold">{Math.round(remaining)} <span className="text-xs font-normal text-muted-foreground">{tap.volume_unit || 'oz'}</span></div>
                                        <div className={cn("text-xs mt-1 px-2 py-0.5 rounded-full inline-block", percent < 20 ? "bg-red-500/20 text-red-400" : "bg-green-500/20 text-green-400")}>
                                            {Math.round(percent)}%
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

function Badge({ label, value, color }: { label: string, value: any, color: string }) {
    if (!value) return null;
    return (
        <div className={cn("flex flex-col items-center justify-center px-3 py-1.5 rounded-xl border text-xs font-medium w-14", color)}>
            <span className="opacity-70 text-[10px] uppercase">{label}</span>
            <span className="text-sm font-bold">{value}</span>
        </div>
    );
}
