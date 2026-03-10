import type { Metadata } from "next";
import Link from "next/link";
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

export const metadata: Metadata = {
  title: "EquityIQ",
  description: "Multi-agent stock intelligence system",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased min-h-screen flex flex-col`}
      >
        {/* Background orbs */}
        <div className="bg-orb bg-orb-1" />
        <div className="bg-orb bg-orb-2" />

        <header className="sticky top-0 z-50 glass-dark border-b border-zinc-800/50 px-6 py-3">
          <nav className="max-w-7xl mx-auto flex items-center justify-between">
            <Link href="/" className="flex items-center gap-2 group">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-amber-500 to-rose-600 flex items-center justify-center text-white font-bold text-sm">
                EQ
              </div>
              <span className="text-lg font-bold gradient-text group-hover:opacity-80 transition-opacity">
                EquityIQ
              </span>
            </Link>
            <div className="flex items-center gap-6">
              <Link
                href="/chat"
                className="text-sm text-zinc-400 hover:text-white transition-colors"
              >
                Chat
              </Link>
              <Link
                href="/compare"
                className="text-sm text-zinc-400 hover:text-white transition-colors"
              >
                Compare
              </Link>
              <Link
                href="/history"
                className="text-sm text-zinc-400 hover:text-white transition-colors"
              >
                History
              </Link>
              <span className="text-xs px-3 py-1 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20">
                7 AI Agents
              </span>
            </div>
          </nav>
        </header>

        <main className="flex-1 max-w-7xl mx-auto w-full px-6 py-8">
          {children}
        </main>

        <footer className="border-t border-zinc-800/50 px-6 py-4">
          <div className="max-w-7xl mx-auto flex items-center justify-between text-xs text-zinc-500">
            <span>EquityIQ — Multi-Agent Stock Intelligence</span>
            <div className="flex items-center gap-4">
              <span className="text-zinc-600">US + India Markets</span>
              <span className="text-zinc-600">Gemini Flash</span>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
