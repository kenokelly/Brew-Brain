'use client';

export default function KioskPage() {
    // Kiosk often hides the nav, but here we keep it consistent or we could hide it via layout config if needed.
    // For now, wrapper.
    return (
        <div className="h-[calc(100vh-6rem)] w-full rounded-3xl overflow-hidden border border-border/50 shadow-lg bg-card/50 backdrop-blur-sm">
            <iframe
                src="/static/kiosk.html"
                className="w-full h-full border-none bg-white/90"
                title="Kiosk Mode"
            />
        </div>
    );
}
