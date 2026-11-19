import type { Metadata } from "next";
import { Bricolage_Grotesque, DM_Mono } from "next/font/google";

// Fonts are scoped to the /beta route only, so the rest of the app is unaffected.
const bricolage = Bricolage_Grotesque({
  subsets: ["latin"],
  variable: "--bh-font-sans",
});

const dmMono = DM_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--bh-font-mono",
});

export const metadata: Metadata = {
  title: "Brew Brain · Beta: Brewhouse",
};

export default function BetaLayout({ children }: { children: React.ReactNode }) {
  return <div className={`${bricolage.variable} ${dmMono.variable}`}>{children}</div>;
}
