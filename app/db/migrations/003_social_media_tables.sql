-- Name: DB migration 003 - social media tables
-- Date: 2025-10-23
-- Description: Create tables for social media integration, Twitter/X data ingestion,
--              tweet analysis, sentiment tracking, and constituent engagement

BEGIN;

-- ==============================================================================
-- Social Media Profiles Table
-- ==============================================================================
-- Stores verified social media profile information for politicians/members
CREATE TABLE IF NOT EXISTS social_media_profiles (
  id SERIAL PRIMARY KEY,
  person_id INTEGER REFERENCES legislators(id) ON DELETE CASCADE,
  platform TEXT NOT NULL,  -- 'twitter', 'facebook', 'youtube', 'instagram', etc.
  username TEXT NOT NULL,
  profile_url TEXT,
  verified BOOLEAN DEFAULT FALSE,
  
  -- Profile metrics
  followers_count INTEGER,
  following_count INTEGER,
  posts_count INTEGER,
  
  -- Profile information
  display_name TEXT,
  bio TEXT,
  profile_image_url TEXT,
  
  -- Metadata
  account_created_at TIMESTAMP,
  first_collected_at TIMESTAMP DEFAULT now(),
  last_updated_at TIMESTAMP DEFAULT now(),
  is_active BOOLEAN DEFAULT TRUE,
  
  UNIQUE(person_id, platform, username)
);

CREATE INDEX idx_social_profiles_person ON social_media_profiles(person_id);
CREATE INDEX idx_social_profiles_platform ON social_media_profiles(platform);
CREATE INDEX idx_social_profiles_username ON social_media_profiles(platform, username);

-- ==============================================================================
-- Politician Tweets Table
-- ==============================================================================
CREATE TABLE IF NOT EXISTS politician_tweets (
  id SERIAL PRIMARY KEY,
  profile_id INTEGER REFERENCES social_media_profiles(id) ON DELETE CASCADE,
  person_id INTEGER REFERENCES legislators(id) ON DELETE CASCADE,
  
  -- Tweet identifiers
  tweet_id TEXT UNIQUE NOT NULL,
  conversation_id TEXT,  -- For threading
  
  -- Content
  text TEXT NOT NULL,
  language TEXT,
  
  -- Tweet metadata
  created_at TIMESTAMP NOT NULL,
  tweet_type TEXT,  -- 'original', 'retweet', 'quote', 'reply'
  is_retweet BOOLEAN DEFAULT FALSE,
  is_reply BOOLEAN DEFAULT FALSE,
  is_quote BOOLEAN DEFAULT FALSE,
  
  -- References to other tweets
  reply_to_tweet_id TEXT,
  retweet_of_tweet_id TEXT,
  quote_of_tweet_id TEXT,
  
  -- Engagement metrics (stored at collection time)
  like_count INTEGER DEFAULT 0,
  retweet_count INTEGER DEFAULT 0,
  reply_count INTEGER DEFAULT 0,
  quote_count INTEGER DEFAULT 0,
  impression_count INTEGER,
  
  -- Media attachments
  has_media BOOLEAN DEFAULT FALSE,
  media_urls JSONB,  -- Array of media URLs
  media_types JSONB,  -- Array of media types (photo, video, gif)
  
  -- URLs and mentions
  urls JSONB,  -- Extracted URLs from tweet
  hashtags JSONB,  -- Extracted hashtags
  mentions JSONB,  -- Mentioned users
  
  -- Collection metadata
  collected_at TIMESTAMP DEFAULT now(),
  last_metrics_update TIMESTAMP,
  
  -- Raw data
  raw_data JSONB
);

CREATE INDEX idx_tweets_profile ON politician_tweets(profile_id);
CREATE INDEX idx_tweets_person ON politician_tweets(person_id);
CREATE INDEX idx_tweets_id ON politician_tweets(tweet_id);
CREATE INDEX idx_tweets_created ON politician_tweets(created_at);
CREATE INDEX idx_tweets_conversation ON politician_tweets(conversation_id);
CREATE INDEX idx_tweets_type ON politician_tweets(tweet_type);

