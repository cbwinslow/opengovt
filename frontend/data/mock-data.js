// Mock data for politicians, states, and feed items
const mockData = {
  politicians: [
    {
      id: 1,
      name: "Senator Jane Smith",
      role: "U.S. Senator",
      party: "Democrat",
      state: "California",
      district: "At-Large",
      image: "https://via.placeholder.com/150?text=JS",
      bio: "Serving the people of California since 2015. Fighting for healthcare, climate action, and economic equality.",
      socialMedia: {
        twitter: "@senatorjsmith",
        facebook: "SenatorJaneSmith"
      },
      stats: {
        votesParticipated: 1247,
        billsSponsored: 42,
        voteAlignment: 87,
        approval: 68
      }
    },
    {
      id: 2,
      name: "Representative John Doe",
      role: "U.S. Representative",
      party: "Republican",
      state: "Texas",
      district: "District 5",
      image: "https://via.placeholder.com/150?text=JD",
      bio: "Conservative values, fiscal responsibility. Proud to represent District 5 since 2018.",
      socialMedia: {
        twitter: "@repjohndoe",
        facebook: "RepJohnDoe"
      },
      stats: {
        votesParticipated: 982,
        billsSponsored: 28,
        voteAlignment: 92,
        approval: 71
      }
    },
    {
      id: 3,
      name: "Governor Maria Garcia",
      role: "Governor",
      party: "Democrat",
      state: "New Mexico",
      district: "Statewide",
      image: "https://via.placeholder.com/150?text=MG",
      bio: "First Latina Governor of New Mexico. Focused on education, renewable energy, and border security.",
      socialMedia: {
        twitter: "@govgarcia",
        facebook: "GovMariaGarcia"
      },
      stats: {
        votesParticipated: 456,
        billsSponsored: 67,
        voteAlignment: 84,
        approval: 63
      }
    },
    {
      id: 4,
      name: "Senator Robert Wilson",
      role: "U.S. Senator",
      party: "Republican",
      state: "Florida",
      district: "At-Large",
      image: "https://via.placeholder.com/150?text=RW",
      bio: "Fighting for lower taxes and smaller government. Proud conservative serving Florida.",
      socialMedia: {
        twitter: "@senwilson",
        facebook: "SenatorWilson"
      },
      stats: {
        votesParticipated: 1189,
        billsSponsored: 35,
        voteAlignment: 95,
        approval: 74
      }
    }
  ],

  states: [
    {
      id: 1,
      name: "California",
      abbreviation: "CA",
      governor: "Gavin Newsom",
      population: "39.5M",
      image: "https://via.placeholder.com/150?text=CA",
      stats: {
        activeBills: 234,
        passedThisYear: 156,
        budgetBillions: 308
      }
    },
    {
      id: 2,
      name: "Texas",
      abbreviation: "TX",
      governor: "Greg Abbott",
      population: "29.1M",
      image: "https://via.placeholder.com/150?text=TX",
      stats: {
        activeBills: 198,
        passedThisYear: 134,
        budgetBillions: 248
      }
    }
  ],

  feedItems: [
    // Vote records
    {
      id: 1,
      politicianId: 1,
      type: "vote",
      timestamp: new Date(Date.now() - 1000 * 60 * 60 * 2), // 2 hours ago
      vote: {
        billNumber: "H.R. 1234",
        billTitle: "Climate Action and Clean Energy Act",
        vote: "YEA",
        result: "PASSED",
        yeas: 235,
        nays: 200,
        description: "A bill to promote clean energy and reduce carbon emissions by 50% by 2030"
      },
      likes: 342,
      comments: []
    },
    {
      id: 2,
      politicianId: 2,
      type: "vote",
      timestamp: new Date(Date.now() - 1000 * 60 * 60 * 5), // 5 hours ago
      vote: {
        billNumber: "S. 567",
        billTitle: "Tax Relief and Economic Growth Act",
        vote: "YEA",
        result: "PASSED",
        yeas: 221,
        nays: 214,
        description: "Legislation to provide tax cuts for small businesses and middle-class families"
      },
      likes: 289,
      comments: []
    },
    // Social media posts
    {
      id: 3,
      politicianId: 1,
      type: "social",
      timestamp: new Date(Date.now() - 1000 * 60 * 60 * 8), // 8 hours ago
      social: {
        platform: "twitter",
        content: "Proud to vote YES on the Climate Action Act today. Our children deserve a livable planet. #ClimateAction #GreenFuture"
      },
      likes: 1524,
      comments: []
    },
    {
      id: 4,
      politicianId: 2,
      type: "social",
      timestamp: new Date(Date.now() - 1000 * 60 * 60 * 12), // 12 hours ago
      social: {
        platform: "facebook",
        content: "Just wrapped up a town hall meeting in District 5. Thank you to everyone who came out! Your voices matter. 🇺🇸"
      },
      likes: 892,
      comments: []
    },
    // Analytics/Reports
    {
      id: 5,
      politicianId: 1,
      type: "analytics",
      timestamp: new Date(Date.now() - 1000 * 60 * 60 * 24), // 1 day ago
      analytics: {
        title: "Q3 2025 Voting Consistency Analysis",
        kpis: [
          { label: "Party Alignment", value: "87%", trend: "up" },
          { label: "Constituent Approval", value: "68%", trend: "stable" },
          { label: "Bills Co-Sponsored", value: "23", trend: "up" },
          { label: "Committee Attendance", value: "94%", trend: "up" }
        ],
        summary: "Senator Smith maintained strong party alignment while increasing bipartisan cooperation on infrastructure bills."
      },
      likes: 156,
      comments: []
    },
    {
      id: 6,
      politicianId: 3,
      type: "analytics",
      timestamp: new Date(Date.now() - 1000 * 60 * 60 * 30), // 30 hours ago
      analytics: {
        title: "Education Reform Impact Report",
        kpis: [
          { label: "Schools Funded", value: "245", trend: "up" },
          { label: "Teacher Salary Increase", value: "12%", trend: "up" },
          { label: "Graduation Rate", value: "89%", trend: "up" },
          { label: "Budget Allocated", value: "$2.4B", trend: "stable" }
        ],
        summary: "Governor Garcia's education initiatives show measurable improvements across New Mexico schools."
      },
      likes: 423,
      comments: []
    },
    // Research reports
    {
      id: 7,
      politicianId: 2,
      type: "research",
      timestamp: new Date(Date.now() - 1000 * 60 * 60 * 36), // 36 hours ago
      research: {
        title: "Economic Impact Analysis: Tax Relief Act",
        author: "OpenDiscourse Economic Policy Team",
        findings: [
          "Projected GDP growth: 2.3% increase over 3 years",
          "Small business job creation: estimated 450,000 jobs",
          "Middle-class tax savings: average $1,200 per household",
          "Federal deficit impact: $340B over 10 years"
        ],
        methodology: "Economic modeling using CBO baseline projections and historical tax policy data"
      },
      likes: 234,
      comments: []
    },
    {
      id: 8,
      politicianId: 4,
      type: "vote",
      timestamp: new Date(Date.now() - 1000 * 60 * 60 * 48), // 2 days ago
      vote: {
        billNumber: "H.R. 2891",
        billTitle: "Border Security Enhancement Act",
        vote: "YEA",
        result: "PASSED",
        yeas: 228,
        nays: 207,
        description: "Comprehensive border security legislation including technology upgrades and additional personnel"
      },
      likes: 567,
      comments: []
    },
    {
      id: 9,
      politicianId: 3,
      type: "social",
      timestamp: new Date(Date.now() - 1000 * 60 * 60 * 60), // 2.5 days ago
      social: {
        platform: "twitter",
        content: "Breaking ground on the largest renewable energy project in state history! 🌞 New Mexico is leading the clean energy transition. #RenewableEnergy #GreenJobs"
      },
      likes: 2134,
      comments: []
    },
    {
      id: 10,
      politicianId: 4,
      type: "analytics",
      timestamp: new Date(Date.now() - 1000 * 60 * 60 * 72), // 3 days ago
      analytics: {
        title: "Legislative Effectiveness Score - October 2025",
        kpis: [
          { label: "Bills Passed", value: "8", trend: "up" },
          { label: "Conservative Score", value: "95%", trend: "stable" },
          { label: "Town Halls Held", value: "12", trend: "up" },
          { label: "Constituent Services", value: "1,847", trend: "up" }
        ],
        summary: "Senator Wilson ranks in top 10% for legislative effectiveness among Republicans in the 119th Congress."
      },
      likes: 445,
      comments: []
    }
  ],

  // Store comments separately for easy manipulation
  comments: {}
};

