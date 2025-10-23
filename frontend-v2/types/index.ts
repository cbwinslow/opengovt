export interface Politician {
  id: number;
  name: string;
  role: string;
  party: "Democrat" | "Republican" | "Independent";
  state: string;
  district: string;
  image: string;
  bio: string;
  socialMedia: {
    twitter?: string;
    facebook?: string;
  };
  stats: {
    votesParticipated: number;
    billsSponsored: number;
    voteAlignment: number;
    approval: number;
  };
}

export interface State {
  id: number;
  name: string;
  abbreviation: string;
  governor: string;
  population: string;
  image: string;
  stats: {
    activeBills: number;
    passedThisYear: number;
    budgetBillions: number;
  };
}

export interface VoteData {
  billNumber: string;
  billTitle: string;
  vote: "YEA" | "NAY" | "PRESENT" | "ABSENT";
  result: "PASSED" | "FAILED";
  yeas: number;
  nays: number;
  description: string;
}

export interface SocialData {
  platform: "twitter" | "facebook";
  content: string;
}

export interface KPI {
  label: string;
  value: string;
  trend: "up" | "down" | "stable";
}

export interface AnalyticsData {
  title: string;
  kpis: KPI[];
  summary: string;
}

export interface ResearchData {
  title: string;
  author: string;
  findings: string[];
  methodology: string;
}

export type FeedItemType = "vote" | "social" | "analytics" | "research";

export interface FeedItem {
  id: number;
  politicianId: number;
  type: FeedItemType;
  timestamp: Date;
  vote?: VoteData;
  social?: SocialData;
  analytics?: AnalyticsData;
  research?: ResearchData;
  likes: number;
  comments: Comment[];
}

export interface Comment {
  id: number;
  author: string;
  content: string;
  timestamp: Date;
  likes: number;
}

export interface MockData {
  politicians: Politician[];
  states: State[];
  feedItems: FeedItem[];
  comments: Record<number, Comment[]>;
}
