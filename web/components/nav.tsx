'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import { LayoutDashboard, Beer, Bot, CircleHelp, Monitor, Menu, X } from 'lucide-react';
import { useSocket } from '@/lib/socket';
import { useStatus } from '@/lib/hooks';

const NAV_ITEMS = [
    { href: '/', icon: LayoutDashboard, label: 'Dashboard' },
    { href: '/chat', icon: Bot, label: 'Brewmaster' },
    { href: '/settings', icon: Menu, label: 'Settings' },
    { href: 'http://192.168.155.226:1880/ui/', icon: LayoutDashboard, label: 'TiltPi' },
    { href: '/taplist', icon: Beer, label: 'Tap List' },
    { href: '/automation', icon: Bot, label: 'Automation' },
    { href: '/kiosk', icon: Monitor, label: 'Kiosk Mode' },
    { href: '/help', icon: CircleHelp, label: 'Help' },
];

export function NavBar() {
    const pathname = usePathname();
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
    const { isConnected } = useSocket();
    const { data: status, error } = useStatus();

    // Determine connection state:
    // 1. Real-time (Socket Connected)
    // 2. Live (Polling) (Socket fails, but API works)
    // 3. Offline (Both fail)

    let statusFormatted = "Offline";
    let statusColor = "bg-rose-500";

    if (isConnected) {
        statusFormatted = "Connected";
        statusColor = "bg-emerald-500";
    } else if (status && !error) {
        statusFormatted = "Via API";
        statusColor = "bg-amber-500";
    }

    return (
        <>
            {/* Desktop Sidebar (Left) */}
            <aside className="hidden md:flex flex-col w-20 lg:w-64 fixed inset-y-0 left-0 z-[100] bg-card border-r border-border/50 transition-all duration-300">
                <div className="h-16 flex items-center justify-center lg:justify-start lg:px-6 border-b border-border/50">
                    <Beer className="w-8 h-8 text-primary" />
                    <span className="hidden lg:block ml-3 font-bold text-xl bg-clip-text text-transparent bg-gradient-to-r from-primary to-primary/60">
                        Brew Brain
                    </span>
                </div>

                <nav className="flex-1 py-6 flex flex-col gap-2 px-3">
                    {NAV_ITEMS.map((item) => {
                        const active = pathname === item.href;
                        return (
                            <Link
                                key={item.href}
                                href={item.href}
                                className={cn(
                                    "flex items-center gap-3 px-3 py-3 rounded-xl transition-all duration-200 group relative overflow-hidden focus-visible:ring-2 focus-visible:ring-primary outline-none",
                                    active
                                        ? "bg-primary/10 text-primary font-medium shadow-sm"
                                        : "text-muted-foreground hover:bg-secondary/50 hover:text-foreground"
                                )}
                            >
                                <item.icon className={cn("w-6 h-6 shrink-0", active && "text-primary")} />
                                <span className="hidden lg:block">{item.label}</span>
                                {active && <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-8 bg-primary rounded-r-full lg:hidden" />}
                            </Link>
                        )
                    })}
                </nav>

                <div className="p-4 border-t border-border/50">
                    <div className="flex items-center justify-center lg:justify-start gap-3 text-xs text-muted-foreground">
                        <div className={cn("w-2 h-2 rounded-full animate-pulse", statusColor)} />
                        <span className="hidden lg:block">{statusFormatted}</span>
                    </div>
                </div>
            </aside>

            {/* Mobile Header */}
            <header className="md:hidden fixed top-0 left-0 right-0 h-[calc(4rem+env(safe-area-inset-top))] bg-card/80 backdrop-blur-md border-b border-border/50 z-50 px-4 pt-safe flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <Beer className="w-6 h-6 text-primary" />
                    <div className="flex flex-col">
                        <span className="font-bold text-lg leading-none">Brew Brain</span>
                        <div className="flex items-center gap-1.5 mt-1">
                            <div className={cn("w-1.5 h-1.5 rounded-full animate-pulse", statusColor)} />
                            <span className="text-[10px] text-muted-foreground uppercase tracking-tight font-semibold">Live</span>
                        </div>
                    </div>
                </div>
                <button
                    onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                    className="p-2 -mr-2 text-muted-foreground hover:text-foreground focus-visible:ring-2 focus-visible:ring-primary outline-none"
                    aria-label={mobileMenuOpen ? "Close menu" : "Open menu"}
                >
                    {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
                </button>
            </header>

            {/* Mobile Menu Overlay */}
            {mobileMenuOpen && (
                <div className="md:hidden fixed inset-0 z-40 bg-background/95 backdrop-blur-sm animate-in fade-in slide-in-from-top-10 pt-[calc(5rem+env(safe-area-inset-top))] px-6 pb-6 flex flex-col gap-4">
                    {NAV_ITEMS.map((item) => (
                        <Link
                            key={item.href}
                            href={item.href}
                            onClick={() => setMobileMenuOpen(false)}
                            className={cn(
                                "flex items-center gap-4 p-4 rounded-2xl text-lg font-medium border border-transparent focus-visible:ring-2 focus-visible:ring-primary outline-none",
                                pathname === item.href
                                    ? "bg-primary/10 text-primary border-primary/20"
                                    : "bg-secondary/30 text-foreground"
                            )}
                        >
                            <item.icon className="w-6 h-6" />
                            {item.label}
                        </Link>
                    ))}
                </div>
            )}
            {/* Mobile Bottom Navigation (New) */}
            <nav className="md:hidden fixed bottom-0 left-0 right-0 h-[calc(4rem+env(safe-area-inset-bottom))] bg-card/90 backdrop-blur-lg border-t border-border/50 z-50 pb-safe">
                <div className="flex justify-around items-center h-16">
                    <Link href="/" className={cn("flex items-center justify-center w-full h-full gap-1 flex-col focus-visible:ring-2 focus-visible:ring-primary outline-none", pathname === '/' ? "text-primary" : "text-muted-foreground")}>
                        <LayoutDashboard className="w-5 h-5" />
                        <span className="text-[10px] font-medium">Dashboard</span>
                    </Link>
                    <Link href="/taplist" className={cn("flex items-center justify-center w-full h-full gap-1 flex-col focus-visible:ring-2 focus-visible:ring-primary outline-none", pathname === '/taplist' ? "text-primary" : "text-muted-foreground")}>
                        <Beer className="w-5 h-5" />
                        <span className="text-[10px] font-medium">Taps</span>
                    </Link>
                    <Link href="/chat" className={cn("flex items-center justify-center w-full h-full gap-1 flex-col focus-visible:ring-2 focus-visible:ring-primary outline-none", pathname === '/chat' ? "text-primary" : "text-muted-foreground")}>
                        <Bot className="w-5 h-5" />
                        <span className="text-[10px] font-medium">Brewmaster</span>
                    </Link>
                    <Link href="/settings" className={cn("flex items-center justify-center w-full h-full gap-1 flex-col focus-visible:ring-2 focus-visible:ring-primary outline-none", pathname === '/settings' ? "text-primary" : "text-muted-foreground")}>
                        <Menu className="w-5 h-5" />
                        <span className="text-[10px] font-medium">Settings</span>
                    </Link>
                </div>
            </nav>
        </>
    );
}

export function PageContainer({ children }: { children: React.ReactNode }) {
    return (
        <div className="md:pl-20 lg:pl-64 min-h-screen pt-[calc(4rem+env(safe-area-inset-top))] md:pt-0 pb-[calc(4rem+env(safe-area-inset-bottom)+env(safe-area-inset-bottom))] md:pb-0">
            {children}
        </div>
    );
}
