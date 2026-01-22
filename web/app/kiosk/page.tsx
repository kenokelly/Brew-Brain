'use client';

import { useEffect, useState } from 'react';
import { getSrmColor } from '@/lib/beer';
import { cn } from '@/lib/utils';
import { Droplets, Wifi, Thermometer, Activity } from 'lucide-react';
import { useSocket } from '@/lib/socket';

interface SystemStatus {
    temp?: number;
    pi_temp?: number;
}

interface TapsResponse {
    [key: string]: {
        active: boolean;
        name?: string;
        style?: string;
        abv?: number;
        ibu?: number;
        srm?: number;
        keg_remaining?: number;
        keg_total?: number;
        volume_unit?: string;
    };
}

export default function KioskPage() {
    const socket = useSocket();
    const [status, setStatus] = useState<SystemStatus | null>(null);
    const [taps, setTaps] = useState<TapsResponse | null>(null);
    const [time, setTime] = useState(new Date());

    useEffect(() => {
        // Clock
        const timer = setInterval(() => setTime(new Date()), 1000);
        return () => clearInterval(timer);
    }, []);

    useEffect(() => {
        // Taps Initial Fetch
        fetch('/api/taps').then(r => r.json()).then(setTaps).catch(console.error);

        // Status Initial Poll
        fetch('/api/status').then(r => r.json()).then(setStatus).catch(console.error);

        if (socket) {
            socket.on('status_update', setStatus);
        }
        return () => {
            socket?.off('status_update');
        };
    }, [socket]);

    return (
        <div className="fixed inset-0 bg-background text-foreground overflow-hidden flex flex-col p-6 z-[100]">
            {/* Header */}
            <header className="flex justify-between items-center mb-8 border-b border-white/10 pb-4">
                <h1 className="text-5xl font-extrabold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-primary to-amber-300">
                    On Tap
                </h1>
                <div className="text-right">
                    <div className="text-4xl font-mono font-bold tracking-widest">
                        {time.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </div>
                    <div className="flex items-center justify-end gap-4 text-muted-foreground mt-2 text-lg">
                        <span className="flex items-center gap-1"><Thermometer className="w-5 h-5" /> {status?.temp ? status.temp.toFixed(1) : '--'}°F</span>
                        <span className="flex items-center gap-1"><Activity className="w-5 h-5" /> Pi: {status?.pi_temp ? status.pi_temp : '--'}°C</span>
                    </div>
                </div>
            </header>

            {/* Taps Grid */}
            <div className="flex-1 grid grid-cols-2 lg:grid-cols-4 gap-6 content-start">
                {['tap_1', 'tap_2', 'tap_3', 'tap_4'].map((key, i) => {
                    const tap = taps ? taps[key] : null;
                    const isActive = tap?.active;

                    if (!isActive) {
                        return (
                            <div key={key} className="h-full rounded-3xl bg-secondary/10 border-2 border-dashed border-white/5 flex flex-col items-center justify-center text-muted-foreground opacity-50">
                                <Droplets className="w-16 h-16 mb-4" />
                                <span className="text-2xl font-bold">Tap {i + 1} Empty</span>
                            </div>
                        );
                    }

                    const color = getSrmColor(tap.srm);
                    const total = tap.keg_total || 640;
                    const remaining = tap.keg_remaining || 0;
                    const pct = Math.min(100, Math.max(0, (remaining / total) * 100));

                    return (
                        <div key={key} className="h-full rounded-3xl bg-card border border-white/10 relative overflow-hidden flex flex-col shadow-2xl">
                            {/* Beer Color Header */}
                            <div className="h-32 w-full relative" style={{ backgroundColor: color }}>
                                <div className="absolute inset-0 bg-gradient-to-t from-black/80 to-transparent" />
                                <div className="absolute bottom-4 left-4">
                                    <div className="text-xs font-bold uppercase tracking-wider text-white/80 mb-1">Tap {i + 1}</div>
                                    <h2 className="text-3xl font-extrabold text-white leading-tight shadow-sm drop-shadow-md">{tap.name}</h2>
                                </div>
                            </div>

                            {/* Body */}
                            <div className="flex-1 p-6 flex flex-col justify-between">
                                <div>
                                    <div className="text-xl text-primary font-semibold mb-2">{tap.style}</div>
                                    <div className="flex gap-4 text-lg text-muted-foreground font-mono">
                                        <span>{tap.abv}% ABV</span>
                                        <span>{tap.ibu} IBU</span>
                                    </div>
                                </div>

                                {/* Keg Level */}
                                <div className="mt-8">
                                    <div className="flex justify-between text-sm mb-2 font-bold text-muted-foreground">
                                        <span>KEG LEVEL</span>
                                        <span>{Math.round(remaining)} {tap.volume_unit}</span>
                                    </div>
                                    <div className="h-6 bg-secondary/50 rounded-full overflow-hidden border border-white/5">
                                        <div
                                            className="h-full transition-all duration-1000 ease-out"
                                            style={{ width: `${pct}%`, backgroundColor: pct > 20 ? '#10b981' : '#ef4444' }}
                                        />
                                    </div>
                                </div>
                            </div>
                        </div>
                    );
                })}
            </div>
            {/* Exit Kiosk Button */}
            <a
                href="/"
                className="fixed bottom-6 right-6 p-4 rounded-full bg-white/5 hover:bg-white/20 text-muted-foreground hover:text-white transition-all backdrop-blur-md border border-white/5 z-50 group"
                title="Exit Kiosk"
            >
                <div className="w-6 h-6 border-2 border-current rounded-md group-hover:scale-90 transition-transform" />
            </a>
        </div>
    );
}
