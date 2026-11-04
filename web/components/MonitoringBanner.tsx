import Link from 'next/link';
import { ShieldCheck, ShieldOff, FlaskConical, Droplets, WifiOff } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { SystemStatus } from '@/types/api';

// No Tilt reading for this long means the signal is probably lost
const STALE_MIN = 20;

type Tone = 'ok' | 'warn' | 'info' | 'off' | 'bad';

const TONES: Record<Tone, string> = {
  ok: 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400',
  warn: 'bg-amber-500/10 border-amber-500/40 text-amber-400',
  info: 'bg-sky-500/10 border-sky-500/30 text-sky-400',
  off: 'bg-secondary/40 border-border text-muted-foreground',
  bad: 'bg-rose-500/10 border-rose-500/40 text-rose-400',
};

function minutesSince(iso?: string): number | null {
  if (!iso) return null;
  const t = Date.parse(iso);
  return Number.isNaN(t) ? null : Math.max(0, Math.round((Date.now() - t) / 60000));
}

function describe(status: SystemStatus) {
  const ago = minutesSince(status.last_sync);
  const agoText = ago === null ? 'no readings yet' : ago < 1 ? 'last reading just now' : `last reading ${ago} min ago`;

  if (status.test_mode) {
    return { tone: 'warn' as Tone, Icon: FlaskConical, title: 'Simulated data',
      detail: 'Readings are fake and the Tilt is ignored. Alerts are off. Turn off Simulated Data in Settings.' };
  }
  if (status.water_test) {
    return { tone: 'info' as Tone, Icon: Droplets, title: 'Water test running',
      detail: `Calibrating the Tilt in water. Fermentation alerts are paused · ${agoText}` };
  }
  if (!status.brew_active) {
    return { tone: 'off' as Tone, Icon: ShieldOff, title: 'Monitoring off',
      detail: 'No alerts will be sent. Turn on Brew Alerts in Settings when a batch is fermenting.' };
  }
  if (ago === null || ago > STALE_MIN) {
    return { tone: 'bad' as Tone, Icon: WifiOff, title: 'Monitoring on, but no Tilt signal',
      detail: `Alerts are on, but ${agoText}. Check the Tilt is in the fermenter and TiltPi is running.` };
  }
  return { tone: 'ok' as Tone, Icon: ShieldCheck, title: 'Monitoring active',
    detail: `Live Tilt data · alerts on for signal loss, stalls and temperature · ${agoText}` };
}

export function MonitoringBanner({ status }: { status?: SystemStatus }) {
  if (!status) return null;
  const { tone, Icon, title, detail } = describe(status);
  return (
    <Link
      href="/settings"
      className={cn('flex items-center gap-3 px-4 py-3 rounded-2xl border transition-colors hover:brightness-110', TONES[tone])}
    >
      <Icon className="w-5 h-5 shrink-0" />
      <div className="min-w-0">
        <p className="font-bold text-sm">{title}</p>
        <p className="text-xs opacity-80">{detail}</p>
      </div>
    </Link>
  );
}
