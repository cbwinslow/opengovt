# Frontend Integration Guide

This guide explains how to connect the OpenGovt frontend to a real backend data source.

## Current State: Mock Data

The frontend currently uses static mock data defined in `data/mock-data.js`. This includes:
- 4 sample politicians (2 Senators, 1 Representative, 1 Governor)
- 2 states
- 10 feed items across different types (votes, social media, analytics, research)
- Sample comments

## Integration Steps

### 1. Create Backend API

You'll need to create API endpoints that return JSON data matching the structure expected by the frontend. Required endpoints:

#### Politicians API
```
GET /api/politicians
GET /api/politicians/:id
```

Expected format:
```javascript
{
  id: 1,
  name: "Senator Jane Smith",
  role: "U.S. Senator",
  party: "Democrat",
  state: "California",
  district: "At-Large",
  image: "https://...",
  bio: "...",
  socialMedia: { twitter: "@...", facebook: "..." },
  stats: {
    votesParticipated: 1247,
    billsSponsored: 42,
    voteAlignment: 87,
    approval: 68
  }
}
```

#### Feed Items API
```
GET /api/feed/:politicianId
GET /api/feed/:politicianId?type=vote|social|analytics|research
```

Expected format:
```javascript
{
  id: 1,
  politicianId: 1,
  type: "vote|social|analytics|research",
  timestamp: "2025-10-22T10:00:00Z",
  vote: { /* vote details */ },
  social: { /* social media post */ },
  analytics: { /* analytics report */ },
  research: { /* research report */ },
  likes: 342,
  comments: []
}
```

#### Comments API
```
GET /api/comments/:feedItemId
POST /api/comments
```

#### States API
```
GET /api/states
GET /api/states/:id
```

### 2. Modify Frontend JavaScript

In `js/app.js`, replace the mock data loading with API calls:

```javascript
// Replace this:
loadPoliticianProfile(politicianId) {
  this.currentPolitician = mockData.politicians.find(p => p.id === politicianId);
}

// With this:
async loadPoliticianProfile(politicianId) {
  const response = await fetch(`/api/politicians/${politicianId}`);
  this.currentPolitician = await response.json();
  this.renderProfile(this.currentPolitician);
  await this.loadFeed(politicianId);
}

async loadFeed(politicianId) {
  const response = await fetch(`/api/feed/${politicianId}`);
  const feedItems = await response.json();
  this.renderFeedItems(feedItems);
}
```

### 3. Data Pipeline Integration

The backend should automatically populate feed items from:

#### Vote Records
- Source: Congress.gov API, OpenStates API, GovTrack
- Frequency: Real-time or hourly updates
- Processing: Parse XML/JSON votes, extract bill info, vote tallies

#### Social Media
- Source: Twitter API v2, Facebook Graph API
- Frequency: Every 15-30 minutes
- Processing: Filter for official accounts, extract text and metadata

#### Analytics Reports
- Source: Internal analysis pipeline
- Frequency: Daily/weekly/quarterly
- Processing: Run SQL queries, calculate KPIs, generate summaries

#### Research Reports
- Source: Internal research team + automated analysis
- Frequency: As published
- Processing: Format findings, methodology, conclusions

### 4. Backend Technology Recommendations

#### Option A: Python + FastAPI
```python
from fastapi import FastAPI
from typing import List
import asyncpg

app = FastAPI()

@app.get("/api/politicians/{politician_id}")
async def get_politician(politician_id: int):
    # Query PostgreSQL database
    # Return politician data
    pass

@app.get("/api/feed/{politician_id}")
async def get_feed(politician_id: int, type: str = None):
    # Query feed items from database
    # Filter by type if specified
    # Return sorted by timestamp
    pass
```

#### Option B: Node.js + Express
```javascript
const express = require('express');
const app = express();

app.get('/api/politicians/:id', async (req, res) => {
  // Query database
  // Return JSON
});

app.get('/api/feed/:politicianId', async (req, res) => {
  // Query feed items
  // Return JSON
});
```

### 5. Database Schema

