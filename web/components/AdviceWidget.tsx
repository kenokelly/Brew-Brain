'use client';

import { useState, useEffect } from 'react';
import { cn } from '@/lib/utils';
import Link from 'next/link';
import { Sparkles, RefreshCcw, ChevronRight, MessageSquare, Lightbulb, Loader2 } from 'lucide-react';
import { fetcher } from '@/lib/hooks';

import { AdviceSkeleton } from '@/components/ui/skeleton';

interface AdviceData {
    status: 'success' | 'fallback' | 'error';
    advice: string;
    source?: string;
    generated_at?: string;
}

const SOURCE_TEXT: Record<string, string> = {
    cloud: 'Claude (cloud)',
    ollama: 'Ollama on the Pi',
    template: 'Built-in message',
    pending: 'Still generating',
};

export function AdviceWidget({ className }: { className?: string }) {
    const [advice, setAdvice] = useState<AdviceData | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [showDetails, setShowDetails] = useState(false);

    // refresh=true asks the server for new advice instead of the hour-long cache
    const fetchAdvice = async (refresh = false) => {
        setIsLoading(true);
        try {
            const json = await fetcher<any>(`/api/ai/advice${refresh ? '?refresh=1' : ''}`);
            if (json.status === 'success' && json.data) {
                setAdvice(json.data);
            }
        } catch (error) {
            console.error('Failed to fetch AI advice:', error);
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        fetchAdvice();
    }, []);

    if (isLoading && !advice) {
        return <AdviceSkeleton />;
    }

    if (!advice) {
        return (
            <div className={cn(
                "rounded-2xl p-6 shadow-md border bg-card border-border flex flex-col items-center justify-center gap-2 text-center min-h-[140px]",
                className
            )}>
                <Sparkles className="w-6 h-6 text-muted-foreground opacity-50" />
                <p className="text-sm text-muted-foreground">No advice available right now (the local AI can take up to a couple of minutes to respond).</p>
                <button
                    onClick={() => fetchAdvice(true)}
                    disabled={isLoading}
                    className="text-xs text-primary hover:text-primary/80 transition-colors mt-1 flex items-center gap-1 disabled:opacity-50"
                >
                    {isLoading ? <Loader2 className="w-3 h-3 animate-spin" /> : <RefreshCcw className="w-3 h-3" />} Retry
                </button>
            </div>
        );
    }

    return (
        <div className={cn(
            "group relative overflow-hidden rounded-2xl p-6 shadow-md border transition-all duration-300",
            "bg-card/50 backdrop-blur-md border-purple-500/20 hover:border-purple-500/40",
            className
        )}>
            {/* Header */}
            <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                    <div className="p-2 rounded-xl bg-purple-600/10 text-purple-500">
                        <Sparkles className="w-4 h-4" />
                    </div>
                    <div>
                        <h3 className="text-sm font-bold uppercase tracking-wider text-purple-500">Proactive Advice</h3>
                        <div className="flex items-center gap-1">
                            <span className="text-[10px] text-muted-foreground">Brewmaster Intelligence</span>
                            {advice.source === 'ollama' && (
                                <span className="text-[9px] bg-purple-500/10 text-purple-500 px-1.5 py-0.5 rounded-full font-bold">EDGE</span>
                            )}
                        </div>
                    </div>
                </div>
                <button
                    onClick={() => fetchAdvice(true)}
                    aria-label="Refresh advice"
                    title="Get new advice (can take a minute or two)"
                    disabled={isLoading}
                    className="p-2 rounded-full hover:bg-purple-500/10 text-purple-500 transition-colors disabled:opacity-50"
                >
                    <RefreshCcw className={cn("w-4 h-4", isLoading && "animate-spin")} />
                </button>
            </div>

            {/* Content */}
            <div className="relative z-10">
                <div className="flex gap-3">
                    <div className="shrink-0 mt-1">
                        <Lightbulb className="w-5 h-5 text-amber-400" />
                    </div>
                    <div className="space-y-3">
                        <p className="text-sm leading-relaxed text-foreground/90 whitespace-pre-wrap">
                            {renderBold(advice.advice)}
                        </p>
                        <div className="flex items-center gap-4 pt-2">
                            <Link
                                href={`/chat?q=${encodeURIComponent(`About the dashboard advice: "${advice.advice}" Can you explain this in more detail for my batch?`)}`}
                                className="text-[10px] font-bold text-purple-400 hover:text-purple-300 flex items-center gap-1 transition-colors uppercase tracking-tight"
                            >
                                <MessageSquare className="w-3 h-3" /> Ask Detail
                            </Link>
                            <button
                                type="button"
                                onClick={() => setShowDetails((d) => !d)}
                                aria-expanded={showDetails}
                                className="text-[10px] font-bold text-muted-foreground hover:text-foreground flex items-center gap-1 transition-colors uppercase tracking-tight"
                            >
                                {showDetails ? 'Hide details' : 'Learn More'}
                                <ChevronRight className={cn("w-3 h-3 transition-transform", showDetails && "rotate-90")} />
                            </button>
                        </div>
                        {showDetails && (
                            <div className="text-xs text-muted-foreground space-y-1 border-t border-border/50 pt-2">
                                <p>Based on the live Tilt readings since the log start, the Brewfather fermentation schedule and your batch notes.</p>
                                <p>
                                    From: {SOURCE_TEXT[advice.source || ''] || advice.source || 'unknown'}
                                    {advice.generated_at && ` · ${new Date(advice.generated_at).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' })}`}
                                </p>
                                <p>New advice is generated at most once an hour. Use the refresh button to get it now.</p>
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* Background Decoration */}
            <div className="absolute -bottom-6 -right-6 opacity-[0.03] group-hover:opacity-[0.07] transition-opacity">
                <Sparkles className="w-32 h-32 text-purple-500" />
            </div>
        </div>
    );
}

export default AdviceWidget;

// The AI writes **bold** markdown; show it as bold rather than raw asterisks
function renderBold(text: string) {
    return text.split(/\*\*(.+?)\*\*/g).map((part, i) =>
        i % 2 === 1 ? <strong key={i} className="font-semibold text-foreground">{part}</strong> : part
    );
}
