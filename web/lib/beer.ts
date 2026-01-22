export const SRM_COLORS: { [key: number]: string } = {
    1: "#FFE699",
    2: "#FFD878",
    3: "#FFCA5A",
    4: "#FFBF42",
    5: "#FBB123",
    6: "#F8A600",
    7: "#F39C00",
    8: "#EA8F00",
    9: "#E58500",
    10: "#DE7C00",
    11: "#D77200",
    12: "#CF6900",
    13: "#CB6200",
    14: "#C35900",
    15: "#BB5100",
    16: "#B54C00",
    17: "#B04500",
    18: "#A63E00",
    19: "#A13700",
    20: "#9B3200",
    21: "#952D00",
    22: "#8E2900",
    23: "#882300",
    24: "#821E00",
    25: "#7B1A00",
    26: "#771900",
    27: "#701400",
    28: "#6A0E00",
    29: "#660D00",
    30: "#5E0B00",
    35: "#530A00",
    40: "#4C0500", // Stout/Porter
    50: "#3D0300"  // Black
};

export function getSrmColor(srm: number | string | undefined): string {
    if (!srm) return "#FBB123"; // Default Gold (SRM 5)

    const srmVal = typeof srm === 'string' ? parseInt(srm) : srm;
    if (isNaN(srmVal)) return "#FBB123";

    if (srmVal in SRM_COLORS) return SRM_COLORS[srmVal];

    // Find closest
    let closest = 5;
    let minDiff = 100;
    for (const key in SRM_COLORS) {
        const k = parseInt(key);
        const diff = Math.abs(k - srmVal);
        if (diff < minDiff) {
            minDiff = diff;
            closest = k;
        }
    }
    return SRM_COLORS[closest];
}
