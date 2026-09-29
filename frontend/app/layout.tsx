import type { Metadata } from "next";
import "./globals.css";
import { WalletProvider } from "@/lib/wallet/WalletProvider";
import { SiteHeader } from "@/components/SiteHeader";
import { SiteFooter } from "@/components/SiteFooter";

export const metadata: Metadata = {
  title: "WeatherCover — Weather conditions verified. Coverage decisions automated.",
  description:
    "Parametric weather coverage built on WeatherResolve, a real-world observation resolution layer on GenLayer. Not a weather API dashboard — a verified condition resolution and coverage application.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <WalletProvider>
          <SiteHeader />
          <main className="mx-auto min-h-[70vh] max-w-6xl px-4 py-8 sm:px-6 sm:py-10">{children}</main>
          <SiteFooter />
        </WalletProvider>
      </body>
    </html>
  );
}
