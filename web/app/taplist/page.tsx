'use client';

export default function TapListPage() {
    return (
        <div className="h-[calc(100vh-6rem)] w-full rounded-3xl overflow-hidden border border-border/50 shadow-lg bg-card/50 backdrop-blur-sm">
            <iframe
                src="/static/taplist.html"
                className="w-full h-full border-none bg-white/90"
                title="Tap List"
            />
        </div>
    );
}
