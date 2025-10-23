"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useTheme } from "@/lib/themes/theme-provider";
import Link from "next/link";

export default function Home() {


  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="border-b bg-card">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-primary to-primary/60 flex items-center justify-center text-2xl">
              🐙
            </div>
            <div>
              <h1 className="text-2xl font-bold">OpenGovt</h1>
              <p className="text-xs text-muted-foreground">Political Transparency Platform</p>
            </div>
          </div>
          <div className="flex gap-2">
            <Link href="/settings">
              <Button variant="outline">⚙️ Settings</Button>
            </Link>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="container mx-auto px-4 py-16 text-center">
        <h1 className="text-5xl font-bold mb-4">
          Political Transparency,{" "}
          <span className="text-primary">Simplified</span>
        </h1>
        <p className="text-xl text-muted-foreground mb-8 max-w-2xl mx-auto">
          Track politicians, voting records, and government activity with complete transparency and accountability.
        </p>
        <div className="flex gap-4 justify-center">

          <Link href="/settings">
            <Button size="lg" variant="outline">Customize Theme</Button>
          </Link>
        </div>
      </section>

      {/* Features */}
      <section className="container mx-auto px-4 py-16">
        <h2 className="text-3xl font-bold text-center mb-12">Key Features</h2>
        <div className="grid md:grid-cols-3 gap-6">
          <Card>
            <CardHeader>
              <div className="text-4xl mb-2">🗳️</div>
              <CardTitle>Voting Records</CardTitle>
              <CardDescription>
                Complete legislative voting history with bill details and outcomes
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                Track how your representatives vote on every bill with full transparency.
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div className="text-4xl mb-2">📊</div>
              <CardTitle>Analytics & KPIs</CardTitle>
              <CardDescription>
                Performance metrics and voting consistency analysis
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                Data-driven insights into politician behavior and effectiveness.
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div className="text-4xl mb-2">💬</div>
              <CardTitle>Public Discussion</CardTitle>
              <CardDescription>
                Comment and engage in political discourse
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                Join the conversation and share your perspective on political issues.
              </p>
            </CardContent>
          </Card>
        </div>
      </section>

      {/* Theme Demo */}
      <section className="container mx-auto px-4 py-16">
        <Card className="max-w-3xl mx-auto">
          <CardHeader>
            <CardTitle>🎨 Current Theme: {currentTheme.name}</CardTitle>
            <CardDescription>
              Customize your experience with multiple themes, font sizes, and dark mode
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex gap-2 flex-wrap">
              <div className="flex-1 min-w-[100px] p-4 rounded" style={{ background: `hsl(var(--primary))`, color: `hsl(var(--primary-foreground))` }}>
                Primary
              </div>
              <div className="flex-1 min-w-[100px] p-4 rounded" style={{ background: `hsl(var(--secondary))`, color: `hsl(var(--secondary-foreground))` }}>
                Secondary
              </div>
              <div className="flex-1 min-w-[100px] p-4 rounded" style={{ background: `hsl(var(--accent))`, color: `hsl(var(--accent-foreground))` }}>
                Accent
              </div>
            </div>
            <div className="flex gap-2 flex-wrap">
              <div className="flex-1 min-w-[100px] p-4 rounded" style={{ background: `hsl(var(--democrat))`, color: 'white' }}>
                Democrat
              </div>
              <div className="flex-1 min-w-[100px] p-4 rounded" style={{ background: `hsl(var(--republican))`, color: 'white' }}>
                Republican
              </div>
              <div className="flex-1 min-w-[100px] p-4 rounded" style={{ background: `hsl(var(--independent))`, color: 'white' }}>
                Independent
              </div>
            </div>
            <Link href="/settings">
              <Button className="w-full">Customize in Settings →</Button>
            </Link>
          </CardContent>
        </Card>
      </section>

      {/* CTA */}
      <section className="container mx-auto px-4 py-16 text-center">
        <Card className="max-w-2xl mx-auto bg-primary text-primary-foreground">
          <CardHeader>
            <CardTitle className="text-3xl">Ready to Get Started?</CardTitle>
            <CardDescription className="text-primary-foreground/80">
              Join thousands tracking government accountability
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="mb-6">
              Click the octopus in the bottom-right corner to chat with Octo, your guide!
            </p>
            <Button variant="secondary" size="lg">
              Explore Politicians
            </Button>
          </CardContent>
        </Card>
      </section>

      {/* Footer */}
      <footer className="border-t py-8 text-center text-sm text-muted-foreground">
        <div className="container mx-auto px-4">
          <p>© 2025 OpenGovt - Political Transparency Platform</p>
          <p className="mt-2">Making government transparent and accessible</p>
        </div>
      </footer>
    </div>
  );
}
