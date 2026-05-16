'use client';

interface StatisticalGridProps {
    tempZScore?: number;
    sgRateZScore?: number;
}

export function StatisticalGrid({ tempZScore, sgRateZScore }: StatisticalGridProps) {
    if (tempZScore === undefined && sgRateZScore === undefined) return null;

    return (
        <div className="p-4 rounded-xl bg-secondary/20 mb-4">
            <h3 className="text-sm font-medium text-muted-foreground mb-2">Statistical Analysis</h3>
            <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                    <div className="text-muted-foreground">Temp Z-Score</div>
                    <div className="text-lg font-semibold">
                        {tempZScore?.toFixed(2) ?? '--'}
                    </div>
                </div>
                <div>
                    <div className="text-muted-foreground">SG Rate Z-Score</div>
                    <div className="text-lg font-semibold">
                        {sgRateZScore?.toFixed(2) ?? '--'}
                    </div>
                </div>
            </div>
        </div>
    );
}
