# Social Media Analysis Guide

This guide covers the social media integration features in OpenGovt, specifically Twitter/X data ingestion, sentiment analysis, toxicity detection, and political statement extraction.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Database Schema](#database-schema)
- [Data Ingestion](#data-ingestion)
- [Analysis Features](#analysis-features)
- [API Usage Examples](#api-usage-examples)
- [Best Practices](#best-practices)

## Overview

The social media module provides comprehensive analysis of politicians' social media presence, including:

- **Tweet Collection**: Automated ingestion of tweets, retweets, quotes, and replies
- **Sentiment Analysis**: Multi-model sentiment detection using VADER and transformers
- **Toxicity Detection**: Hate speech and toxic language identification
- **Statement Extraction**: Multi-granularity extraction of political actions and declarations
- **Engagement Metrics**: Like, retweet, reply, and quote tracking
- **Constituent Analysis**: Profile analysis of people responding to politicians

## Prerequisites

### 1. Twitter API Access

You need Twitter API v2 access with elevated permissions:

1. Sign up for a Twitter Developer account at https://developer.twitter.com/
2. Create a new app and generate API credentials
3. Set the following environment variables in `.env`:

```bash
TWITTER_BEARER_TOKEN=your_bearer_token
TWITTER_API_KEY=your_api_key
TWITTER_API_SECRET=your_api_secret
TWITTER_ACCESS_TOKEN=your_access_token
TWITTER_ACCESS_SECRET=your_access_secret
```

### 2. Python Dependencies

Install required packages:

```bash
pip install -r requirements.txt
pip install -r requirements-analysis.txt
```

### 3. NLP Models

Download required NLP models:

```bash
# SpaCy language model
python -m spacy download en_core_web_sm

# NLTK data
python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords')"
```

### 4. Database Migration

Run the social media migration:

```bash
psql -d opengovt -f app/db/migrations/003_social_media_tables.sql
```

## Database Schema

### Core Tables

#### `social_media_profiles`
Stores social media profile information for politicians.

**Key fields:**
- `person_id`: Links to legislators table
- `platform`: 'twitter', 'facebook', 'youtube', etc.
- `username`: Social media handle
- `followers_count`, `following_count`: Profile metrics
- `verified`: Verification status

#### `politician_tweets`
Stores tweets from politicians.

**Key fields:**
- `tweet_id`: Unique Twitter tweet ID
- `text`: Tweet content
- `created_at`: Tweet timestamp
- `like_count`, `retweet_count`, `reply_count`: Engagement metrics
- `tweet_type`: 'original', 'retweet', 'quote', 'reply'

#### `tweet_replies`
Stores replies to politician tweets.

**Key fields:**
- `original_tweet_id`: References politician_tweets
- `reply_user_id`: Twitter user ID of replier
- `reply_text`: Content of reply
- `reply_user_followers`: Follower count of replier

### Analysis Tables

#### `tweet_sentiment`
Sentiment analysis results for tweets.

**Scores:**
- `compound_score`: Overall sentiment (-1 to 1)
- `positive_score`, `negative_score`, `neutral_score`: Component scores
- `sentiment_label`: 'positive', 'negative', 'neutral'

#### `reply_toxicity`
Toxicity analysis for replies (hate speech detection).

**Scores:**
- `toxicity_score`: Overall toxicity (0 to 1)
- `severe_toxicity_score`, `identity_attack_score`, `insult_score`
- `is_toxic`, `is_hate_speech`: Boolean flags

#### `political_statements`
Extracted political statements at multiple granularity levels.

**Example:**
- `statement_full`: "Senator X voted to increase taxes 5 percent in VA last year"
- `statement_medium`: "Senator X voted to increase taxes 5 percent"
- `statement_short`: "Senator X voted to increase taxes"

## Data Ingestion

### Collecting Tweets

Use the `twitter_ingestion.py` script to collect tweets:

```bash
# Set database URL as environment variable (required)
export DATABASE_URL="postgresql://user:pass@localhost/opengovt"

# Collect tweets for a specific politician
python scripts/twitter_ingestion.py \
  --person-id 123 \
  --username SenatorSmith \
  --days 30 \
  --include-replies \
  --max-tweets 1000
```

**Parameters:**
- `--person-id`: Database ID of the person (legislators table)
- `--username`: Twitter username (without @)
- `--days`: Number of days of history to fetch (default: 30)
- `--include-replies`: Also fetch replies to each tweet
- `--max-tweets`: Maximum number of tweets to collect (default: 1000)

**Note:** Database connection URL must be provided via the `DATABASE_URL` environment variable for security reasons. Never pass database credentials via command-line arguments.

### Batch Processing

Create a configuration file `twitter_batch.json`:

```json
{
  "politicians": [
    {"person_id": 1, "username": "SenSchumer"},
    {"person_id": 2, "username": "SenatorCollins"},
    {"person_id": 3, "username": "SenWarren"}
  ],
  "settings": {
    "days": 30,
    "include_replies": true,
    "max_tweets_per_person": 500
  }
}
```

Process batch:

```python
import json
from scripts.twitter_ingestion import TwitterAPIClient, TwitterDataProcessor, TwitterIngestionPipeline

# Load config
with open('twitter_batch.json') as f:
    config = json.load(f)

# Initialize
api = TwitterAPIClient()
processor = TwitterDataProcessor(DATABASE_URL)
pipeline = TwitterIngestionPipeline(api, processor)

# Process each politician
for pol in config['politicians']:
    pipeline.ingest_person_tweets(
        person_id=pol['person_id'],
        username=pol['username'],
        **config['settings']
    )
```

## Analysis Features

**Prerequisites:** All analysis scripts require the `DATABASE_URL` environment variable to be set:
```bash
export DATABASE_URL="postgresql://user:pass@localhost/opengovt"
```

### Sentiment Analysis

Run sentiment analysis on collected tweets and replies:

```bash
# Analyze all unprocessed tweets
python scripts/analyze_tweets.py --analyze-sentiment

# Analyze for specific person
python scripts/analyze_tweets.py --person-id 123 --analyze-sentiment

# Analyze both sentiment and toxicity
python scripts/analyze_tweets.py --analyze-all
```

**Models Used:**
1. **VADER**: Fast, social-media-optimized lexicon-based analyzer
2. **Transformer**: twitter-roberta-base-sentiment for higher accuracy

**Output:** Results stored in `tweet_sentiment` and `reply_sentiment` tables.

### Toxicity Detection

Detect toxic language and hate speech:

```bash
# Analyze toxicity in replies
python scripts/analyze_tweets.py --analyze-toxicity

# Batch process
python scripts/analyze_tweets.py --analyze-toxicity --batch-size 500
```

**Detects:**
- General toxicity
- Severe toxicity
- Identity-based attacks
- Insults and profanity
- Threats

**Hate Speech Classification:**
Combines identity_attack_score + toxicity_score for `is_hate_speech` flag.

### Political Statement Extraction

Extract actionable statements at multiple granularity levels:

```bash
# Extract from tweets
python scripts/extract_statements.py --source tweets

# Extract from vote records
python scripts/extract_statements.py --source votes

# Extract all sources
python scripts/extract_statements.py --source all --person-id 123
```

**Extraction Levels:**

1. **Short** (general action):
   - "Senator X voted to increase taxes"
   - Useful for broad categorization

2. **Medium** (with magnitude):
   - "Senator X voted to increase taxes 5 percent"
   - Adds quantitative details

3. **Full** (complete context):
   - "Senator X voted to increase taxes 5 percent in VA last year"
   - Includes location, timeframe, specific amounts

**Use Cases:**
- Profile summaries showing key positions
- Search and filtering by topic
- Comparison across different detail levels
- Timeline of position changes

## API Usage Examples

### Query Recent Tweets

```python
import psycopg2

conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

# Get recent tweets with sentiment
cursor.execute("""
    SELECT 
        pt.text,
        pt.created_at,
        pt.like_count,
        ts.sentiment_label,
        ts.compound_score
    FROM politician_tweets pt
    JOIN tweet_sentiment ts ON pt.id = ts.tweet_id
    WHERE pt.person_id = %s
    ORDER BY pt.created_at DESC
    LIMIT 20
""", (person_id,))

for text, created, likes, sentiment, score in cursor.fetchall():
    print(f"{created}: {text[:100]}... [{sentiment}: {score:.2f}]")
```

### Analyze Reply Toxicity

```python
# Get toxic reply statistics
cursor.execute("""
    SELECT 
        p.name,
        COUNT(DISTINCT tr.id) as total_replies,
        COUNT(DISTINCT CASE WHEN rt.is_toxic THEN tr.id END) as toxic_replies,
        AVG(rt.toxicity_score) as avg_toxicity,
        COUNT(DISTINCT CASE WHEN rt.is_hate_speech THEN tr.id END) as hate_speech_count
    FROM legislators p
    JOIN politician_tweets pt ON p.id = pt.person_id
    JOIN tweet_replies tr ON pt.id = tr.original_tweet_id
    LEFT JOIN reply_toxicity rt ON tr.id = rt.reply_id
    WHERE p.id = %s
    GROUP BY p.id, p.name
""", (person_id,))
```

### Get Political Statements by Subject

```python
# Get all tax-related statements
cursor.execute("""
    SELECT 
        p.name,
        ps.statement_full,
        ps.statement_medium,
        ps.statement_short,
        ps.stance,
        ps.confidence
    FROM political_statements ps
    JOIN legislators p ON ps.person_id = p.id
    WHERE ps.subject = 'taxes'
    AND ps.confidence > 0.7
    ORDER BY ps.extracted_at DESC
""")
```

### Daily Engagement Trends

```python
# Get engagement trends over time
cursor.execute("""
    SELECT 
        date,
        total_tweets,
        total_likes,
        total_retweets,
        avg_sentiment,
        toxic_replies_percentage
    FROM tweet_engagement_daily
    WHERE person_id = %s
    AND date >= CURRENT_DATE - INTERVAL '30 days'
    ORDER BY date DESC
""", (person_id,))
```

## Best Practices

### Rate Limiting

Twitter API has strict rate limits:
- **Tweet timeline**: 1,500 requests per 15 minutes
- **User lookup**: 900 requests per 15 minutes
- **Search (replies)**: 450 requests per 15 minutes

The ingestion script respects these limits with `wait_on_rate_limit=True`.

### Data Retention

Configure retention policies in `.env`:

```bash
TWEET_RETENTION_DAYS=365
LOG_RETENTION_DAYS=90
```

Cleanup old data:

```sql
-- Delete tweets older than retention period
DELETE FROM politician_tweets 
WHERE collected_at < NOW() - INTERVAL '365 days';

-- Delete orphaned analysis records
DELETE FROM tweet_sentiment 
WHERE tweet_id NOT IN (SELECT id FROM politician_tweets);
```

### Performance Optimization

1. **Batch Processing**: Process in batches of 100-500 records
2. **Indexes**: All foreign keys and frequently queried columns are indexed
3. **Views**: Use pre-built views for common queries
4. **Caching**: Cache model results for frequently analyzed tweets

### Privacy Considerations

1. **Reply Author Data**: Store minimal PII, anonymize if needed
2. **Toxic Content**: Consider redacting extreme content
3. **User Consent**: Respect Twitter's Terms of Service
4. **Data Access**: Implement role-based access control

### Monitoring

Track ingestion and analysis progress:

```python
# Monitor ingestion progress
cursor.execute("""
    SELECT 
        p.name,
        COUNT(pt.id) as tweets_collected,
        MAX(pt.created_at) as latest_tweet,
        COUNT(ts.id) as tweets_analyzed
    FROM legislators p
    LEFT JOIN politician_tweets pt ON p.id = pt.person_id
    LEFT JOIN tweet_sentiment ts ON pt.id = ts.tweet_id
    WHERE p.id IN (SELECT DISTINCT person_id FROM social_media_profiles)
    GROUP BY p.id, p.name
""")
```

### Error Handling

The scripts include comprehensive error handling:

- **Network errors**: Automatic retry with exponential backoff
- **API errors**: Rate limit detection and waiting
- **Data errors**: Skip invalid records, log errors
- **Database errors**: Transaction rollback, data integrity checks

Check logs for issues:

```bash
tail -f logs/twitter_ingestion.log
tail -f logs/analysis.log
```

## Advanced Features

### Real-Time Monitoring

Stream tweets in real-time (requires elevated Twitter API access):

```python
from scripts.twitter_ingestion import TwitterAPIClient
import tweepy

class PoliticianStreamListener(tweepy.StreamingClient):
    def on_tweet(self, tweet):
        # Process tweet immediately
        # Analyze sentiment, toxicity, extract statements
        pass

# Monitor specific accounts
stream = PoliticianStreamListener(bearer_token=BEARER_TOKEN)
stream.add_rules(tweepy.StreamRule("from:SenatorSmith"))
stream.filter()
```

### Scheduled Jobs

Use cron or systemd timers for regular updates:

```bash
# Crontab entry: Run every 6 hours
0 */6 * * * /path/to/venv/bin/python /path/to/scripts/twitter_ingestion.py --batch-config /path/to/config.json

# Crontab entry: Analyze new tweets every hour
0 * * * * /path/to/venv/bin/python /path/to/scripts/analyze_tweets.py --analyze-all --batch-size 1000
```

### Custom Analysis

Extend the analysis with custom models:

```python
from scripts.analyze_tweets import TweetAnalysisProcessor

class CustomAnalyzer(TweetAnalysisProcessor):
    def analyze_custom_metric(self, person_id=None):
        # Implement your custom analysis
        query = "SELECT id, text FROM politician_tweets WHERE ..."
        self.cursor.execute(query)
        
        for tweet_id, text in self.cursor.fetchall():
            result = your_custom_model(text)
            # Store result in database
```

## Troubleshooting

### Common Issues

1. **Twitter API Authentication Failed**
   - Verify credentials in `.env`
   - Check API access level (need elevated)
   - Regenerate tokens if expired

2. **Models Not Found**
   - Run model downloads (see Prerequisites)
   - Check MODEL_CACHE_DIR permissions

3. **Database Connection Error**
   - Verify DATABASE_URL format
   - Check PostgreSQL is running
   - Ensure migrations are applied

4. **Slow Analysis**
   - Reduce batch size
   - Enable GPU acceleration (for transformers)
   - Use cached model results

### Getting Help

- **Documentation**: See `docs/` directory
- **Issues**: Check GitHub issues
- **Logs**: Review `logs/` directory for detailed errors

## References

- [Twitter API v2 Documentation](https://developer.twitter.com/en/docs/twitter-api)
- [Tweepy Documentation](https://docs.tweepy.org/)
- [VADER Sentiment](https://github.com/cjhutto/vaderSentiment)
- [Detoxify](https://github.com/unitaryai/detoxify)
- [Transformers](https://huggingface.co/docs/transformers/)