-- ==============================================================================
-- Tweet Replies Table
-- ==============================================================================
CREATE TABLE IF NOT EXISTS tweet_replies (
  id SERIAL PRIMARY KEY,
  original_tweet_id INTEGER REFERENCES politician_tweets(id) ON DELETE CASCADE,
  
  -- Reply identifiers
  reply_tweet_id TEXT UNIQUE NOT NULL,
  conversation_id TEXT,
  
  -- Reply author info
  reply_user_id TEXT,
  reply_username TEXT,
  reply_user_display_name TEXT,
  reply_user_verified BOOLEAN,
  reply_user_followers INTEGER,
  
  -- Content
  reply_text TEXT NOT NULL,
  language TEXT,
  
  -- Engagement metrics
  like_count INTEGER DEFAULT 0,
  retweet_count INTEGER DEFAULT 0,
  reply_count INTEGER DEFAULT 0,
  
  -- Metadata
  created_at TIMESTAMP NOT NULL,
  collected_at TIMESTAMP DEFAULT now(),
  
  -- Raw data
  raw_data JSONB
);

CREATE INDEX idx_replies_original ON tweet_replies(original_tweet_id);
CREATE INDEX idx_replies_id ON tweet_replies(reply_tweet_id);
CREATE INDEX idx_replies_user ON tweet_replies(reply_user_id);
CREATE INDEX idx_replies_created ON tweet_replies(created_at);

-- ==============================================================================
-- Tweet Sentiment Analysis
-- ==============================================================================
CREATE TABLE IF NOT EXISTS tweet_sentiment (
  id SERIAL PRIMARY KEY,
  tweet_id INTEGER REFERENCES politician_tweets(id) ON DELETE CASCADE,
  
  -- Sentiment scores
  compound_score FLOAT,  -- Overall sentiment (-1 to 1)
  positive_score FLOAT,
  negative_score FLOAT,
  neutral_score FLOAT,
  
  -- Classification
  sentiment_label TEXT,  -- 'positive', 'negative', 'neutral'
  confidence FLOAT,
  
  -- Emotion detection
  emotions JSONB,  -- {'anger': 0.1, 'joy': 0.7, 'fear': 0.1, 'sadness': 0.1}
  
  -- Model info
  model_name TEXT DEFAULT 'vader',
  analyzed_at TIMESTAMP DEFAULT now(),
  
  UNIQUE(tweet_id, model_name)
);

CREATE INDEX idx_tweet_sentiment_tweet ON tweet_sentiment(tweet_id);
CREATE INDEX idx_tweet_sentiment_label ON tweet_sentiment(sentiment_label);

-- ==============================================================================
-- Reply Sentiment Analysis
-- ==============================================================================
CREATE TABLE IF NOT EXISTS reply_sentiment (
  id SERIAL PRIMARY KEY,
  reply_id INTEGER REFERENCES tweet_replies(id) ON DELETE CASCADE,
  
  -- Sentiment scores
  compound_score FLOAT,
  positive_score FLOAT,
  negative_score FLOAT,
  neutral_score FLOAT,
  
  -- Classification
  sentiment_label TEXT,
  confidence FLOAT,
  
  -- Emotion detection
  emotions JSONB,
  
  -- Model info
  model_name TEXT DEFAULT 'vader',
  analyzed_at TIMESTAMP DEFAULT now(),
  
  UNIQUE(reply_id, model_name)
);

CREATE INDEX idx_reply_sentiment_reply ON reply_sentiment(reply_id);
CREATE INDEX idx_reply_sentiment_label ON reply_sentiment(sentiment_label);

-- ==============================================================================
-- Tweet Toxicity Analysis
-- ==============================================================================
CREATE TABLE IF NOT EXISTS tweet_toxicity (
  id SERIAL PRIMARY KEY,
  tweet_id INTEGER REFERENCES politician_tweets(id) ON DELETE CASCADE,
  
  -- Toxicity scores (0 to 1)
  toxicity_score FLOAT,
  severe_toxicity_score FLOAT,
  identity_attack_score FLOAT,
  insult_score FLOAT,
  profanity_score FLOAT,
  threat_score FLOAT,
  
  -- Classification
  is_toxic BOOLEAN,
  toxicity_level TEXT,  -- 'low', 'medium', 'high', 'severe'
  
  -- Model info
  model_name TEXT DEFAULT 'detoxify',
  analyzed_at TIMESTAMP DEFAULT now(),
  
  UNIQUE(tweet_id, model_name)
);

CREATE INDEX idx_tweet_toxicity_tweet ON tweet_toxicity(tweet_id);
CREATE INDEX idx_tweet_toxicity_is_toxic ON tweet_toxicity(is_toxic) WHERE is_toxic = TRUE;

