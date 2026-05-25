"use client";

import { useState, useEffect } from "react";
import { Capacitor } from "@capacitor/core";
import { BarcodeScanner } from "@capacitor-mlkit/barcode-scanning";
import { ScanLine, Plus, X, Server, Save } from "lucide-react";
import toast from "react-hot-toast";
import { apiFetch } from "@/lib/api";

export default function BarcodeInventoryScanner({ onComplete }: { onComplete?: () => void }) {
    const [isSupported, setIsSupported] = useState(false);
    const [scanning, setScanning] = useState(false);
    
    // Modal State
    const [scannedCode, setScannedCode] = useState<string | null>(null);
    const [category, setCategory] = useState("hops");
    const [name, setName] = useState("");
    const [amount, setAmount] = useState("");
    const [unit, setUnit] = useState("g");
    
    const [submitting, setSubmitting] = useState(false);

    useEffect(() => {
        if (Capacitor.isNativePlatform()) {
            BarcodeScanner.isSupported().then((result) => {
                setIsSupported(result.supported);
            });
        }
    }, []);

    const handleScan = async () => {
        if (!Capacitor.isNativePlatform() || !isSupported) {
            // Mock scan for desktop testing
            setScannedCode("MOCK-123456789");
            prefillForm("MOCK-123456789");
            return;
        }

        try {
            setScanning(true);
            const { camera } = await BarcodeScanner.requestPermissions();
            if (camera !== 'granted' && camera !== 'limited') {
                toast.error("Camera permission is required to scan barcodes.");
                setScanning(false);
                return;
            }

            const { barcodes } = await BarcodeScanner.scan();
            if (barcodes.length > 0) {
                const code = barcodes[0].rawValue || "UNKNOWN";
                setScannedCode(code);
                prefillForm(code);
            }
        } catch (e: any) {
            toast.error(`Scan failed: ${e.message}`);
        } finally {
            setScanning(false);
        }
    };
    
    const prefillForm = (code: string) => {
        // Look up learned barcodes from local storage (or a new API endpoint)
        try {
            const learned = localStorage.getItem(`barcode_${code}`);
            if (learned) {
                const data = JSON.parse(learned);
                setCategory(data.category || "hops");
                setName(data.name || "");
                setUnit(data.unit || "g");
                toast.success("Product recognized!");
            } else {
                toast("New product. Please enter details.");
            }
        } catch (e) {}
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!name || !amount) {
            toast.error("Name and amount are required.");
            return;
        }

        setSubmitting(true);
        const toastId = toast.loading("Adding to Brewfather...");
        
        try {
            const payload = {
                category: category,
                item: {
                    name: name,
                    amount: parseFloat(amount),
                    unit: unit,
                    inventory: parseFloat(amount)
                }
            };
            
            // For yeast and miscs, Brewfather schema expects specific casing
            // This is a simplified payload, the API handles the category routing.
            
            await apiFetch("/api/automation/inventory/add", {
                method: "POST",
                body: payload
            });
            
            toast.success("Added to inventory!", { id: toastId });
            
            // Save learning
            if (scannedCode) {
                localStorage.setItem(`barcode_${scannedCode}`, JSON.stringify({ category, name, unit }));
            }
            
            // Reset
            setScannedCode(null);
            setName("");
            setAmount("");
            if (onComplete) onComplete();
            
        } catch (e: any) {
            toast.error(`Failed: ${e.message}`, { id: toastId });
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <>
            <button
                onClick={handleScan}
                disabled={scanning}
                className="flex items-center gap-2 bg-primary text-primary-foreground px-4 py-2 rounded-lg hover:bg-primary/90 transition-colors font-semibold"
            >
                <ScanLine className="w-5 h-5" />
                {scanning ? "Scanning..." : "Scan Item"}
            </button>

            {scannedCode && (
                <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4 animate-in fade-in">
                    <div className="bg-card border border-border w-full max-w-md rounded-2xl shadow-2xl overflow-hidden flex flex-col">
                        <div className="p-4 border-b border-border/50 flex justify-between items-center bg-secondary/20">
                            <h3 className="font-bold flex items-center gap-2">
                                <ScanLine className="w-5 h-5 text-primary" />
                                Add to Inventory
                            </h3>
                            <button onClick={() => setScannedCode(null)} className="p-2 hover:bg-secondary rounded-lg">
                                <X className="w-5 h-5" />
                            </button>
                        </div>
                        
                        <form onSubmit={handleSubmit} className="p-6 space-y-4">
                            <div className="bg-secondary/30 p-3 rounded-lg border border-border/50 font-mono text-xs text-muted-foreground flex items-center justify-between">
                                <span>Barcode:</span>
                                <span className="font-bold text-foreground">{scannedCode}</span>
                            </div>

                            <div className="space-y-1">
                                <label className="text-xs font-bold text-muted-foreground uppercase">Category</label>
                                <select 
                                    value={category}
                                    onChange={(e) => setCategory(e.target.value)}
                                    className="w-full bg-secondary text-foreground p-3 rounded-lg border border-border/50 outline-none focus:border-primary"
                                >
                                    <option value="hops">Hops</option>
                                    <option value="fermentables">Fermentables</option>
                                    <option value="yeasts">Yeast</option>
                                    <option value="miscs">Misc (Salts, Additions)</option>
                                </select>
                            </div>

                            <div className="space-y-1">
                                <label className="text-xs font-bold text-muted-foreground uppercase">Product Name</label>
                                <input 
                                    type="text" 
                                    placeholder="e.g., Citra Pellets, Maris Otter"
                                    value={name}
                                    onChange={(e) => setName(e.target.value)}
                                    className="w-full bg-secondary text-foreground p-3 rounded-lg border border-border/50 outline-none focus:border-primary"
                                    required
                                />
                            </div>

                            <div className="flex gap-4">
                                <div className="space-y-1 flex-1">
                                    <label className="text-xs font-bold text-muted-foreground uppercase">Amount</label>
                                    <input 
                                        type="number" 
                                        step="0.01"
                                        placeholder="0"
                                        value={amount}
                                        onChange={(e) => setAmount(e.target.value)}
                                        className="w-full bg-secondary text-foreground p-3 rounded-lg border border-border/50 outline-none focus:border-primary"
                                        required
                                    />
                                </div>
                                <div className="space-y-1 w-24">
                                    <label className="text-xs font-bold text-muted-foreground uppercase">Unit</label>
                                    <select 
                                        value={unit}
                                        onChange={(e) => setUnit(e.target.value)}
                                        className="w-full bg-secondary text-foreground p-3 rounded-lg border border-border/50 outline-none focus:border-primary"
                                    >
                                        <option value="g">g</option>
                                        <option value="kg">kg</option>
                                        <option value="oz">oz</option>
                                        <option value="lbs">lbs</option>
                                        <option value="pkg">pkg</option>
                                        <option value="items">items</option>
                                    </select>
                                </div>
                            </div>

                            <div className="pt-4 flex gap-3">
                                <button
                                    type="button"
                                    onClick={() => setScannedCode(null)}
                                    className="flex-1 px-4 py-3 bg-secondary hover:bg-secondary/80 text-foreground font-bold rounded-lg transition-colors"
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    disabled={submitting}
                                    className="flex-2 flex items-center justify-center gap-2 px-6 py-3 bg-primary hover:bg-primary/90 text-primary-foreground font-bold rounded-lg transition-colors disabled:opacity-50 w-[60%]"
                                >
                                    {submitting ? "Saving..." : "Add to Brewfather"}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </>
    );
}
