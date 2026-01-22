import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

import { SocketProvider } from "@/lib/socket";
import { NavBar, PageContainer } from "@/components/nav";

export const metadata: Metadata = {
  title: "Brew Brain",
  description: "Autonomous Fermentation Intelligence",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased bg-background text-foreground`}
      >
        <SocketProvider>
          <NavBar />
          <PageContainer>
            {children}
          </PageContainer>
        </SocketProvider>
      </body>
    </html>
  );
}