-- ==============================================================================
-- Reply Toxicity Analysis (Hate Speech Detection)
-- ==============================================================================
CREATE TABLE IF NOT EXISTS reply_toxicity (
  id SERIAL PRIMARY KEY,
  reply_id INTEGER REFERENCES tweet_replies(id) ON DELETE CASCADE,
  
  -- Toxicity scores
  toxicity_score FLOAT,
  severe_toxicity_score FLOAT,
  identity_attack_score FLOAT,
  insult_score FLOAT,
  profanity_score FLOAT,
  threat_score FLOAT,
  
  -- Classification
  is_toxic BOOLEAN,
  is_hate_speech BOOLEAN,
  toxicity_level TEXT,
  
  -- Model info
  model_name TEXT DEFAULT 'detoxify',
  analyzed_at TIMESTAMP DEFAULT now(),
  
  UNIQUE(reply_id, model_name)
);

CREATE INDEX idx_reply_toxicity_reply ON reply_toxicity(reply_id);
CREATE INDEX idx_reply_toxicity_is_toxic ON reply_toxicity(is_toxic) WHERE is_toxic = TRUE;
CREATE INDEX idx_reply_toxicity_hate_speech ON reply_toxicity(is_hate_speech) WHERE is_hate_speech = TRUE;

-- ==============================================================================
-- Tweet Topics/Categories
-- ==============================================================================
CREATE TABLE IF NOT EXISTS tweet_topics (
  id SERIAL PRIMARY KEY,
  tweet_id INTEGER REFERENCES politician_tweets(id) ON DELETE CASCADE,
  
  -- Topic classification
  topic TEXT NOT NULL,  -- 'healthcare', 'immigration', 'economy', etc.
  confidence FLOAT,
  
  -- Subtopics
  subtopics JSONB,
  
  -- Model info
  model_name TEXT,
  classified_at TIMESTAMP DEFAULT now()
);

CREATE INDEX idx_tweet_topics_tweet ON tweet_topics(tweet_id);
CREATE INDEX idx_tweet_topics_topic ON tweet_topics(topic);

-- ==============================================================================
-- Political Statement Extraction (Multi-granularity bins)
-- ==============================================================================
CREATE TABLE IF NOT EXISTS political_statements (
  id SERIAL PRIMARY KEY,
  person_id INTEGER REFERENCES legislators(id) ON DELETE CASCADE,
  source_type TEXT,  -- 'tweet', 'bill', 'speech', 'vote'
  source_id INTEGER,  -- Reference to the source (tweet_id, bill_id, etc.)
  
  -- Statement at different granularity levels
  statement_full TEXT,  -- e.g., "Senator X voted to increase taxes 5 percent in VA last year"
  statement_medium TEXT,  -- e.g., "Senator X voted to increase taxes 5 percent"
  statement_short TEXT,  -- e.g., "Senator X voted to increase taxes"
  
  -- Statement metadata
  action_type TEXT,  -- 'vote', 'statement', 'declaration', 'proposal'
  subject TEXT,  -- 'taxes', 'healthcare', 'immigration', etc.
  stance TEXT,  -- 'for', 'against', 'neutral'
  
  -- Details
  magnitude TEXT,  -- e.g., "5 percent"
  location TEXT,  -- e.g., "VA"
  timeframe TEXT,  -- e.g., "last year"
  
  -- Confidence and extraction
  confidence FLOAT,
  extraction_method TEXT,  -- 'rule_based', 'ml_model', 'manual'
  extracted_at TIMESTAMP DEFAULT now(),
  
  -- Related entities
  related_bill_id INTEGER REFERENCES bills(id),
  related_vote_id INTEGER REFERENCES votes(id),
  
  -- Metadata
  metadata JSONB
);

CREATE INDEX idx_statements_person ON political_statements(person_id);
CREATE INDEX idx_statements_source ON political_statements(source_type, source_id);
CREATE INDEX idx_statements_action ON political_statements(action_type);
CREATE INDEX idx_statements_subject ON political_statements(subject);

-- ==============================================================================
-- Tweet Engagement Summary (Daily aggregates)
-- ==============================================================================
CREATE TABLE IF NOT EXISTS tweet_engagement_daily (
  id SERIAL PRIMARY KEY,
  person_id INTEGER REFERENCES legislators(id) ON DELETE CASCADE,
  profile_id INTEGER REFERENCES social_media_profiles(id) ON DELETE CASCADE,
  date DATE NOT NULL,
  
  -- Tweet counts
  total_tweets INTEGER DEFAULT 0,
  original_tweets INTEGER DEFAULT 0,
  retweets INTEGER DEFAULT 0,
  replies INTEGER DEFAULT 0,
  quotes INTEGER DEFAULT 0,
  
  -- Engagement totals
  total_likes INTEGER DEFAULT 0,
  total_retweets INTEGER DEFAULT 0,
  total_replies_received INTEGER DEFAULT 0,
  total_quotes_received INTEGER DEFAULT 0,
  
  -- Averages
  avg_likes_per_tweet FLOAT,
  avg_retweets_per_tweet FLOAT,
  avg_sentiment FLOAT,
  
  -- Reply analysis
  total_replies_analyzed INTEGER DEFAULT 0,
  avg_reply_sentiment FLOAT,
  avg_reply_toxicity FLOAT,
  toxic_replies_count INTEGER DEFAULT 0,
  toxic_replies_percentage FLOAT,
  
  -- Sentiment distribution
  positive_tweets INTEGER DEFAULT 0,
  negative_tweets INTEGER DEFAULT 0,
  neutral_tweets INTEGER DEFAULT 0,
  
  -- Calculated at
  calculated_at TIMESTAMP DEFAULT now(),
  
  UNIQUE(person_id, profile_id, date)
);