// Initialize empty comment arrays for each feed item
mockData.feedItems.forEach(item => {
  mockData.comments[item.id] = [];
});

// Add some sample comments
mockData.comments[1] = [
  {
    id: 1,
    author: "John Public",
    content: "Great to see action on climate! This is what we need.",
    timestamp: new Date(Date.now() - 1000 * 60 * 60),
    likes: 23
  },
  {
    id: 2,
    author: "Sarah Voter",
    content: "How will this affect energy prices in the short term?",
    timestamp: new Date(Date.now() - 1000 * 60 * 30),
    likes: 8
  }
];

mockData.comments[3] = [
  {
    id: 3,
    author: "Climate Activist",
    content: "Thank you for your leadership on this critical issue!",
    timestamp: new Date(Date.now() - 1000 * 60 * 60 * 6),
    likes: 45
  }
];

mockData.comments[5] = [
  {
    id: 4,
    author: "Policy Wonk",
    content: "Interesting to see the bipartisan cooperation metrics improving.",
    timestamp: new Date(Date.now() - 1000 * 60 * 60 * 20),
    likes: 12
  },
  {
    id: 5,
    author: "Constituent123",
    content: "Would love to see more details on the infrastructure bills mentioned.",
    timestamp: new Date(Date.now() - 1000 * 60 * 60 * 18),
    likes: 7
  }
];
