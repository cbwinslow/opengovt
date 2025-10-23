import type { Metadata } from "next";
import "./globals.css";
import dynamic from "next/dynamic";
// Lazy-load optional features that may be missing to prevent runtime errors
const ThemeProvider = dynamic(() => import("@/lib/themes/theme-provider").then(m => m.ThemeProvider), {
  ssr: false,
  loading: () => <>{/* theme provider loading noop */}</>,
});
const OctopusMascot = dynamic(() => import("@/components/mascot/octopus-mascot").then(m => m.OctopusMascot), {
  ssr: false,
  loading: () => null,
});

export const metadata: Metadata = {
  title: "OpenGovt - Political Transparency Platform",
  description: "Track politicians, voting records, and government activity with transparency and accountability",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="antialiased">
        <ThemeProvider>
          {children}
          <OctopusMascot />
        </ThemeProvider>
      </body>
    </html>
  );
}