CREATE INDEX idx_engagement_daily_person ON tweet_engagement_daily(person_id);
CREATE INDEX idx_engagement_daily_date ON tweet_engagement_daily(date);

-- ==============================================================================
-- Reply Author Profiles (Aggregate info about people responding)
-- ==============================================================================
CREATE TABLE IF NOT EXISTS reply_author_profiles (
  id SERIAL PRIMARY KEY,
  user_id TEXT UNIQUE NOT NULL,
  username TEXT,
  display_name TEXT,
  
  -- Profile info
  bio TEXT,
  location TEXT,
  profile_image_url TEXT,
  verified BOOLEAN,
  
  -- Metrics
  followers_count INTEGER,
  following_count INTEGER,
  tweet_count INTEGER,
  
  -- Account info
  account_created_at TIMESTAMP,
  
  -- Bot detection
  bot_likelihood_score FLOAT,  -- 0 to 1, higher = more likely bot
  is_likely_bot BOOLEAN,
  
  -- Political leaning (if detectable)
  estimated_political_leaning TEXT,  -- 'left', 'center', 'right', 'unknown'
  political_leaning_confidence FLOAT,
  
  -- Engagement with politician
  total_replies_to_person INTEGER DEFAULT 0,
  avg_reply_sentiment FLOAT,
  avg_reply_toxicity FLOAT,
  
  -- Collection metadata
  first_seen_at TIMESTAMP DEFAULT now(),
  last_updated_at TIMESTAMP DEFAULT now(),
  
  -- Raw data
  raw_data JSONB
);

CREATE INDEX idx_reply_authors_user_id ON reply_author_profiles(user_id);
CREATE INDEX idx_reply_authors_username ON reply_author_profiles(username);
CREATE INDEX idx_reply_authors_bot ON reply_author_profiles(is_likely_bot);

-- ==============================================================================
-- Political Polarity Analysis (of replies)
-- ==============================================================================
CREATE TABLE IF NOT EXISTS reply_political_polarity (
  id SERIAL PRIMARY KEY,
  reply_id INTEGER REFERENCES tweet_replies(id) ON DELETE CASCADE,
  
  -- Political disposition
  political_leaning TEXT,  -- 'left', 'center-left', 'center', 'center-right', 'right'
  polarity_score FLOAT,  -- -1 (left) to 1 (right)
  confidence FLOAT,
  
  -- Balance indicators
  is_balanced BOOLEAN,
  is_extreme BOOLEAN,
  
  -- Model info
  model_name TEXT,
  analyzed_at TIMESTAMP DEFAULT now(),
  
  UNIQUE(reply_id, model_name)
);

CREATE INDEX idx_polarity_reply ON reply_political_polarity(reply_id);
CREATE INDEX idx_polarity_leaning ON reply_political_polarity(political_leaning);

-- ==============================================================================
-- Tweet Attachment Media
-- ==============================================================================
CREATE TABLE IF NOT EXISTS tweet_media (
  id SERIAL PRIMARY KEY,
  tweet_id INTEGER REFERENCES politician_tweets(id) ON DELETE CASCADE,
  
  -- Media info
  media_key TEXT,
  media_type TEXT,  -- 'photo', 'video', 'animated_gif'
  media_url TEXT,
  preview_image_url TEXT,
  
  -- Video specific
  duration_ms INTEGER,
  view_count INTEGER,
  
  -- Dimensions
  width INTEGER,
  height INTEGER,
  
  -- Alt text
  alt_text TEXT,
  
  -- Collected
  collected_at TIMESTAMP DEFAULT now()
);

CREATE INDEX idx_media_tweet ON tweet_media(tweet_id);
CREATE INDEX idx_media_type ON tweet_media(media_type);

-- ==============================================================================
-- Views for Analysis
-- ==============================================================================

