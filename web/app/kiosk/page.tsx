"use client";

import { useState, useEffect } from "react";
import { apiFetch } from "@/lib/api";
import { Loader2 } from "lucide-react";
import Image from "next/image";

interface Tap {
    tap_id: string;
    beer_name: string;
    style: string;
    abv: number;
    keg_volume_l: number;
    remaining_pct: number;
    qr_code_base64: string;
}

export default function KioskPage() {
    const [taps, setTaps] = useState<Tap[]>([]);
    const [loading, setLoading] = useState(true);

    const fetchTaps = async () => {
        try {
            const res = await apiFetch<{taps: Tap[]}>("/api/taps");
            if (res.taps) {
                setTaps(res.taps);
            }
        } catch (err) {
            console.error("Failed to load taps", err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchTaps();
        const interval = setInterval(fetchTaps, 30000); // refresh every 30s
        return () => clearInterval(interval);
    }, []);

    if (loading) {
        return (
            <div className="min-h-screen bg-black flex items-center justify-center">
                <Loader2 className="w-12 h-12 text-primary animate-spin" />
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-black text-white p-8 font-sans selection:bg-primary/30">
            <header className="mb-12 text-center">
                <h1 className="text-5xl font-black tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-amber-200 to-amber-500 uppercase drop-shadow-sm">
                    On Tap Now
                </h1>
            </header>

            <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-8 max-w-7xl mx-auto">
                {taps.length === 0 ? (
                    <div className="col-span-full text-center text-zinc-500 py-20 text-xl font-medium">
                        No taps currently active.
                    </div>
                ) : (
                    taps.map((tap, i) => (
                        <div key={tap.tap_id} className="relative bg-zinc-900 border border-zinc-800 rounded-3xl p-8 flex flex-col gap-6 overflow-hidden group shadow-2xl transition-all duration-500 hover:border-amber-500/30 hover:shadow-amber-500/10">
                            {/* Number Badge */}
                            <div className="absolute -top-6 -right-6 text-9xl font-black text-white/[0.03] pointer-events-none transition-transform duration-500 group-hover:scale-110">
                                {i + 1}
                            </div>
                            
                            <div className="space-y-2 z-10">
                                <h2 className="text-3xl font-bold tracking-tight text-white line-clamp-2">
                                    {tap.beer_name || "Unknown Brew"}
                                </h2>
                                <div className="flex items-center gap-3 text-amber-500 font-semibold tracking-wide uppercase text-sm">
                                    <span>{tap.style || "Style Unknown"}</span>
                                    <span className="w-1.5 h-1.5 rounded-full bg-amber-500/50" />
                                    <span>{tap.abv}% ABV</span>
                                </div>
                            </div>

                            <div className="flex-1 flex items-center justify-between gap-6 z-10 mt-4">
                                {/* Keg Level */}
                                <div className="flex-1 space-y-3">
                                    <div className="flex justify-between text-xs font-bold text-zinc-400 uppercase tracking-wider">
                                        <span>Keg Level</span>
                                        <span className="text-white">{tap.remaining_pct.toFixed(0)}%</span>
                                    </div>
                                    <div className="h-4 bg-zinc-800 rounded-full overflow-hidden border border-zinc-700/50">
                                        <div 
                                            className="h-full bg-gradient-to-r from-amber-600 to-amber-400 rounded-full transition-all duration-1000 ease-out"
                                            style={{ width: `${Math.max(0, Math.min(100, tap.remaining_pct))}%` }}
                                        />
                                    </div>
                                    <div className="text-xs text-zinc-500 font-medium">
                                        {tap.keg_volume_l}L Capacity
                                    </div>
                                </div>

                                {/* QR Code */}
                                {tap.qr_code_base64 && (
                                    <div className="bg-white p-2 rounded-xl shadow-lg shrink-0">
                                        <Image 
                                            src={`data:image/png;base64,${tap.qr_code_base64}`} 
                                            alt="Tap Info QR"
                                            width={100}
                                            height={100}
                                            className="rounded-lg opacity-90"
                                        />
                                        <p className="text-[9px] text-center text-zinc-500 font-bold uppercase mt-1">Scan to View</p>
                                    </div>
                                )}
                            </div>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
}
