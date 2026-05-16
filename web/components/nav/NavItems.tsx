'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import { LayoutDashboard, Beer, Bot, CircleHelp, Menu, Monitor } from 'lucide-react';

export const NAV_ITEMS = [
    { href: '/', icon: LayoutDashboard, label: 'Dashboard' },
    { href: '/chat', icon: Bot, label: 'Brewmaster' },
    { href: '/settings', icon: Menu, label: 'Settings' },
    { href: 'http://192.168.155.226:1880/ui/', icon: LayoutDashboard, label: 'TiltPi' },
    { href: '/taplist', icon: Beer, label: 'Tap List' },
    { href: '/automation', icon: Bot, label: 'Automation' },
    { href: '/kiosk', icon: Monitor, label: 'Kiosk Mode' },
    { href: '/help', icon: CircleHelp, label: 'Help' },
];

export function SidebarItem({ href, icon: Icon, label }: typeof NAV_ITEMS[0]) {
    const pathname = usePathname();
    const active = pathname === href;

    return (
        <Link
            href={href}
            className={cn(
                "flex items-center gap-3 px-3 py-3 rounded-xl transition-all duration-200 group relative overflow-hidden focus-visible:ring-2 focus-visible:ring-primary outline-none",
                active
                    ? "bg-primary/10 text-primary font-medium shadow-sm"
                    : "text-muted-foreground hover:bg-secondary/50 hover:text-foreground"
            )}
        >
            <Icon className={cn("w-6 h-6 shrink-0", active && "text-primary")} />
            <span className="hidden lg:block">{label}</span>
            {active && <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-8 bg-primary rounded-r-full lg:hidden" />}
        </Link>
    );
}

export function MobileMenuItem({ href, icon: Icon, label, onClick }: typeof NAV_ITEMS[0] & { onClick: () => void }) {
    const pathname = usePathname();
    const active = pathname === href;

    return (
        <Link
            href={href}
            onClick={onClick}
            className={cn(
                "flex items-center gap-4 p-4 rounded-2xl text-lg font-medium border border-transparent focus-visible:ring-2 focus-visible:ring-primary outline-none",
                active
                    ? "bg-primary/10 text-primary border-primary/20"
                    : "bg-secondary/30 text-foreground"
            )}
        >
            <Icon className="w-6 h-6" />
            {label}
        </Link>
    );
}