-- View: Latest tweet sentiment for each politician
CREATE OR REPLACE VIEW latest_tweet_sentiment AS
SELECT DISTINCT ON (p.id)
  p.id AS person_id,
  p.name,
  pt.tweet_id,
  pt.text AS tweet_text,
  pt.created_at AS tweet_created_at,
  ts.sentiment_label,
  ts.compound_score,
  pt.like_count,
  pt.retweet_count,
  pt.reply_count
FROM legislators p
JOIN politician_tweets pt ON p.id = pt.person_id
JOIN tweet_sentiment ts ON pt.id = ts.tweet_id
ORDER BY p.id, pt.created_at DESC;

-- View: Tweet engagement summary by politician
CREATE OR REPLACE VIEW politician_tweet_summary AS
SELECT
  p.id AS person_id,
  p.name,
  p.bioguide,
  COUNT(pt.id) AS total_tweets,
  AVG(pt.like_count) AS avg_likes,
  AVG(pt.retweet_count) AS avg_retweets,
  AVG(pt.reply_count) AS avg_replies,
  AVG(ts.compound_score) AS avg_sentiment,
  SUM(CASE WHEN ts.sentiment_label = 'positive' THEN 1 ELSE 0 END) AS positive_tweets,
  SUM(CASE WHEN ts.sentiment_label = 'negative' THEN 1 ELSE 0 END) AS negative_tweets,
  SUM(CASE WHEN ts.sentiment_label = 'neutral' THEN 1 ELSE 0 END) AS neutral_tweets
FROM legislators p
LEFT JOIN politician_tweets pt ON p.id = pt.person_id
LEFT JOIN tweet_sentiment ts ON pt.id = ts.tweet_id
GROUP BY p.id, p.name, p.bioguide;

-- View: Toxic reply analysis by politician
CREATE OR REPLACE VIEW politician_toxic_replies AS
SELECT
  p.id AS person_id,
  p.name,
  COUNT(tr.id) AS total_replies,
  SUM(CASE WHEN rt.is_toxic THEN 1 ELSE 0 END) AS toxic_replies,
  AVG(rt.toxicity_score) AS avg_toxicity,
  SUM(CASE WHEN rt.is_hate_speech THEN 1 ELSE 0 END) AS hate_speech_replies,
  ROUND(SUM(CASE WHEN rt.is_toxic THEN 1 ELSE 0 END)::NUMERIC / NULLIF(COUNT(tr.id), 0) * 100, 2) AS toxic_percentage
FROM legislators p
JOIN politician_tweets pt ON p.id = pt.person_id
JOIN tweet_replies tr ON pt.id = tr.original_tweet_id
LEFT JOIN reply_toxicity rt ON tr.id = rt.reply_id
GROUP BY p.id, p.name;

-- View: Political statement summary by person
CREATE OR REPLACE VIEW politician_statement_summary AS
SELECT
  p.id AS person_id,
  p.name,
  COUNT(ps.id) AS total_statements,
  COUNT(DISTINCT ps.subject) AS subjects_covered,
  ps.action_type,
  COUNT(*) AS count_by_action,
  STRING_AGG(DISTINCT ps.subject, ', ') AS subjects
FROM legislators p
JOIN political_statements ps ON p.id = ps.person_id
GROUP BY p.id, p.name, ps.action_type;

-- View: Tweet engagement trends (last 30 days)
CREATE OR REPLACE VIEW tweet_engagement_trends AS
SELECT
  ted.person_id,
  ted.date,
  ted.total_tweets,
  ted.total_likes,
  ted.total_retweets,
  ted.avg_sentiment,
  ted.toxic_replies_percentage,
  LAG(ted.avg_sentiment) OVER (PARTITION BY ted.person_id ORDER BY ted.date) AS prev_day_sentiment,
  LAG(ted.total_tweets) OVER (PARTITION BY ted.person_id ORDER BY ted.date) AS prev_day_tweets
FROM tweet_engagement_daily ted
WHERE ted.date >= CURRENT_DATE - INTERVAL '30 days'
ORDER BY ted.person_id, ted.date DESC;

COMMIT;

-- ==============================================================================
-- Notes:
-- ==============================================================================
-- 1. This schema supports comprehensive Twitter/X integration
-- 2. Multi-granularity statement extraction allows for different levels of detail
-- 3. Sentiment and toxicity analysis on both tweets and replies
-- 4. Political polarity detection on responses
-- 5. Bot detection for reply authors
-- 6. Daily aggregates for efficient reporting
-- 7. Views provide convenient access to common queries
-- 8. All tables have appropriate indexes for performance
