import type { Metadata } from "next";
import "./globals.css";


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
