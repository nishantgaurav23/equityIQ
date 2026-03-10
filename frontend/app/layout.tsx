import type { Metadata } from "next";
import Link from "next/link";
import { Plus_Jakarta_Sans, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const jakartaSans = Plus_Jakarta_Sans({
  variable: "--font-jakarta",
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700", "800"],
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-jetbrains",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
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
        className={`${jakartaSans.variable} ${jetbrainsMono.variable} antialiased min-h-screen flex flex-col`}
      >
        {/* Background orbs */}
        <div className="bg-orb bg-orb-1" />
        <div className="bg-orb bg-orb-2" />

        <header className="sticky top-0 z-50 glass-dark border-b border-zinc-800/50 px-6 py-3.5">
          <nav className="max-w-7xl mx-auto flex items-center justify-between">
            <Link href="/" className="flex items-center gap-2.5 group">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-amber-500 to-rose-600 flex items-center justify-center text-white font-bold text-xs tracking-tight">
                EQ
              </div>
              <span className="text-lg font-extrabold gradient-text group-hover:opacity-80 transition-opacity tracking-tight">
                EquityIQ
              </span>
            </Link>
            <div className="flex items-center gap-7">
              <Link
                href="/chat"
                className="text-[13px] font-medium text-zinc-400 hover:text-white transition-colors"
              >
                Chat
              </Link>
              <Link
                href="/compare"
                className="text-[13px] font-medium text-zinc-400 hover:text-white transition-colors"
              >
                Compare
              </Link>
              <Link
                href="/history"
                className="text-[13px] font-medium text-zinc-400 hover:text-white transition-colors"
              >
                History
              </Link>
              <span className="text-[11px] font-semibold px-3 py-1 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20 tracking-wide">
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
