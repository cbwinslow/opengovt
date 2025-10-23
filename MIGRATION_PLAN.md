# OpenGovt Frontend Migration Plan

## Overview

This document outlines the comprehensive plan to migrate the current vanilla JavaScript frontend to a modern Next.js + React + TypeScript stack with enhanced features as requested.

## Current State

- **Technology**: Vanilla JavaScript, HTML, CSS
- **Features**: Basic Facebook-like UI with politician profiles, feeds, comments
- **Deployment**: Static files, no build process
- **Data**: Mock data in JavaScript
- **Authentication**: None

## Target State

- **Technology**: Next.js 14 (App Router), React, TypeScript, Tailwind CSS, shadcn/ui
- **Features**: Full social platform with authentication, real-time updates, advanced content handling
- **Deployment**: Vercel/similar platform with serverless functions
- **Data**: PostgreSQL database with Prisma ORM
- **Authentication**: NextAuth.js with OAuth providers

## Migration Phases

### Phase 1: Framework Migration ✅ IN PROGRESS
**Timeline**: Current Sprint

**Tasks**:
- [x] Initialize Next.js 14 project with TypeScript
- [x] Set up Tailwind CSS
- [x] Install and configure shadcn/ui
- [x] Create component structure
- [x] Migrate data types to TypeScript
- [ ] Create layout components (Header, Sidebar, MainFeed, RightSidebar)
- [ ] Create feed card components (VoteCard, SocialCard, AnalyticsCard, ResearchCard)
- [ ] Implement mobile-responsive design
- [ ] Migrate mock data
- [ ] Test basic functionality

**Deliverables**:
- Working Next.js application
- Responsive Facebook-like layout
- Basic feed functionality
- Component library setup

### Phase 2: Authentication & User System
**Timeline**: Sprint 2 (Week 2-3)

**Tasks**:
- [ ] Set up NextAuth.js
- [ ] Configure OAuth providers (Google, GitHub, Twitter)
- [ ] Create user database schema
- [ ] Implement user profiles
- [ ] Add avatar support
- [ ] Create demographic information forms
- [ ] Implement anonymous posting option
- [ ] Add role-based access control (admin/user/moderator)
- [ ] Create user settings page

**Components**:
- `AuthProvider` - Authentication context
- `LoginButton` - OAuth login UI
- `UserProfile` - Profile page component
- `UserSettings` - Settings page
- `AdminDashboard` - Admin panel

### Phase 3: Enhanced Social Features
**Timeline**: Sprint 3 (Week 4-5)

**Tasks**:
- [ ] Implement reputation system
  - Upvote/downvote mechanism
  - Reputation calculation algorithm
  - Reputation display badges
- [ ] Add user follow system
  - Follow/unfollow politicians
  - Follow other users
  - Following feed
- [ ] Implement direct messaging
  - Real-time chat using Pusher/Ably
  - Message notifications
  - Conversation threads
- [ ] Create user activity feed
- [ ] Add notification system

**Components**:
- `ReputationBadge` - User reputation display
- `FollowButton` - Follow/unfollow UI
- `MessageThread` - DM conversation
- `NotificationDropdown` - Notifications UI

### Phase 4: Advanced Content Handling
**Timeline**: Sprint 4 (Week 6-7)

**Tasks**:
- [ ] Implement markdown rendering in comments
  - Install and configure markdown parser
  - Add syntax highlighting
  - Support for tables, lists, code blocks
- [ ] Add link previews
  - OpenGraph metadata fetching
  - Link preview cards
  - URL validation
- [ ] Implement image handling
  - Image upload to cloud storage (Cloudflare R2/S3)
  - Image optimization
  - Image preview in comments
  - Lightbox viewer
- [ ] Add file attachments
  - File upload support
  - File type validation
  - File preview generation
- [ ] Integrate virus scanning
  - ClamAV API or similar
  - Scan files on upload
  - Quarantine malicious files
  - User feedback on scan results

**Components**:
- `MarkdownRenderer` - Markdown display
- `LinkPreview` - URL preview card
- `ImageUpload` - Image upload UI
- `FileAttachment` - File preview/download
- `MediaViewer` - Lightbox for images/videos

### Phase 5: Real-time Updates
**Timeline**: Sprint 5 (Week 8)

**Tasks**:
- [ ] Set up WebSocket infrastructure (Pusher/Ably/Socket.io)
- [ ] Implement real-time feed updates
- [ ] Add real-time comment updates
- [ ] Live notification delivery
- [ ] Online status indicators
- [ ] Typing indicators for messages
- [ ] Optimistic UI updates

