'use client';

import { Book, Compass, Cpu, Info, Search, Code, AlertCircle, Home, Database, Thermometer, Bot, Zap, Calculator } from 'lucide-react';
import { Tooltip } from '@/components/ui/Tooltip';

export default function HelpPage() {
    return (
        <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 pb-12">
            <div className="bg-card/50 p-8 rounded-2xl border border-white/5 shadow-2xl">
                <h1 className="text-4xl font-extrabold mb-4 flex items-center gap-4 text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-purple-500">
                    <Book className="w-10 h-10 text-blue-400" />
                    Brew-Brain Documentation
                </h1>
                <p className="text-muted-foreground text-lg mb-8 leading-relaxed">
                    Welcome to your central command center for homebrewing. Brew-Brain integrates real-time hardware telemetry with advanced recipe planning and a conversational AI Brewmaster to guide your fermentation.
                </p>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                    {/* Dashboard & Telemetry */}
                    <div className="p-6 bg-black/20 rounded-xl border border-white/5 transition-transform hover:scale-[1.02]">
                        <h2 className="text-xl font-bold mb-4 flex items-center gap-3 text-emerald-400">
                            <Thermometer className="w-6 h-6" />
                            Dashboard & Telemetry
                        </h2>
                        <ul className="space-y-4 text-sm text-muted-foreground">
                            <li>
                                <strong className="text-white block mb-1">Tilt & DS18B20 Integration</strong>
                                The dashboard automatically polls your Bluetooth Tilt Hydrometer and ambient temperature probes to track fermentation in real-time.
                            </li>
                            <li>
                                <strong className="text-white block mb-1">Real-Time ABV Calculation</strong>
                                By providing your Original Gravity (OG) in the Settings page, the dashboard dynamically calculates your current ABV as fermentation progresses.
                            </li>
                        </ul>
                    </div>

                    {/* Automation Hub */}
                    <div className="p-6 bg-black/20 rounded-xl border border-white/5 transition-transform hover:scale-[1.02]">
                        <h2 className="text-xl font-bold mb-4 flex items-center gap-3 text-purple-400">
                            <Zap className="w-6 h-6" />
                            Automation Hub
                        </h2>
                        <ul className="space-y-4 text-sm text-muted-foreground">
                            <li>
                                <strong className="text-white block mb-1">Ingredient Scout & Sourcing</strong>
                                Compare live prices across The Malt Miller and Get Er Brewed. Upload a deficit JSON to automatically generate an optimized shopping basket.
                            </li>
                            <li>
                                <strong className="text-white block mb-1">Calculators</strong>
                                <div className="grid grid-cols-2 gap-2 mt-2">
                                    <span className="bg-white/5 px-2 py-1 rounded text-xs flex items-center gap-1"><Calculator className="w-3 h-3"/> Refractometer</span>
                                    <span className="bg-white/5 px-2 py-1 rounded text-xs flex items-center gap-1"><Calculator className="w-3 h-3"/> IBU Scaler</span>
                                    <span className="bg-white/5 px-2 py-1 rounded text-xs flex items-center gap-1"><Calculator className="w-3 h-3"/> Carbonation</span>
                                    <span className="bg-white/5 px-2 py-1 rounded text-xs flex items-center gap-1"><Calculator className="w-3 h-3"/> Priming Sugar</span>
                                </div>
                            </li>
                        </ul>
                    </div>

                    {/* AI Brewmaster */}
                    <div className="p-6 bg-black/20 rounded-xl border border-white/5 transition-transform hover:scale-[1.02]">
                        <h2 className="text-xl font-bold mb-4 flex items-center gap-3 text-orange-400">
                            <Bot className="w-6 h-6" />
                            AI Brewmaster
                        </h2>
                        <ul className="space-y-4 text-sm text-muted-foreground">
                            <li>
                                <strong className="text-white block mb-1">Context-Aware Assistance</strong>
                                The AI reads your current batch settings (SG, Temp, Style) directly from the database and provides tailored advice.
                            </li>
                            <li>
                                <strong className="text-white block mb-1">Graceful Degradation</strong>
                                If your local LLM (Ollama) is offline, the interface seamlessly falls back to a template response, preventing application crashes.
                            </li>
                        </ul>
                    </div>

                    {/* Settings & System */}
                    <div className="p-6 bg-black/20 rounded-xl border border-white/5 transition-transform hover:scale-[1.02]">
                        <h2 className="text-xl font-bold mb-4 flex items-center gap-3 text-blue-400">
                            <Database className="w-6 h-6" />
                            Settings & System
                        </h2>
                        <ul className="space-y-4 text-sm text-muted-foreground">
                            <li>
                                <strong className="text-white block mb-1">API Configuration</strong>
                                Connect your Brewfather account, SerpAPI key (for pricing), and Telegram Bot token directly from the Settings page.
                            </li>
                            <li>
                                <strong className="text-white block mb-1">Keg Label Generation</strong>
                                Easily generate and print HTML/PDF keg labels based on your active batch's metadata.
                            </li>
                        </ul>
                    </div>
                </div>
            </div>

            {/* Troubleshooting & FAQ */}
            <div className="bg-blue-500/10 border border-blue-500/20 p-8 rounded-2xl flex flex-col md:flex-row items-start gap-6 shadow-lg">
                <AlertCircle className="w-10 h-10 text-blue-400 flex-shrink-0 mt-1" />
                <div className="space-y-4 w-full">
                    <h3 className="text-2xl font-bold text-blue-400 mb-2">Troubleshooting Guide</h3>
                    
                    <div className="space-y-4">
                        <div className="bg-black/30 p-4 rounded-lg">
                            <h4 className="font-bold text-white mb-1">AI Chat responds with "Brewmaster is currently offline"</h4>
                            <p className="text-sm text-blue-200">
                                This occurs when the `ollama` container is not running, or the `llama3` model has not been pulled. Connect to your host machine and run `docker exec -it ollama ollama run llama3` to initialize it.
                            </p>
                        </div>
                        
                        <div className="bg-black/30 p-4 rounded-lg">
                            <h4 className="font-bold text-white mb-1">Calculators or Ingredient Scout display a red error toast</h4>
                            <p className="text-sm text-blue-200">
                                Verify that your SerpAPI key is correctly saved in Settings. The backend will return a 400 error if external scraping requires a key that is missing.
                            </p>
                        </div>

                        <div className="bg-black/30 p-4 rounded-lg">
                            <h4 className="font-bold text-white mb-1">Not receiving Telegram updates</h4>
                            <p className="text-sm text-blue-200">
                                Telegram updates will not trigger during the configured "Quiet Hours" (e.g., 23:00 to 07:00). Ensure your `TELEGRAM_TOKEN` and `TELEGRAM_CHAT_ID` are valid.
                            </p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
