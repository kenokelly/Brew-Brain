'use client';

import { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Sparkles, ChevronLeft, Loader2 } from 'lucide-react';
import Link from 'next/link';
import { cn } from '@/lib/utils';
import { apiFetch } from '@/lib/api';

interface Message {
    role: 'user' | 'assistant';
    content: string;
}

export default function ChatPage() {
    const [messages, setMessages] = useState<Message[]>([
        { role: 'assistant', content: 'Hello! I am your Brewmaster AI. How can I help with your fermentation today?' }
    ]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const scrollRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [messages]);

    const handleSend = async () => {
        if (!input.trim() || loading) return;

        const userMsg = input.trim();
        setInput('');
        setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
        setLoading(true);

        try {
            const data: any = await apiFetch('/api/ai/chat', {
                method: 'POST',
                body: { message: userMsg }
            });

            if (data.status === 'success' || data.status === 'fallback') {
                setMessages(prev => [...prev, { role: 'assistant', content: data.response }]);
            } else {
                setMessages(prev => [...prev, { role: 'assistant', content: 'Sorry, I encountered an error processing your request.' }]);
            }
        } catch (err) {
            setMessages(prev => [...prev, { role: 'assistant', content: 'Connection to Brewmaster failed. Is Ollama running?' }]);
        } finally {
            setLoading(false);
        }
    };

    return (
        <main className="flex flex-col h-[calc(100vh-4rem)] md:h-screen bg-background text-foreground overflow-hidden">
            {/* Header */}
            <header className="flex items-center justify-between p-4 border-b border-border/50 bg-background/80 backdrop-blur-md sticky top-0 z-10">
                <div className="flex items-center gap-3">
                    <Link href="/" className="p-2 rounded-full hover:bg-secondary transition-colors md:hidden">
                        <ChevronLeft className="w-5 h-5" />
                    </Link>
                    <div className="bg-purple-600/10 p-2 rounded-xl">
                        <Bot className="w-6 h-6 text-purple-500" />
                    </div>
                    <div>
                        <h1 className="font-bold tracking-tight">Brewmaster AI</h1>
                        <div className="flex items-center gap-1.5">
                            <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                            <span className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider">Local Ollama Active</span>
                        </div>
                    </div>
                </div>
            </header>

            {/* Chat Window */}
            <div 
                ref={scrollRef}
                className="flex-1 overflow-y-auto p-4 md:p-6 space-y-6"
            >
                {messages.map((msg, i) => (
                    <div 
                        key={i} 
                        className={cn(
                            "flex items-start gap-3 max-w-[85%] animate-in fade-in slide-in-from-bottom-2 duration-300",
                            msg.role === 'user' ? "ml-auto flex-row-reverse" : ""
                        )}
                    >
                        <div className={cn(
                            "p-2 rounded-xl shrink-0",
                            msg.role === 'user' ? "bg-primary/10" : "bg-purple-600/10"
                        )}>
                            {msg.role === 'user' ? <User className="w-5 h-5 text-primary" /> : <Sparkles className="w-5 h-5 text-purple-500" />}
                        </div>
                        <div className={cn(
                            "p-4 rounded-2xl text-sm leading-relaxed",
                            msg.role === 'user' 
                                ? "bg-primary text-primary-foreground rounded-tr-none" 
                                : "bg-card border border-border/50 rounded-tl-none shadow-sm"
                        )}>
                            {msg.content}
                        </div>
                    </div>
                ))}
                {loading && (
                    <div className="flex items-start gap-3 max-w-[85%] animate-pulse">
                        <div className="bg-purple-600/10 p-2 rounded-xl">
                            <Bot className="w-5 h-5 text-purple-500" />
                        </div>
                        <div className="bg-card border border-border/50 p-4 rounded-2xl rounded-tl-none">
                            <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
                        </div>
                    </div>
                )}
            </div>

            {/* Input Area */}
            <div className="p-4 md:p-6 border-t border-border/50 bg-background/80 backdrop-blur-md">
                <div className="max-w-4xl mx-auto relative">
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                        placeholder="Ask the Brewmaster..."
                        className="w-full bg-secondary/50 border border-border/50 rounded-2xl px-5 py-4 pr-14 focus:ring-2 focus:ring-purple-500/20 outline-none transition-all shadow-inner"
                    />
                    <button
                        onClick={handleSend}
                        disabled={!input.trim() || loading}
                        className="absolute right-2 top-2 bottom-2 px-4 rounded-xl bg-purple-600 text-white hover:bg-purple-500 transition-colors disabled:opacity-50 disabled:grayscale"
                    >
                        <Send className="w-4 h-4" />
                    </button>
                </div>
                <p className="text-[10px] text-center text-muted-foreground mt-3">
                    Brewmaster uses your real-time batch data to provide context-aware advice.
                </p>
            </div>
        </main>
    );
}
