'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import { LayoutDashboard, Beer, Bot, CircleHelp, Flame, Settings as SettingsIcon, Monitor, Gauge, Wrench } from 'lucide-react';

// `dynamicHost: true` means the href's hostname is resolved from
// window.location at click time (via onClick, not a static Link href) so it
// still works if the Pi's LAN IP changes or the app is reached via a
// different address - mirrors the working pattern already used by the
// dashboard's own openTiltPi() button. Doing this via onClick (rather than
// computing window.location in the href itself) avoids a server/client
// hydration mismatch, since onClick only ever runs in the browser.
export const NAV_ITEMS = [
    { href: '/', icon: LayoutDashboard, label: 'Dashboard', group: 'Monitor' },
    { href: 'http://{host}:1880/ui/', icon: Gauge, label: 'TiltPi', group: 'Monitor', dynamicHost: true },
    { href: '/taplist', icon: Beer, label: 'Tap List', group: 'Monitor' },
    { href: '/kiosk', icon: Monitor, label: 'Kiosk Mode', group: 'Monitor' },
    { href: '/brewday', icon: Flame, label: 'Brew Day', group: 'Brew' },
    { href: '/automation', icon: Wrench, label: 'Automation', group: 'Brew' },
    { href: '/chat', icon: Bot, label: 'Brewmaster', group: 'Brew' },
    { href: '/settings', icon: SettingsIcon, label: 'Settings', group: 'System' },
    { href: '/help', icon: CircleHelp, label: 'Help', group: 'System' },
];

function resolveHref(href: string, dynamicHost?: boolean): string {
    if (dynamicHost && typeof window !== 'undefined') {
        return href.replace('{host}', window.location.hostname);
    }
    return href;
}

export function SidebarItem({ href, icon: Icon, label, dynamicHost }: typeof NAV_ITEMS[0]) {
    const pathname = usePathname();
    const active = pathname === href;
    const ariaLabel = label === 'Help' ? 'Help & Documentation' : label;

    const className = cn(
        "flex items-center gap-3 px-3 py-3 rounded-xl transition-all duration-200 group relative overflow-hidden focus-visible:ring-2 focus-visible:ring-primary outline-none",
        active
            ? "bg-primary/10 text-primary font-medium shadow-sm"
            : "text-muted-foreground hover:bg-secondary/50 hover:text-foreground"
    );
    const content = (
        <>
            <Icon className={cn("w-6 h-6 shrink-0", active && "text-primary")} />
            <span className="hidden lg:block">{label}</span>
            {active && <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-8 bg-primary rounded-r-full lg:hidden" />}
        </>
    );

    if (dynamicHost) {
        return (
            <button
                type="button"
                onClick={() => window.open(resolveHref(href, dynamicHost), '_blank')}
                aria-label={ariaLabel}
                className={cn(className, "text-left w-full")}
            >
                {content}
            </button>
        );
    }

    return (
        <Link href={href} aria-label={ariaLabel} className={className}>
            {content}
        </Link>
    );
}

export function MobileMenuItem({ href, icon: Icon, label, dynamicHost, onClick }: typeof NAV_ITEMS[0] & { onClick: () => void }) {
    const pathname = usePathname();
    const active = pathname === href;
    const ariaLabel = label === 'Help' ? 'Help & Documentation' : label;

    const className = cn(
        "flex items-center gap-4 p-4 rounded-2xl text-lg font-medium border border-transparent focus-visible:ring-2 focus-visible:ring-primary outline-none",
        active
            ? "bg-primary/10 text-primary border-primary/20"
            : "bg-secondary/30 text-foreground"
    );
    const content = (
        <>
            <Icon className="w-6 h-6" />
            {label}
        </>
    );

    if (dynamicHost) {
        return (
            <button
                type="button"
                onClick={() => { window.open(resolveHref(href, dynamicHost), '_blank'); onClick(); }}
                aria-label={ariaLabel}
                className={cn(className, "text-left w-full")}
            >
                {content}
            </button>
        );
    }

    return (
        <Link href={href} onClick={onClick} aria-label={ariaLabel} className={className}>
            {content}
        </Link>
    );
}
