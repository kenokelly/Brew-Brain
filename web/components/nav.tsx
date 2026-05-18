'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import { LayoutDashboard, Beer, Bot, Menu, X } from 'lucide-react';
import { ConnectionStatus, MobileConnectionStatus } from './nav/ConnectionStatus';
import { NAV_ITEMS, SidebarItem, MobileMenuItem } from './nav/NavItems';
import { ThemeToggle } from './theme-toggle';

export function NavBar() {
    const pathname = usePathname();
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

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
                    {NAV_ITEMS.map((item) => (
                        <SidebarItem key={item.href} {...item} />
                    ))}
                </nav>

                <div className="p-4 border-t border-border/50 flex flex-col gap-4">
                    <div className="flex items-center justify-between lg:justify-center w-full">
                         <span className="hidden lg:block text-xs font-semibold text-muted-foreground uppercase tracking-wider">Appearance</span>
                         <ThemeToggle />
                    </div>
                    <ConnectionStatus />
                </div>
            </aside>

            {/* Mobile Header */}
            <header className="md:hidden fixed top-0 left-0 right-0 h-[calc(4rem+env(safe-area-inset-top))] bg-card/80 backdrop-blur-md border-b border-border/50 z-50 px-4 pt-safe flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <Beer className="w-6 h-6 text-primary" />
                    <div className="flex flex-col">
                        <span className="font-bold text-lg leading-none">Brew Brain</span>
                        <MobileConnectionStatus />
                    </div>
                </div>
                <div className="flex items-center gap-2">
                    <ThemeToggle />
                    <button
                        onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                        className="p-2 -mr-2 text-muted-foreground hover:text-foreground focus-visible:ring-2 focus-visible:ring-primary outline-none"
                        aria-label={mobileMenuOpen ? "Close menu" : "Open menu"}
                    >
                        {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
                    </button>
                </div>
            </header>

            {/* Mobile Menu Overlay */}
            {mobileMenuOpen && (
                <div className="md:hidden fixed inset-0 z-40 bg-background/95 backdrop-blur-sm animate-in fade-in slide-in-from-top-10 pt-[calc(5rem+env(safe-area-inset-top))] px-6 pb-6 flex flex-col gap-4">
                    {NAV_ITEMS.map((item) => (
                        <MobileMenuItem 
                            key={item.href} 
                            {...item} 
                            onClick={() => setMobileMenuOpen(false)} 
                        />
                    ))}
                </div>
            )}
            {/* Mobile Bottom Navigation */}
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