Use the existing models in `/models/`:
- `person.py` - Politicians
- `vote.py` - Vote records
- `bill.py` - Bill information
- `committee.py` - Committee assignments
- `jurisdiction.py` - States and jurisdictions

Add new tables for frontend:
```sql
CREATE TABLE feed_items (
  id SERIAL PRIMARY KEY,
  politician_id INTEGER REFERENCES persons(id),
  type VARCHAR(20) NOT NULL,
  timestamp TIMESTAMP NOT NULL,
  content JSONB NOT NULL,
  likes INTEGER DEFAULT 0,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE comments (
  id SERIAL PRIMARY KEY,
  feed_item_id INTEGER REFERENCES feed_items(id),
  author VARCHAR(255) NOT NULL,
  content TEXT NOT NULL,
  timestamp TIMESTAMP DEFAULT NOW(),
  likes INTEGER DEFAULT 0
);
```

### 6. Data Update Pipeline

Create background jobs to populate the feed:

```python
# Example: Vote ingestion
async def ingest_votes():
    # Fetch latest votes from Congress.gov
    votes = await fetch_congress_votes()
    
    for vote in votes:
        # Create feed item
        feed_item = {
            'politician_id': get_politician_for_vote(vote),
            'type': 'vote',
            'timestamp': vote.date,
            'content': {
                'vote': {
                    'billNumber': vote.bill_number,
                    'billTitle': vote.bill_title,
                    'vote': vote.vote_cast,
                    'result': vote.result,
                    'yeas': vote.yeas,
                    'nays': vote.nays,
                    'description': vote.description
                }
            }
        }
        await db.insert('feed_items', feed_item)

# Run every hour
schedule.every().hour.do(ingest_votes)
```

### 7. Real-time Updates

For real-time updates, add WebSocket support:

```javascript
// Frontend
const ws = new WebSocket('ws://localhost:8080/ws');

ws.onmessage = (event) => {
  const update = JSON.parse(event.data);
  if (update.type === 'new_feed_item') {
    this.prependFeedItem(update.data);
  }
};

// Backend
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        # Send updates when new feed items are created
        await websocket.send_json(new_item)
```

### 8. Authentication (Future)

Add user authentication for likes and comments:

```javascript
// Frontend
async handleComment(itemId, content) {
  const response = await fetch('/api/comments', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${this.authToken}`
    },
    body: JSON.stringify({
      feed_item_id: itemId,
      content: content
    })
  });
}
```

### 9. Deployment

#### Frontend
- Deploy as static files to CDN (Cloudflare, AWS S3, Netlify)
- Or serve from backend at `/static/`

#### Backend
- Deploy FastAPI with Uvicorn/Gunicorn
- Use PostgreSQL for data storage
- Add Redis for caching
- Use Nginx as reverse proxy

### 10. Environment Variables

```bash
# .env
DATABASE_URL=postgresql://user:pass@localhost:5432/opengovt
REDIS_URL=redis://localhost:6379
TWITTER_API_KEY=...
TWITTER_API_SECRET=...
FACEBOOK_API_KEY=...
CONGRESS_API_KEY=...
```

## Migration Plan

1. **Phase 1**: Set up backend API with mock data
2. **Phase 2**: Connect one data source (e.g., votes from Congress.gov)
3. **Phase 3**: Add social media integration
4. **Phase 4**: Implement analytics pipeline
5. **Phase 5**: Add research reports
6. **Phase 6**: Enable user authentication and interactions
7. **Phase 7**: Add real-time updates

## Testing

Before going live:
- Test API endpoints with Postman/curl
- Verify data formats match frontend expectations
- Test error handling (404s, 500s)
- Load test with realistic data volumes
- Test comment posting and like functionality
- Verify real-time updates work correctly

## Monitoring

Add monitoring for:
- API response times
- Database query performance
- Feed update frequency
- Error rates
- User engagement metrics

## Questions?

Refer to:
- Backend documentation in `/docs/`
- Data models in `/models/`
- Congress API documentation at https://api.congress.gov
- OpenStates API at https://openstates.org/api/