**Technologies**:
- Pusher Channels or Ably
- React Query for data synchronization
- SWR for cache management

### Phase 6: Admin Tools & Content Management
**Timeline**: Sprint 6 (Week 9-10)

**Tasks**:
- [ ] Create admin dashboard
  - User management
  - Content moderation queue
  - Analytics dashboard
  - System health monitoring
- [ ] Implement content moderation
  - Flag inappropriate content
  - Review queue for flagged items
  - Ban/suspend users
  - Content removal tools
- [ ] Add data integrity workflows
  - Data validation rules
  - Automated data quality checks
  - Data correction tools
  - Audit logs
- [ ] Create report generation
  - Analytics reports
  - User activity reports
  - Content metrics
  - Export functionality

**Components**:
- `AdminDashboard` - Main admin panel
- `ModerationQueue` - Content review UI
- `UserManagement` - User admin tools
- `AnalyticsPanel` - Metrics and charts
- `AuditLog` - Activity log viewer

### Phase 7: Database & Backend API
**Timeline**: Sprint 7 (Week 11-12)

**Tasks**:
- [ ] Set up PostgreSQL database
- [ ] Install and configure Prisma ORM
- [ ] Design database schema
  - Users table
  - Politicians table
  - Feed items table
  - Comments table
  - Likes table
  - Follows table
  - Messages table
  - Notifications table
- [ ] Create API routes
  - Authentication endpoints
  - User CRUD operations
  - Feed operations
  - Comment operations
  - Admin operations
- [ ] Implement data migrations
- [ ] Add database indexes for performance
- [ ] Set up connection pooling

**Database Schema**:
```prisma
model User {
  id            String    @id @default(cuid())
  email         String    @unique
  name          String?
  image         String?
  reputation    Int       @default(0)
  createdAt     DateTime  @default(now())
  comments      Comment[]
  likes         Like[]
  follows       Follow[]
  messages      Message[]
}

model Politician {
  id            Int       @id @default(autoincrement())
  name          String
  role          String
  party         String
  state         String
  feedItems     FeedItem[]
}

model FeedItem {
  id            Int       @id @default(autoincrement())
  politicianId  Int
  type          String
  content       Json
  timestamp     DateTime  @default(now())
  politician    Politician @relation(fields: [politicianId], references: [id])
  comments      Comment[]
  likes         Like[]
}

model Comment {
  id            Int       @id @default(autoincrement())
  content       String
  userId        String
  feedItemId    Int
  createdAt     DateTime  @default(now())
  user          User      @relation(fields: [userId], references: [id])
  feedItem      FeedItem  @relation(fields: [feedItemId], references: [id])
  likes         Like[]
}

model Like {
  id            Int       @id @default(autoincrement())
  userId        String
  feedItemId    Int?
  commentId     Int?
  user          User      @relation(fields: [userId], references: [id])
  feedItem      FeedItem? @relation(fields: [feedItemId], references: [id])
  comment       Comment?  @relation(fields: [commentId], references: [id])
}
```

### Phase 8: Integration with Government Data
**Timeline**: Sprint 8 (Week 13-14)

**Tasks**:
- [ ] Integrate Congress.gov API
- [ ] Integrate OpenStates API
- [ ] Integrate GovTrack API
- [ ] Set up automated data ingestion
- [ ] Create background jobs for data updates
- [ ] Implement caching strategy
- [ ] Add rate limiting
- [ ] Create data transformation pipelines

**Jobs**:
- Vote ingestion job (hourly)
- Social media scraper (every 15 min)
- Analytics calculation job (daily)
- Research report processor (on demand)

### Phase 9: Testing & Quality Assurance
**Timeline**: Sprint 9 (Week 15)

**Tasks**:
- [ ] Write unit tests
  - Component tests with React Testing Library
  - Utility function tests
  - Hook tests
- [ ] Write integration tests
  - API endpoint tests
  - Database operation tests
  - Authentication flow tests
- [ ] Write E2E tests
  - Playwright tests for critical user flows
  - Mobile responsive tests
- [ ] Performance testing
  - Load testing
  - Database query optimization
  - Bundle size optimization
- [ ] Security audit
  - CodeQL scanning
  - Dependency vulnerability checks
  - Penetration testing

### Phase 10: Deployment & DevOps
**Timeline**: Sprint 10 (Week 16)

