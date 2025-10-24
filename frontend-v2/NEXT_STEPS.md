# Next Steps for OpenGovt Frontend Migration

## ✅ What's Been Completed

### Phase 1 - Foundation Setup (Current Commit)

1. **Next.js 14 Project Initialized**
   - App Router architecture
   - TypeScript configured
   - Tailwind CSS with custom theming
   - Facebook-inspired CSS variables

2. **Component Library Setup**
   - shadcn/ui configured
   - Base components created: Card, Button, Avatar
   - Utility functions: `cn()`, `formatTimeAgo()`

3. **Type System**
   - Complete TypeScript types for:
     - Politicians
     - Feed items (Vote, Social, Analytics, Research)
     - Comments
     - States
     - All data models

4. **Planning Documents**
   - **MIGRATION_PLAN.md**: Complete 10-phase roadmap
   - **ISSUES_BREAKDOWN.md**: 40 GitHub issues ready to create

## 🚀 Immediate Next Steps (Continue Phase 1)

### Step 1: Create Layout Components
**Files to create in `components/layout/`:**

1. **`header.tsx`** - Top navigation bar
   - Logo and app name
   - Search bar
   - User menu/auth buttons
   - Mobile hamburger menu

2. **`sidebar.tsx`** - Left sidebar
   - Politicians list with avatars
   - States list
   - Filter/search
   - Active item highlighting

3. **`main-feed.tsx`** - Main feed container
   - Profile header section
   - Feed items list
   - Loading states
   - Empty states

4. **`right-sidebar.tsx`** - Right sidebar
   - Trending topics
   - Recent bills
   - Activity feed

5. **`profile-header.tsx`** - Politician profile
   - Cover photo
   - Profile picture
   - Name, role, party
   - Stats grid

### Step 2: Create Feed Card Components
**Files to create in `components/feed/`:**

1. **`vote-card.tsx`** - Legislative vote display
   - Bill number and title
   - Vote cast (YEA/NAY) with styling
   - Vote tallies
   - Result badge

2. **`social-card.tsx`** - Social media post
   - Platform indicator (Twitter/Facebook icon)
   - Post content
   - Timestamp

3. **`analytics-card.tsx`** - Analytics report
   - Title
   - KPI grid with trends
   - Summary text

4. **`research-card.tsx`** - Research report
   - Title and author
   - Findings list
   - Methodology

5. **`feed-actions.tsx`** - Like, comment, share buttons
   - Icon buttons
   - Count displays
   - Active states

6. **`comment-section.tsx`** - Comment thread
   - Comment list
   - Comment form
   - Nested replies (future)

7. **`comment-item.tsx`** - Individual comment
   - Avatar
   - Author name
   - Comment text
   - Timestamp
   - Like button

### Step 3: Add More shadcn/ui Components

**Install these components:**
```bash
cd frontend-v2
npx shadcn@latest add input
npx shadcn@latest add textarea
npx shadcn@latest add badge
npx shadcn@latest add dropdown-menu
npx shadcn@latest add dialog
npx shadcn@latest add separator
npx shadcn@latest add scroll-area
npx shadcn@latest add tabs
```

**Or manually create if network restricted:**
- Input
- Textarea
- Badge
- DropdownMenu
- Dialog
- Separator
- ScrollArea
- Tabs

### Step 4: Update Mock Data

**File: `lib/data/mock-data.ts`**
- Fix TypeScript errors
- Ensure data matches types
- Add more sample data if needed

### Step 5: Wire Up the App

**File: `app/page.tsx`**
- Already has skeleton code
- Connect state management
- Implement politician switching
- Add feed filtering

### Step 6: Test & Validate

1. **Run dev server:**
   ```bash
   cd frontend-v2
   npm run dev
   ```

2. **Test functionality:**
   - Navigate between politicians
   - View all feed types
   - Post comments
   - Like items
   - Responsive design

3. **Fix issues:**
   - TypeScript errors
   - Styling problems
   - Mobile responsiveness
   - Loading states

### Step 7: Add Missing Features

1. **Search functionality**
2. **Feed filtering** (by type)
3. **Sorting options**
4. **Pagination** or infinite scroll
5. **Loading skeletons**
6. **Error boundaries**

## 📋 Commands Reference

### Development
```bash
cd frontend-v2
npm run dev          # Start dev server (http://localhost:3000)
npm run build        # Build for production
npm run start        # Start production server
npm run lint         # Run ESLint
```

### Adding Components
```bash
npx shadcn@latest add [component-name]
```

### Useful Tools
```bash
npm run type-check   # Check TypeScript (add to package.json)
```

## 🎨 Design Guidelines

### Colors
- **Primary Blue**: `hsl(221.2 83.2% 53.3%)`  - Main brand color
- **Democrat Blue**: `hsl(240 100% 37%)` - Party color
- **Republican Red**: `hsl(0 87% 55%)` - Party color
- **Background**: `hsl(0 0% 94%)` - Page background
- **Card Background**: `hsl(0 0% 100%)` - White cards

### Spacing
- Use Tailwind spacing scale (4, 8, 12, 16, 24, 32px)
- Consistent padding: `p-4` for cards
- Gap between elements: `gap-4`

### Typography
- **Headings**: Font-semibold or font-bold
- **Body**: Default font-normal
- **Small text**: `text-sm` for metadata
- **Tiny text**: `text-xs` for timestamps

### Breakpoints
- **Mobile**: < 768px (1 column)
- **Tablet**: 768px - 1024px (2 columns)
- **Desktop**: > 1024px (3 columns)

## 🐛 Known Issues to Fix

1. **Mock data file** needs TypeScript fixes
2. **Layout components** not yet created
3. **Feed cards** not yet implemented
4. **Comment system** needs migration
5. **Mobile menu** not implemented
6. **Search** not functional

## 📚 Resources

### Documentation
- [Next.js 14 Docs](https://nextjs.org/docs)
- [shadcn/ui Components](https://ui.shadcn.com/)
- [Tailwind CSS](https://tailwindcss.com/docs)
- [Radix UI](https://www.radix-ui.com/)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)

### Code Examples
- See original `frontend/` directory for reference
- Check `types/index.ts` for data structures
- Review `lib/utils.ts` for helper functions

## 🎯 Success Criteria for Phase 1

Before moving to Phase 2, ensure:

- ✅ All layout components created and working
- ✅ All feed card types render correctly
- ✅ Comment system functional
- ✅ Mobile responsive (test on 3 screen sizes)
- ✅ TypeScript has no errors
- ✅ ESLint has no errors
- ✅ Matches original design visually
- ✅ Performance is acceptable (< 2s load time)
- ✅ No console errors
- ✅ All interactions work (like, comment, navigate)

## 🔄 After Phase 1

Once Phase 1 is complete:

1. **Create GitHub Issues** from ISSUES_BREAKDOWN.md
2. **Set up Project Board** for tracking
3. **Begin Phase 2**: NextAuth.js authentication
4. **Set up database** (Prisma + PostgreSQL)
5. **Create API routes**

## 📞 Questions?

Refer to:
- **MIGRATION_PLAN.md** - Overall strategy
- **ISSUES_BREAKDOWN.md** - Detailed tasks
- **Original frontend/** - Reference implementation

## 🎉 End Goal

A modern, scalable, mobile-friendly political transparency platform with:
- Next.js + React + TypeScript
- Real-time updates
- User authentication
- Social features
- Admin tools
- Government data integration
- Production deployment

---

**Current Status**: Phase 1 - Foundation Complete ✅  
**Next Action**: Create layout components  
**Target**: Complete Phase 1 within 2-3 weeks
