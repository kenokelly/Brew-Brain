'use client';

import { useEffect, useState } from 'react';
import { cn } from '@/lib/utils';
import { Activity, Thermometer, Droplets, Server, Wifi, Brain, RefreshCcw, ExternalLink } from 'lucide-react';
import { useSocket } from '@/lib/socket';
import { RealTimeChart } from '@/components/charts';
import { useStatus } from '@/lib/hooks';
import { DashboardSkeleton } from '@/components/ui/skeleton';
import { AnomalyWidget } from '@/components/AnomalyWidget';
import { PredictionCard } from '@/components/PredictionCard';
import { PeerComparisonWidget } from '@/components/PeerComparison';
import { BrewDayGuide } from '@/components/BrewDayGuide';
import { GrafanaChart } from '@/components/GrafanaChart';
import type { SystemStatus } from '@/types/api';
import { BookOpen } from 'lucide-react';
import toast from 'react-hot-toast';

interface DataPoint {
  time: string;
  temp: number;
  sg: number;
}

export default function Dashboard() {
  const { socket, isConnected: connected } = useSocket();
  const { data: status, error, isLoading, mutate: mutateStatus } = useStatus();
  const [history, setHistory] = useState<DataPoint[]>([]);
  const [isGuideOpen, setIsGuideOpen] = useState(false);
  const [timeRange, setTimeRange] = useState('now-7d');

  // Update history when status changes (from SWR or socket)
  useEffect(() => {
    if (status?.temp && status?.sg) {
      // Calculate dynamic values if not present
      updateHistory(status);
    }
  }, [status?.temp, status?.sg]);

  // Socket Listeners for real-time updates
  useEffect(() => {
    if (!socket) return;

    socket.on('status_update', (data: typeof status) => {
      // SWR will handle the data, but we also update history
      if (data?.temp && data?.sg) {
        updateHistory(data);
        mutateStatus(); // Refresh SWR cache
      }
    });

    return () => {
      socket.off('status_update');
    };
  }, [socket, mutateStatus]);

  const updateHistory = (data: SystemStatus) => {
    const now = new Date().toLocaleTimeString();
    if (data.temp && data.sg) {
      setHistory(prev => {
        const newPoint = { time: now, temp: data.temp!, sg: data.sg! };
        // Keep last 50 points
        const newHistory = [...prev, newPoint];
        if (newHistory.length > 50) newHistory.shift();
        return newHistory;
      });
    }
  };

  const handleSyncBrewfather = async () => {
    const toastId = toast.loading("Syncing with Brewfather...");
    try {
      const res = await fetch('/api/sync_brewfather', { method: 'POST' });
      const d = await res.json();
      if (res.ok && d.status === 'synced') {
        toast.success(`Synced batch: ${d.data.name}`, { id: toastId });
        mutateStatus();
      } else {
        toast.error(`Sync error: ${d.error || 'Unknown'}`, { id: toastId });
      }
    } catch (e) {
      toast.error("Connection failed", { id: toastId });
    }
  };

  const openTiltPi = () => {
    window.open(`http://${window.location.hostname}:1880/ui/`, '_blank');
  };

  // Calculations for Rings
  const og = status?.og || 1.050;
  const sg = status?.sg || 1.000;
  const abv = Math.max(0, (og - sg) * 131.25);
  const att = Math.max(0, ((og - sg) / (og - 1)) * 100);

  return (
    <main className="min-h-screen bg-background text-foreground p-4 md:p-8 font-sans selection:bg-primary/20 pb-24">
      <div className="max-w-7xl mx-auto space-y-6">

        {/* Header */}
        <header className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div>
            <h1 className="text-4xl font-extrabold tracking-tight lg:text-5xl bg-clip-text text-transparent bg-gradient-to-r from-primary to-primary/60">
              Brew Brain
            </h1>
            <p className="text-muted-foreground mt-2 text-lg">
              {status?.batch_name || "Autonomous Fermentation Intelligence"}
            </p>
          </div>
          <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-secondary/50 backdrop-blur-md border border-white/10 shadow-sm">
            <div className={cn("w-3 h-3 rounded-full animate-pulse",
              connected ? "bg-emerald-500" :
                (!error && status) ? "bg-amber-500" : "bg-rose-500"
            )} />
            <span className="text-sm font-medium">
              {connected ? "Real-time" :
                (!error && status) ? "Live (Polling)" : "Offline"}
            </span>
          </div>
          <button
            onClick={() => setIsGuideOpen(true)}
            className="hidden md:flex items-center gap-2 px-6 py-2.5 rounded-full bg-primary/10 text-primary border border-primary/20 hover:bg-primary/20 transition-all font-bold text-sm shadow-[0_0_20px_rgba(var(--primary),0.1)] active:scale-95"
          >
            <BookOpen className="w-4 h-4" />
            Brew Day Prep
          </button>
        </header>

        {/* Brew Day Guide Modal */}
        <BrewDayGuide isOpen={isGuideOpen} onClose={() => setIsGuideOpen(false)} />

        {/* Status Cards (Top 4 Grid) */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard
            title="Gravity"
            value={status?.sg ? status.sg.toFixed(3) : "--.---"}
            unit="SG"
            color="amber"
          />
          <StatCard
            title="Temp"
            value={status?.temp ? status.temp.toFixed(1) : "--.-"}
            unit={`°${status?.temp_unit || 'C'}`}
            color="blue"
            subtext={status?.pi_temp ? `Pi: ${status.pi_temp}°C` : undefined}
          />

          {/* Alcohol Ring Card */}
          <div className="bg-card/50 backdrop-blur-sm border border-border/50 rounded-2xl p-4 flex flex-col items-center justify-center relative overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-br from-emerald-500/10 to-transparent pointer-events-none" />
            <span className="text-xs uppercase tracking-widest text-emerald-500/80 mb-2 font-bold z-10">Alcohol</span>
            <RingChart value={abv} max={15} color="#10b981" unit="%" />
          </div>

          {/* Attenuation Ring Card */}
          <div className="bg-card/50 backdrop-blur-sm border border-border/50 rounded-2xl p-4 flex flex-col items-center justify-center relative overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-br from-purple-500/10 to-transparent pointer-events-none" />
            <span className="text-xs uppercase tracking-widest text-purple-500/80 mb-2 font-bold z-10">Atten.</span>
            <RingChart value={att} max={100} color="#a855f7" unit="%" />
          </div>
        </div>

        {/* Batch Info Card (Legacy Restoration) */}
        <div className="bg-card/50 backdrop-blur-sm border border-border/50 rounded-2xl p-6 relative overflow-hidden">
          <div className="flex justify-between items-start mb-2 relative z-10">
            <div className="flex items-center gap-3">
              <h2 className="text-xl font-bold">{status?.batch_name || '--'}</h2>
              <button
                onClick={handleSyncBrewfather}
                className="text-muted-foreground hover:text-blue-400 p-1.5 rounded-full hover:bg-secondary transition-colors"
                title="Sync from Brewfather"
              >
                <RefreshCcw className="w-4 h-4" />
              </button>
            </div>
            <div className="text-right hidden md:block">
              <div className="text-xs text-muted-foreground uppercase tracking-wider">Targets</div>
              <span className="font-mono text-sm text-blue-400">
                OG: <span className="text-foreground">{status?.og?.toFixed(3) || '--'}</span>{' '}
                FG: <span className="text-foreground">{status?.target_fg?.toFixed(3) || '--'}</span>
              </span>
            </div>
          </div>
          <div className="flex flex-col md:flex-row justify-between gap-4 relative z-10">
            <div>
              <p className="text-xs text-muted-foreground">Started: {status?.start_date || '--'}</p>
              <p className="text-sm text-muted-foreground italic mt-1 line-clamp-1">{status?.batch_notes || 'No notes'}</p>
            </div>
            {/* Mobile Targets */}
            <div className="md:hidden flex justify-between items-end border-t border-border/50 pt-2 mt-2">
              <div className="text-xs text-muted-foreground uppercase tracking-wider">Targets</div>
              <span className="font-mono text-sm text-blue-400">
                OG: <span className="text-foreground">{status?.og?.toFixed(3) || '--'}</span>{' '}
                FG: <span className="text-foreground">{status?.target_fg?.toFixed(3) || '--'}</span>
              </span>
            </div>
          </div>
        </div>

        {/* AI & Insights */}
        <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <PredictionCard />
          <AnomalyWidget />
          <PeerComparisonWidget />
        </section>

        {/* Grafana Controls Section */}
        <div className="space-y-4">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <h3 className="text-lg font-semibold flex items-center gap-2">
              <Activity className="w-5 h-5 text-primary" /> Fermentation Chart
            </h3>
            <div className="flex flex-wrap gap-2">
              <button onClick={openTiltPi} className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 hover:bg-indigo-500/20 transition-colors">
                <ExternalLink className="w-3 h-3" /> TiltPi
              </button>
              <div className="flex bg-secondary rounded-lg p-1 gap-1">
                {['now-24h', 'now-3d', 'now-7d', 'now-30d'].map((range) => (
                  <button
                    key={range}
                    onClick={() => setTimeRange(range)}
                    className={cn(
                      "px-3 py-1 text-xs font-medium rounded-md transition-colors",
                      timeRange === range
                        ? "bg-primary text-primary-foreground shadow-sm"
                        : "text-muted-foreground hover:text-foreground"
                    )}
                  >
                    {range.replace('now-', '')}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="w-full h-[400px] md:h-[600px] rounded-3xl overflow-hidden bg-card border border-border/50 relative shadow-lg">
            <GrafanaChart timeRange={timeRange} />
          </div>
        </div>

      </div>
    </main>
  );
}

// Sub-components

function StatCard({ title, value, unit, color, subtext }: { title: string, value: string, unit: string, color: 'amber' | 'blue' | 'emerald' | 'rose', subtext?: string }) {
  const gradients = {
    amber: "from-amber-500/10",
    blue: "from-blue-500/10",
    emerald: "from-emerald-500/10",
    rose: "from-rose-500/10"
  };
  const textColors = {
    amber: "text-amber-400/80",
    blue: "text-blue-400/80",
    emerald: "text-emerald-400/80",
    rose: "text-rose-400/80"
  };

  return (
    <div className="glass-panel bg-card/50 backdrop-blur-sm border border-border/50 p-4 rounded-2xl flex flex-col items-center justify-center relative overflow-hidden group hover:-translate-y-1 transition-transform duration-300">
      <div className={`absolute inset-0 bg-gradient-to-br ${gradients[color]} to-transparent pointer-events-none`} />
      <div className="relative z-10 text-center">
        <span className={`text-xs uppercase tracking-widest ${textColors[color]} mb-1 block font-bold`}>{title}</span>
        <div className="flex items-baseline justify-center gap-1">
          <span className="text-3xl font-bold tracking-tight tabular-nums">{value}</span>
          <span className="text-xs text-muted-foreground">{unit}</span>
        </div>
        {subtext && <div className="text-xs text-muted-foreground mt-1 opacity-80">{subtext}</div>}
      </div>
    </div>
  );
}

function RingChart({ value, max, color, unit }: { value: number, max: number, color: string, unit: string }) {
  const radius = 28;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (Math.min(value / max, 1) * circumference);

  return (
    <div className="relative w-16 h-16 z-10">
      <svg className="w-full h-full transform -rotate-90">
        <circle
          className="text-secondary"
          strokeWidth="6"
          stroke="currentColor"
          fill="transparent"
          r={radius}
          cx="32"
          cy="32"
        />
        <circle
          className="transition-all duration-1000 ease-out"
          strokeWidth="6"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          stroke={color}
          fill="transparent"
          r={radius}
          cx="32"
          cy="32"
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center flex-col">
        <span className="text-sm font-bold tabular-nums leading-none">{value.toFixed(1)}</span>
        <span className="text-[10px] text-muted-foreground leading-none mt-0.5">{unit}</span>
      </div>
    </div>
  );
}
