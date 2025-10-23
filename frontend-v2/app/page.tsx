"use client";

import { useState } from "react";
import { Header } from "@/components/layout/header";
import { Sidebar } from "@/components/layout/sidebar";
import { MainFeed } from "@/components/layout/main-feed";
import { RightSidebar } from "@/components/layout/right-sidebar";
import { mockData } from "@/lib/data/mock-data";
import type { Politician } from "@/types";

export default function Home() {
  const [currentPolitician, setCurrentPolitician] = useState<Politician>(
    mockData.politicians[0]
  );

  return (
    <div className="min-h-screen bg-[hsl(var(--bg-primary))]">
      <Header onPoliticianSelect={setCurrentPolitician} />
      
      <div className="max-w-[1400px] mx-auto px-4 py-4">
        <div className="grid grid-cols-1 lg:grid-cols-[280px_1fr] xl:grid-cols-[280px_1fr_320px] gap-4">
          {/* Left Sidebar */}
          <aside className="hidden lg:block sticky top-[72px] self-start">
            <Sidebar
              politicians={mockData.politicians}
              states={mockData.states}
              currentPoliticianId={currentPolitician.id}
              onPoliticianSelect={setCurrentPolitician}
            />
          </aside>

          {/* Main Feed */}
          <main className="min-w-0">
            <MainFeed
              politician={currentPolitician}
              feedItems={mockData.feedItems.filter(
                (item) => item.politicianId === currentPolitician.id
              )}
              comments={mockData.comments}
            />
          </main>

          {/* Right Sidebar */}
          <aside className="hidden xl:block sticky top-[72px] self-start">
            <RightSidebar />
          </aside>
        </div>
      </div>
    </div>
  );
}
