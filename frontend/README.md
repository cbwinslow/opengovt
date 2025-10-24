# OpenGovt Frontend - Political Transparency Platform

A Facebook-like social media interface for tracking politicians, government entities, voting records, analytics, and legislative activity.

## Overview

This frontend provides a familiar social media experience for viewing and interacting with political data. Politicians and government entities have "profiles" with automated feeds populated by:

- **Voting Records**: Real-time tracking of how politicians vote on bills
- **Analytics & KPIs**: Performance metrics, voting consistency, approval ratings
- **Social Media Posts**: Integration of politicians' actual social media content
- **Research Reports**: Analysis and studies conducted by the OpenDiscourse team
- **Comments**: Public can comment on any feed item

## Features

### 🎯 Core Functionality

- **Politician Profiles**: View detailed profiles with bio, stats, and complete activity feed
- **Automated Feeds**: All content is algorithmically populated - politicians cannot control their feeds
- **Vote Tracking**: See every vote cast with bill details, vote tallies, and outcomes
- **Analytics Dashboard**: KPIs showing party alignment, approval ratings, effectiveness
- **Research Integration**: Display analysis reports and policy impact studies
- **Social Media Aggregation**: Pull in Twitter/Facebook posts from politicians
- **Comment System**: Users can comment on any feed item (votes, posts, reports)
- **Real-time Updates**: Feeds update as new votes and activity occur

### 👥 Entity Types

1. **Politicians**: Senators, Representatives, Governors
2. **States**: State-level government entities with their own feeds
3. **Government Entities**: Federal/state departments (future)

### 📊 Feed Item Types

- **Vote Records**: Bill votes with full details and vote breakdown
- **Social Media**: Politician's Twitter/Facebook posts
- **Analytics**: Quarterly reports, voting consistency, performance metrics
- **Research**: Policy analysis, economic impact studies, fact-checks

## Project Structure

```
frontend/
├── index.html              # Main application page
├── css/
│   └── styles.css          # Facebook-inspired styling
├── js/
│   └── app.js              # Main application logic
└── data/
    └── mock-data.js        # Mock data (politicians, votes, feeds)
```

## Getting Started

### Quick Start

1. Simply open `index.html` in a web browser:
   ```bash
   cd frontend
   open index.html  # macOS
   # or
   xdg-open index.html  # Linux
   # or just double-click the file
   ```

2. Or serve with Python:
   ```bash
   cd frontend
   python3 -m http.server 8000
   # Visit http://localhost:8000
   ```

3. Or use Node.js:
   ```bash
   cd frontend
   npx http-server -p 8000
   # Visit http://localhost:8000
   ```

### No Build Required

This is a vanilla JavaScript application with no build step or dependencies. Just open and run!

## Usage

### Navigation

- **Click on any politician** in the left sidebar to view their profile and feed
- **Search bar**: Find politicians by name, state, or party
- **Logo**: Click to return to home feed

### Interacting with Feeds

- **Like**: Click the 👍 button to like a feed item
- **Comment**: Click 💬 to show/hide comments, then type and post
- **Share**: Click ↗️ to share (future functionality)

### Feed Item Types

Each feed item is labeled by type:
- 🔵 **VOTE**: Legislative votes with bill details
- 🟢 **SOCIAL**: Social media posts from the politician
- 🟠 **ANALYTICS**: Performance reports and KPIs
- 🟣 **RESEARCH**: Analysis reports from OpenDiscourse team

## Data Integration

### Current: Mock Data

The frontend currently uses mock data in `data/mock-data.js` to demonstrate functionality.

### Future: Real Data Integration

To connect to real backend data:

1. **Replace mock data** with API calls in `js/app.js`
2. **API endpoints** should provide:
   - `GET /api/politicians` - List of politicians
   - `GET /api/politicians/:id` - Politician details
   - `GET /api/feed/:politicianId` - Feed items for a politician
   - `GET /api/votes/:politicianId` - Voting records
   - `POST /api/comments` - Submit comments
   - `POST /api/likes` - Record likes

3. **Backend data sources**:
   - Congress.gov API for federal votes
   - OpenStates API for state legislators
   - GovTrack for additional data
   - Twitter/Facebook APIs for social posts
   - Internal analysis pipeline for reports

## Design Principles

### Facebook-Inspired UI

- Familiar three-column layout (sidebar, feed, trending)
- Card-based feed items
- Profile headers with cover photos and stats
- Comment threads with avatars
- Hover effects and smooth transitions

### User-Controlled vs. Platform-Controlled

**Politicians CANNOT:**
- Delete or hide votes
- Remove analysis reports
- Control what appears in their feed
- Hide unfavorable metrics

**The Platform Controls:**
- What appears in feeds (algorithms + data)
- Analysis and research displayed
- Voting records and statistics
- Comment moderation

**Users CAN:**
- View all politician activity
- Comment on any feed item
- Like and share content
- Search and filter

## Customization

### Styling

Edit `css/styles.css` to customize:
- Color scheme (CSS variables at top of file)
- Party colors
- Layout breakpoints
- Component styling

### Mock Data

Edit `data/mock-data.js` to add:
- More politicians
- Additional states
- More feed items (votes, posts, reports)
- Sample comments

### Functionality

Edit `js/app.js` to:
- Add new feed item types
- Customize rendering
- Add features (filters, sorting)
- Integrate with backend APIs

## Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- Mobile browsers (responsive design)

## Future Enhancements

### Planned Features

- [ ] Real-time vote updates via WebSocket
- [ ] Advanced filtering (by date, type, topic)
- [ ] Sorting options (chronological, relevance, popularity)
- [ ] Bill detail pages with full text
- [ ] Politician comparison tool
- [ ] Voting pattern visualization
- [ ] Fact-check integration
- [ ] Email/push notifications for important votes
- [ ] Export reports as PDF
- [ ] Dark mode
- [ ] Accessibility improvements

### Backend Integration

- [ ] Connect to OpenDiscourse API
- [ ] Real-time data sync
- [ ] User authentication
- [ ] Personalized feeds
- [ ] Saved politicians/bills
- [ ] Comment moderation system
- [ ] Analytics tracking
- [ ] A/B testing framework

## Contributing

This frontend is part of the OpenDiscourse project. To contribute:

1. Follow the existing code style
2. Test on multiple browsers
3. Keep it simple - no build tools unless necessary
4. Document new features in this README

## License

Part of the OpenDiscourse/OpenGovt project - See main repository LICENSE

## Related Documentation

- Main repository README: `../README.md`
- Project roadmap: `../OPENDISCOURSE_PROJECT.md`
- Backend documentation: `../docs/`
- Data models: `../models/`

---

**OpenGovt** - Making government transparent and accessible through technology.
