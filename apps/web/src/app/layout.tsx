import type { Metadata } from "next";
import { Figtree, Fraunces } from "next/font/google";

import { AppShell } from "@/components/layout/AppShell";
import "./globals.css";

const figtree = Figtree({
  variable: "--font-figtree",
  subsets: ["latin"],
});

const fraunces = Fraunces({
  variable: "--font-fraunces",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "ZooLog AI",
  description:
    "AI agent for animal observation journals from video footage.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${figtree.variable} ${fraunces.variable} h-full antialiased`}
    >
      <body className="min-h-full font-sans text-ink">
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
