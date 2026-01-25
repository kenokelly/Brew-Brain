'use client';

import { useEffect, useState } from 'react';
import { cn } from '@/lib/utils';
import { Activity, Thermometer, Droplets, Server, Wifi, Brain } from 'lucide-react';
import { useSocket } from '@/lib/socket';
import { RealTimeChart } from '@/components/charts';
import { useStatus } from '@/lib/hooks';
import { DashboardSkeleton } from '@/components/ui/skeleton';
import { AnomalyWidget } from '@/components/AnomalyWidget';
import { PredictionCard } from '@/components/PredictionCard';
import type { SystemStatus } from '@/types/api';

interface DataPoint {
  time: string;
  temp: number;
  sg: number;
}

export default function Dashboard() {
  const { socket, isConnected: connected } = useSocket();
  const { data: status, error, isLoading } = useStatus();
  const [history, setHistory] = useState<DataPoint[]>([]);

  // Update history when status changes (from SWR or socket)
  useEffect(() => {
    if (status?.temp && status?.sg) {
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
      }
    });

    return () => {
      socket.off('status_update');
    };
  }, [socket]);

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

  return (
    <main className="min-h-screen bg-background text-foreground p-8 font-sans selection:bg-primary/20">
      <div className="max-w-7xl mx-auto space-y-8">

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
            <div className={cn("w-3 h-3 rounded-full animate-pulse", connected ? "bg-emerald-500" : "bg-rose-500")} />
            <span className="text-sm font-medium">
              {connected ? "Real-time" : "Connecting..."}
            </span>
          </div>
        </header>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <StatCard
            title="Wort Temp"
            value={status?.temp ? `${status.temp.toFixed(1)}°F` : "--"}
            icon={<Thermometer className="w-5 h-5 text-rose-500" />}
            subtext={status?.pi_temp ? `Pi: ${status.pi_temp}°C` : undefined}
          />
          <StatCard
            title="Specific Gravity"
            value={status?.sg ? status.sg.toFixed(3) : "--"}
            icon={<Activity className="w-5 h-5 text-blue-500" />}
          />
          <StatCard
            title="Tilt Signal"
            value={status?.rssi ? `${status.rssi} dBm` : "--"}
            icon={<Wifi className="w-5 h-5 text-emerald-500" />}
          />
          <StatCard
            title="Last Sync"
            value={status?.last_sync ? new Date(status.last_sync).toLocaleTimeString() : "--"}
            icon={<Server className="w-5 h-5 text-amber-500" />}
          />
        </div>

        {/* AI Insights Section */}
        <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <PredictionCard />
          <AnomalyWidget />
        </section>

        {/* Charts Section */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <ChartCard title="Temperature Trend">
            <RealTimeChart data={history} dataKey="temp" color="#f43f5e" unit="°F" />
          </ChartCard>
          <ChartCard title="Gravity Trend">
            <RealTimeChart data={history} dataKey="sg" color="#3b82f6" unit="" />
          </ChartCard>
        </div>

        {/* Grafana Embed */}
        <section className="relative overflow-hidden rounded-3xl bg-secondary/30 backdrop-blur-xl border border-white/10 p-1 shadow-2xl h-[600px]">
          <iframe
            src={`http://${typeof window !== 'undefined' ? window.location.hostname : 'localhost'}:3000/d-solo/fermentation-dashboard/brew-brain-production?orgId=1&panelId=1&theme=dark`}
            className="w-full h-full rounded-2xl border-none opacity-90 hover:opacity-100 transition-opacity"
            title="Grafana Dashboard"
          />
        </section>
      </div>
    </main>
  );
}

function StatCard({ title, value, icon, subtext }: { title: string, value: string, icon: React.ReactNode, subtext?: string }) {
  return (
    <div className="group relative overflow-hidden rounded-2xl bg-card p-6 shadow-md border border-border/50 hover:shadow-lg transition-all duration-300 hover:-translate-y-1">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-muted-foreground">{title}</h3>
        <div className="p-2 rounded-full bg-secondary/80 text-secondary-foreground">
          {icon}
        </div>
      </div>
      <div className="text-3xl font-bold tracking-tight">{value}</div>
      {subtext && <div className="text-xs text-muted-foreground mt-1">{subtext}</div>}
      <div className="absolute bottom-0 left-0 h-1 w-full bg-gradient-to-r from-primary/0 via-primary/20 to-primary/0 opacity-0 group-hover:opacity-100 transition-opacity" />
    </div>
  );
}

function ChartCard({ title, children }: { title: string, children: React.ReactNode }) {
  return (
    <div className="h-80 rounded-3xl bg-card/50 backdrop-blur-sm border border-border/50 p-6 flex flex-col shadow-sm">
      <h3 className="text-lg font-semibold mb-4">{title}</h3>
      <div className="flex-1 w-full min-h-0">
        {children}
      </div>
    </div>
  );
}
