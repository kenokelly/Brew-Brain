"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { Loader2 } from "lucide-react";
import { useParams } from "next/navigation";

interface Tap {
    tap_id: string;
    beer_name: string;
    style: string;
    abv: number;
    keg_volume_l: number;
    remaining_pct: number;
    untappd_url?: string;
}

export default function PublicTapPage() {
    const params = useParams();
    const id = params.id as string;
    
    const [tap, setTap] = useState<Tap | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchTaps = async () => {
            try {
                const res = await apiFetch<{taps: Tap[]}>("/api/taps");
                if (res.taps) {
                    const found = res.taps.find(t => t.tap_id === id);
                    if (found) setTap(found);
                }
            } catch (err) {
                console.error("Failed to load tap", err);
            } finally {
                setLoading(false);
            }
        };
        fetchTaps();
    }, [id]);

    if (loading) {
        return (
            <div className="min-h-screen bg-zinc-50 flex items-center justify-center">
                <Loader2 className="w-8 h-8 text-amber-500 animate-spin" />
            </div>
        );
    }

    if (!tap) {
        return (
            <div className="min-h-screen bg-zinc-50 flex flex-col items-center justify-center p-6 text-center space-y-4">
                <div className="w-20 h-20 bg-zinc-200 rounded-full flex items-center justify-center mb-4">
                    <span className="text-3xl">🍺</span>
                </div>
                <h1 className="text-2xl font-bold text-zinc-800">Tap Not Found</h1>
                <p className="text-zinc-500">This tap is either empty or does not exist.</p>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-white font-sans text-zinc-900 pb-20">
            {/* Header Image Area */}
            <div className="h-64 bg-zinc-900 relative flex flex-col items-center justify-center overflow-hidden">
                <div className="absolute inset-0 opacity-20 bg-[url('https://www.transparenttextures.com/patterns/cubes.png')]" />
                <div className="absolute inset-0 bg-gradient-to-t from-zinc-900 via-transparent to-transparent" />
                <h1 className="text-4xl font-black text-white text-center px-4 z-10 leading-tight drop-shadow-md">
                    {tap.beer_name || "Unknown Brew"}
                </h1>
                <p className="text-amber-500 font-bold tracking-widest uppercase mt-4 z-10 drop-shadow-md">
                    {tap.style || "Style Unknown"}
                </p>
            </div>

            {/* Content Area */}
            <div className="max-w-md mx-auto -mt-8 relative z-20 px-6">
                <div className="bg-white rounded-3xl shadow-xl shadow-zinc-200 p-8 border border-zinc-100 flex justify-between items-center">
                    <div className="text-center">
                        <div className="text-3xl font-black text-zinc-800">{tap.abv}%</div>
                        <div className="text-xs font-bold text-zinc-400 uppercase tracking-widest mt-1">ABV</div>
                    </div>
                    <div className="w-px h-12 bg-zinc-200" />
                    <div className="text-center">
                        <div className="text-3xl font-black text-zinc-800">{tap.remaining_pct.toFixed(0)}%</div>
                        <div className="text-xs font-bold text-zinc-400 uppercase tracking-widest mt-1">Remaining</div>
                    </div>
                </div>

                {tap.untappd_url && (
                    <div className="mt-8 text-center">
                        <a href={tap.untappd_url} target="_blank" rel="noreferrer" className="inline-block w-full py-4 rounded-2xl bg-[#ffc000] text-amber-950 font-black tracking-wide text-lg shadow-lg shadow-amber-500/30 hover:scale-105 transition-transform">
                            VIEW ON UNTAPPD
                        </a>
                    </div>
                )}

                <div className="mt-12 text-center">
                    <p className="text-zinc-500 italic">Brewed by Brew-Brain</p>
                </div>
            </div>
        </div>
    );
}