**Tasks**:
- [ ] Set up CI/CD pipeline
- [ ] Configure staging environment
- [ ] Set up production environment
- [ ] Configure monitoring (Vercel Analytics, Sentry)
- [ ] Set up logging (LogRocket, Datadog)
- [ ] Create deployment documentation
- [ ] Configure CDN for static assets
- [ ] Set up database backups
- [ ] Create disaster recovery plan

## Technical Stack

### Frontend
- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **UI Components**: shadcn/ui (built on Radix UI)
- **Icons**: Lucide React
- **State Management**: React Context + Zustand (if needed)
- **Data Fetching**: React Query / SWR
- **Forms**: React Hook Form + Zod validation
- **Markdown**: react-markdown
- **Real-time**: Pusher or Ably

### Backend
- **Runtime**: Node.js (Vercel Serverless Functions)
- **Database**: PostgreSQL (Vercel Postgres or Supabase)
- **ORM**: Prisma
- **Authentication**: NextAuth.js
- **File Storage**: Cloudflare R2 or AWS S3
- **Virus Scanning**: ClamAV API or VirusTotal API
- **Email**: Resend or SendGrid

### DevOps
- **Hosting**: Vercel
- **Database**: Vercel Postgres or Supabase
- **Monitoring**: Vercel Analytics + Sentry
- **Logging**: LogRocket
- **CI/CD**: GitHub Actions
- **Testing**: Vitest + Playwright

## Migration Strategy

### Parallel Development
- Keep existing vanilla JS frontend operational
- Develop new Next.js app in `frontend-v2/` directory
- Test thoroughly before switching

### Gradual Rollout
1. Internal testing with dev team
2. Beta testing with select users
3. Soft launch with feature flags
4. Full deployment with monitoring
5. Deprecate old frontend

### Data Migration
1. Set up new database
2. Create migration scripts for existing data
3. Test migration in staging
4. Perform production migration during low-traffic window
5. Verify data integrity

## Success Metrics

### Performance
- Page load time < 2 seconds
- First Contentful Paint < 1.5 seconds
- Time to Interactive < 3 seconds
- Lighthouse score > 90

### User Engagement
- Daily active users (DAU)
- Comment rate
- Like/upvote rate
- Time on site
- Return visitor rate

### Technical
- 99.9% uptime
- API response time < 200ms
- Database query time < 100ms
- Zero critical security vulnerabilities

## Risks & Mitigations

### Risk: Complexity Overload
**Mitigation**: Break into small, testable phases. Each phase should be deployable independently.

### Risk: Performance Issues
**Mitigation**: Implement caching strategy, use CDN, optimize database queries, lazy load components.

### Risk: User Adoption
**Mitigation**: Keep familiar UI/UX, provide migration guide, offer training/tutorials.

### Risk: Data Integrity
**Mitigation**: Comprehensive testing, database constraints, validation at multiple layers.

### Risk: Security Vulnerabilities
**Mitigation**: Regular security audits, automated scanning, follow OWASP guidelines, implement rate limiting.

## Resource Requirements

### Development Team
- 2-3 Full-stack developers
- 1 UI/UX designer
- 1 DevOps engineer
- 1 QA engineer

### Infrastructure
- Vercel Pro plan ($20/month)
- PostgreSQL database ($25-50/month)
- File storage ($10-30/month)
- Monitoring tools ($50/month)
- Total: ~$150-200/month

### Timeline
- **Minimum Viable Product**: 6-8 weeks
- **Full Feature Set**: 12-16 weeks
- **Polish & Launch**: 2-4 weeks
- **Total**: 4-6 months

## Next Steps

1. ✅ Initialize Next.js project
2. ✅ Set up component library
3. ⏳ Complete Phase 1 (Framework Migration)
4. 🔜 Begin Phase 2 (Authentication)

## Questions & Decisions Needed

1. **OAuth Providers**: Which providers to support initially? (Google, GitHub, Twitter, Facebook?)
2. **Database Hosting**: Vercel Postgres vs Supabase vs dedicated PostgreSQL?
3. **Real-time Provider**: Pusher vs Ably vs self-hosted Socket.io?
4. **File Storage**: Cloudflare R2 vs AWS S3 vs Vercel Blob?
5. **Virus Scanning**: ClamAV vs VirusTotal vs other?
6. **Email Provider**: Resend vs SendGrid vs AWS SES?

## Contact

For questions or concerns about this migration plan, please reach out to the development team.

---

Last Updated: 2025-10-23
Status: Phase 1 In Progress
