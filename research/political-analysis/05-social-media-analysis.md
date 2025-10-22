# Social Media Analysis for Political Entities

## Overview

This document covers comprehensive social media analysis for politicians, focusing on Twitter/X as the primary platform for political discourse, including tweet analysis, sentiment tracking, follower engagement, and constituent response measurement.

## 1. Twitter/X API Integration

### 1.1 API Setup and Authentication

```python
import tweepy
import os

class TwitterAPIClient:
    def __init__(self):
        # Twitter API v2 authentication
        self.client = tweepy.Client(
            bearer_token=os.getenv('TWITTER_BEARER_TOKEN'),
            consumer_key=os.getenv('TWITTER_API_KEY'),
            consumer_secret=os.getenv('TWITTER_API_SECRET'),
            access_token=os.getenv('TWITTER_ACCESS_TOKEN'),
            access_token_secret=os.getenv('TWITTER_ACCESS_SECRET'),
            wait_on_rate_limit=True
        )
    
    def get_user_tweets(self, username, max_results=100):
        """Fetch tweets from a politician's account"""
        
        # Get user ID
        user = self.client.get_user(username=username)
        user_id = user.data.id
        
        # Fetch tweets
        tweets = self.client.get_users_tweets(
            id=user_id,
            max_results=max_results,
            tweet_fields=['created_at', 'public_metrics', 'context_annotations', 
                         'entities', 'referenced_tweets'],
            expansions=['author_id', 'referenced_tweets.id'],
            user_fields=['public_metrics']
        )
        
        return tweets
    
    def get_tweet_replies(self, tweet_id, max_results=100):
        """Get replies to a specific tweet"""
        
        # Search for tweets that are replies to this tweet
        query = f"conversation_id:{tweet_id}"
        
        replies = self.client.search_recent_tweets(
            query=query,
            max_results=max_results,
            tweet_fields=['created_at', 'public_metrics', 'author_id'],
            expansions=['author_id']
        )
        
        return replies
    
    def get_user_metrics(self, username):
        """Get user account metrics"""
        
        user = self.client.get_user(
            username=username,
            user_fields=['public_metrics', 'description', 'created_at']
        )
        
        metrics = user.data.public_metrics
        
        return {
            'username': username,
            'followers': metrics['followers_count'],
            'following': metrics['following_count'],
            'tweets': metrics['tweet_count'],
            'listed': metrics['listed_count'],
            'account_created': user.data.created_at,
            'description': user.data.description
        }
```

### 1.2 Rate Limiting and Pagination

```python
import time
from datetime import datetime, timedelta

class TwitterDataCollector:
    def __init__(self, api_client):
        self.api = api_client
        self.rate_limit_window = 15 * 60  # 15 minutes
        self.requests_per_window = 180
    
    def collect_all_tweets(self, username, since_date=None):
        """
        Collect all tweets from a user with pagination
        """
        all_tweets = []
        pagination_token = None
        
        if since_date is None:
            since_date = datetime.now() - timedelta(days=30)
        
        while True:
            try:
                tweets = self.api.client.get_users_tweets(
                    username=username,
                    max_results=100,
                    start_time=since_date.isoformat(),
                    pagination_token=pagination_token,
                    tweet_fields=['created_at', 'public_metrics', 'entities']
                )
                
                if tweets.data:
                    all_tweets.extend(tweets.data)
                
                # Check for more pages
                if 'next_token' in tweets.meta:
                    pagination_token = tweets.meta['next_token']
                    time.sleep(1)  # Be nice to the API
                else:
                    break
                    
            except tweepy.errors.TooManyRequests:
                print("Rate limit reached, waiting...")
                time.sleep(self.rate_limit_window)
                continue
        
        return all_tweets
```

## 2. Tweet Content Analysis

### 2.1 Sentiment Analysis of Tweets

```python
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from transformers import pipeline

class TweetSentimentAnalyzer:
    def __init__(self):
        self.vader = SentimentIntensityAnalyzer()
        self.transformer = pipeline(
            "sentiment-analysis",
            model="cardiffnlp/twitter-roberta-base-sentiment"
        )
    
    def analyze_tweet(self, tweet_text):
        """Analyze sentiment of a single tweet"""
        
        # VADER analysis (good for social media)
        vader_scores = self.vader.polarity_scores(tweet_text)
        
        # Transformer analysis (more accurate)
        transformer_result = self.transformer(tweet_text[:512])[0]
        
        return {
            'text': tweet_text,
            'vader': {
                'compound': vader_scores['compound'],
                'positive': vader_scores['pos'],
                'negative': vader_scores['neg'],
                'neutral': vader_scores['neu']
            },
            'transformer': {
                'label': transformer_result['label'],
                'score': transformer_result['score']
            },
            'overall_sentiment': self._combine_sentiments(vader_scores, transformer_result)
        }
    
    def _combine_sentiments(self, vader, transformer):
        """Combine VADER and transformer results"""
        
        # Weight transformer more heavily
        vader_weight = 0.3
        transformer_weight = 0.7
        
        # Convert transformer to scale
        trans_score = transformer['score'] if transformer['label'] == 'POSITIVE' else -transformer['score']
        
        combined = (vader['compound'] * vader_weight + trans_score * transformer_weight)
        
        if combined > 0.05:
            return 'positive'
        elif combined < -0.05:
            return 'negative'
        else:
            return 'neutral'
```

### 2.2 Topic Classification

```python
from transformers import pipeline

class TweetTopicClassifier:
    def __init__(self):
        self.classifier = pipeline(
            "zero-shot-classification",
            model="facebook/bart-large-mnli"
        )
        
        self.political_topics = [
            'healthcare',
            'immigration',
            'economy',
            'climate change',
            'education',
            'foreign policy',
            'gun control',
            'taxation',
            'criminal justice',
            'voting rights',
            'abortion',
            'infrastructure'
        ]
    
    def classify_tweet(self, tweet_text):
        """Classify tweet into political topics"""
        
        result = self.classifier(
            tweet_text,
            self.political_topics,
            multi_label=True
        )
        
        # Get top 3 topics
        topics = []
        for label, score in zip(result['labels'], result['scores']):
            if score > 0.3:  # Confidence threshold
                topics.append({
                    'topic': label,
                    'confidence': round(score, 3)
                })
        
        return topics[:3]
```

### 2.3 Event Detection

```python
class PoliticalEventDetector:
    """Detect when politician tweets about specific events"""
    
    EVENT_KEYWORDS = {
        'bill_vote': ['vote', 'voting', 'passed', 'failed', 'HR', 'S.'],
        'campaign': ['campaign', 'rally', 'donate', 'volunteer'],
        'current_events': ['breaking', 'just in', 'today'],
        'crisis': ['emergency', 'crisis', 'urgent', 'critical'],
        'scandal': ['investigation', 'corruption', 'scandal'],
        'announcement': ['proud to announce', 'pleased to share', 'introducing']
    }
    
    def detect_event_type(self, tweet_text):
        """Detect what type of event the tweet is about"""
        
        text_lower = tweet_text.lower()
        detected_events = []
        
        for event_type, keywords in self.EVENT_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                detected_events.append(event_type)
        
        return detected_events if detected_events else ['general']
```

## 3. Follower Response Analysis

### 3.1 Reply Sentiment Analysis

```python
class ReplyAnalyzer:
    def __init__(self):
        self.sentiment_analyzer = TweetSentimentAnalyzer()
        self.toxicity_detector = DetoxifyAnalyzer()
    
    def analyze_replies(self, original_tweet_id, replies):
        """
        Analyze sentiment and toxicity of replies to a tweet
        """
        if not replies:
            return None
        
        results = {
            'original_tweet_id': original_tweet_id,
            'total_replies': len(replies),
            'sentiment_distribution': {'positive': 0, 'negative': 0, 'neutral': 0},
            'avg_sentiment': 0,
            'toxic_replies': 0,
            'avg_toxicity': 0,
            'top_replies': []
        }
        
        sentiment_scores = []
        toxicity_scores = []
        
        for reply in replies:
            # Sentiment analysis
            sentiment = self.sentiment_analyzer.analyze_tweet(reply.text)
            results['sentiment_distribution'][sentiment['overall_sentiment']] += 1
            sentiment_scores.append(sentiment['vader']['compound'])
            
            # Toxicity analysis
            toxicity = self.toxicity_detector.analyze(reply.text)
            toxicity_scores.append(toxicity['toxicity'])
            if toxicity['is_toxic']:
                results['toxic_replies'] += 1
            
            # Track top replies by engagement
            results['top_replies'].append({
                'text': reply.text,
                'likes': reply.public_metrics['like_count'],
                'retweets': reply.public_metrics['retweet_count'],
                'sentiment': sentiment['overall_sentiment'],
                'toxicity': toxicity['toxicity']
            })
        
        # Sort by engagement
        results['top_replies'].sort(
            key=lambda x: x['likes'] + x['retweets'] * 2,
            reverse=True
        )
        results['top_replies'] = results['top_replies'][:10]
        
        # Calculate averages
        results['avg_sentiment'] = sum(sentiment_scores) / len(sentiment_scores)
        results['avg_toxicity'] = sum(toxicity_scores) / len(toxicity_scores)
        results['toxic_percentage'] = (results['toxic_replies'] / len(replies)) * 100
        
        return results
```

### 3.2 Engagement Metrics

```python
class EngagementAnalyzer:
    def calculate_engagement_metrics(self, tweets):
        """
        Calculate comprehensive engagement metrics
        """
        if not tweets:
            return None
        
        metrics = {
            'total_tweets': len(tweets),
            'total_likes': 0,
            'total_retweets': 0,
            'total_replies': 0,
            'total_quotes': 0,
            'avg_likes': 0,
            'avg_retweets': 0,
            'avg_replies': 0,
            'engagement_rate': 0,
            'best_performing_tweets': [],
            'engagement_by_time': {}
        }
        
        total_engagement = 0
        
        for tweet in tweets:
            pm = tweet.public_metrics
            
            likes = pm['like_count']
            retweets = pm['retweet_count']
            replies = pm['reply_count']
            quotes = pm['quote_count']
            
            metrics['total_likes'] += likes
            metrics['total_retweets'] += retweets
            metrics['total_replies'] += replies
            metrics['total_quotes'] += quotes
            
            # Calculate tweet engagement score
            engagement_score = likes + (retweets * 2) + (replies * 1.5) + (quotes * 2)
            total_engagement += engagement_score
            
            # Track best tweets
            metrics['best_performing_tweets'].append({
                'text': tweet.text,
                'created_at': tweet.created_at,
                'engagement_score': engagement_score,
                'likes': likes,
                'retweets': retweets,
                'replies': replies
            })
            
            # Engagement by time of day
            hour = tweet.created_at.hour
            if hour not in metrics['engagement_by_time']:
                metrics['engagement_by_time'][hour] = []
            metrics['engagement_by_time'][hour].append(engagement_score)
        
        # Calculate averages
        metrics['avg_likes'] = metrics['total_likes'] / len(tweets)
        metrics['avg_retweets'] = metrics['total_retweets'] / len(tweets)
        metrics['avg_replies'] = metrics['total_replies'] / len(tweets)
        metrics['avg_engagement'] = total_engagement / len(tweets)
        
        # Sort best tweets
        metrics['best_performing_tweets'].sort(
            key=lambda x: x['engagement_score'],
            reverse=True
        )
        metrics['best_performing_tweets'] = metrics['best_performing_tweets'][:10]
        
        # Average engagement by hour
        for hour, scores in metrics['engagement_by_time'].items():
            metrics['engagement_by_time'][hour] = sum(scores) / len(scores)
        
        return metrics
```

## 4. Constituent Base Analysis

### 4.1 Follower Demographics (Approximate)

```python
class FollowerAnalyzer:
    def __init__(self, api_client):
        self.api = api_client
    
    def analyze_follower_sample(self, username, sample_size=1000):
        """
        Analyze a sample of followers
        Note: Full demographic data requires additional APIs
        """
        # Get followers
        followers = self.api.client.get_users_followers(
            username=username,
            max_results=min(sample_size, 1000),
            user_fields=['public_metrics', 'description', 'location', 'created_at']
        )
        
        if not followers.data:
            return None
        
        analysis = {
            'sample_size': len(followers.data),
            'avg_follower_count': 0,
            'avg_following_count': 0,
            'avg_tweets': 0,
            'locations': {},
            'account_ages': [],
            'verified_count': 0,
            'bot_likelihood': []
        }
        
        for follower in followers.data:
            metrics = follower.public_metrics
            
            analysis['avg_follower_count'] += metrics['followers_count']
            analysis['avg_following_count'] += metrics['following_count']
            analysis['avg_tweets'] += metrics['tweet_count']
            
            # Location analysis
            if follower.location:
                loc = follower.location
                analysis['locations'][loc] = analysis['locations'].get(loc, 0) + 1
            
            # Account age
            account_age = (datetime.now(follower.created_at.tzinfo) - follower.created_at).days
            analysis['account_ages'].append(account_age)
            
            # Bot detection (simple heuristic)
            bot_score = self._calculate_bot_likelihood(follower, metrics)
            analysis['bot_likelihood'].append(bot_score)
        
        # Calculate averages
        n = len(followers.data)
        analysis['avg_follower_count'] /= n
        analysis['avg_following_count'] /= n
        analysis['avg_tweets'] /= n
        analysis['avg_account_age_days'] = sum(analysis['account_ages']) / n
        analysis['estimated_bot_percentage'] = sum(
            1 for score in analysis['bot_likelihood'] if score > 0.7
        ) / n * 100
        
        # Top locations
        analysis['top_locations'] = sorted(
            analysis['locations'].items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        return analysis
    
    def _calculate_bot_likelihood(self, follower, metrics):
        """
        Simple bot detection heuristic
        Real implementation would use sophisticated ML models
        """
        score = 0
        
        # High following/follower ratio
        if metrics['following_count'] > 0:
            ratio = metrics['followers_count'] / metrics['following_count']
            if ratio < 0.1 or ratio > 10:
                score += 0.3
        
        # Very high tweet count relative to age
        account_age_days = (datetime.now(follower.created_at.tzinfo) - follower.created_at).days
        if account_age_days > 0:
            tweets_per_day = metrics['tweet_count'] / account_age_days
            if tweets_per_day > 50:
                score += 0.4
        
        # No profile description
        if not follower.description:
            score += 0.2
        
        # Default profile image would add 0.3 (not available in basic data)
        
        return min(1.0, score)
```

### 4.2 Response Correlation Analysis

```python
class ResponseCorrelationAnalyzer:
    """
    Analyze how constituent responses correlate with tweet content
    """
    
    def analyze_response_patterns(self, politician_tweets_with_replies):
        """
        Find patterns between tweet content and follower responses
        """
        from scipy.stats import pearsonr
        
        data_points = []
        
        for tweet_data in politician_tweets_with_replies:
            tweet = tweet_data['tweet']
            replies = tweet_data['replies']
            reply_analysis = tweet_data['reply_analysis']
            
            # Classify tweet
            sentiment_analyzer = TweetSentimentAnalyzer()
            topic_classifier = TweetTopicClassifier()
            
            tweet_sentiment = sentiment_analyzer.analyze_tweet(tweet.text)
            tweet_topics = topic_classifier.classify_tweet(tweet.text)
            
            data_points.append({
                'tweet_id': tweet.id,
                'tweet_sentiment': tweet_sentiment['vader']['compound'],
                'tweet_topics': tweet_topics,
                'reply_count': len(replies),
                'reply_avg_sentiment': reply_analysis['avg_sentiment'],
                'reply_positive_pct': reply_analysis['sentiment_distribution']['positive'] / len(replies) * 100,
                'reply_toxic_pct': reply_analysis['toxic_percentage'],
                'engagement_score': tweet.public_metrics['like_count'] + 
                                  tweet.public_metrics['retweet_count'] * 2
            })
        
        # Correlation analysis
        if len(data_points) < 10:
            return {'error': 'Insufficient data for correlation analysis'}
        
        # Extract arrays
        tweet_sentiments = [d['tweet_sentiment'] for d in data_points]
        reply_sentiments = [d['reply_avg_sentiment'] for d in data_points]
        reply_counts = [d['reply_count'] for d in data_points]
        toxic_pcts = [d['reply_toxic_pct'] for d in data_points]
        
        # Calculate correlations
        correlations = {
            'tweet_sentiment_vs_reply_sentiment': pearsonr(tweet_sentiments, reply_sentiments),
            'tweet_sentiment_vs_reply_count': pearsonr(tweet_sentiments, reply_counts),
            'tweet_sentiment_vs_toxicity': pearsonr(tweet_sentiments, toxic_pcts)
        }
        
        return {
            'data_points': data_points,
            'correlations': {
                k: {'correlation': v[0], 'p_value': v[1]}
                for k, v in correlations.items()
            },
            'insights': self._generate_insights(correlations, data_points)
        }
    
    def _generate_insights(self, correlations, data_points):
        """Generate human-readable insights"""
        insights = []
        
        # Sentiment correlation
        sent_corr = correlations['tweet_sentiment_vs_reply_sentiment'][0]
        if sent_corr > 0.5:
            insights.append("Positive tweets tend to receive positive responses")
        elif sent_corr < -0.5:
            insights.append("Positive tweets tend to receive negative responses (backlash)")
        
        # Engagement correlation
        reply_corr = correlations['tweet_sentiment_vs_reply_count'][0]
        if abs(reply_corr) > 0.3:
            sentiment_type = "positive" if reply_corr > 0 else "negative"
            insights.append(f"{sentiment_type.capitalize()} tweets generate more replies")
        
        # Toxicity correlation
        toxic_corr = correlations['tweet_sentiment_vs_toxicity'][0]
        if toxic_corr < -0.3:
            insights.append("Negative tweets receive more toxic responses")
        
        return insights
```

## 5. Campaign and Issue Tracking

### 5.1 Campaign Event Analysis

```python
class CampaignTweetAnalyzer:
    def track_campaign_issue(self, politician_id, issue_keywords, days=30):
        """
        Track how politician tweets about a campaign issue over time
        """
        # Get tweets
        tweets = get_politician_tweets(politician_id, days=days)
        
        # Filter for issue
        issue_tweets = [
            t for t in tweets
            if any(kw.lower() in t.text.lower() for kw in issue_keywords)
        ]
        
        if not issue_tweets:
            return {'error': 'No tweets found for this issue'}
        
        # Analyze sentiment over time
        sentiment_timeline = []
        engagement_timeline = []
        
        for tweet in issue_tweets:
            sentiment = TweetSentimentAnalyzer().analyze_tweet(tweet.text)
            
            sentiment_timeline.append({
                'date': tweet.created_at,
                'sentiment': sentiment['vader']['compound'],
                'text': tweet.text
            })
            
            engagement_timeline.append({
                'date': tweet.created_at,
                'likes': tweet.public_metrics['like_count'],
                'retweets': tweet.public_metrics['retweet_count'],
                'replies': tweet.public_metrics['reply_count']
            })
        
        # Calculate trend
        import numpy as np
        dates_numeric = [(s['date'] - sentiment_timeline[0]['date']).days for s in sentiment_timeline]
        sentiments = [s['sentiment'] for s in sentiment_timeline]
        
        if len(sentiments) > 1:
            trend = np.polyfit(dates_numeric, sentiments, 1)[0]
        else:
            trend = 0
        
        return {
            'issue': ' '.join(issue_keywords),
            'tweet_count': len(issue_tweets),
            'avg_sentiment': sum(sentiments) / len(sentiments),
            'sentiment_trend': 'improving' if trend > 0.01 else 'declining' if trend < -0.01 else 'stable',
            'total_engagement': sum(e['likes'] + e['retweets'] for e in engagement_timeline),
            'timeline': sentiment_timeline
        }
```

### 5.2 Real-Time Event Monitoring

```python
import tweepy

class RealTimeMonitor:
    def __init__(self, api_client):
        self.api = api_client
        
    def stream_politician_tweets(self, politician_usernames):
        """
        Stream tweets from politicians in real-time
        """
        class PoliticianStreamListener(tweepy.StreamingClient):
            def __init__(self, bearer_token, on_tweet_callback):
                super().__init__(bearer_token)
                self.on_tweet_callback = on_tweet_callback
            
            def on_tweet(self, tweet):
                # Process tweet immediately
                self.on_tweet_callback(tweet)
        
        def process_tweet(tweet):
            # Immediate analysis
            sentiment = TweetSentimentAnalyzer().analyze_tweet(tweet.text)
            
            # Store in database
            store_tweet_analysis({
                'tweet_id': tweet.id,
                'text': tweet.text,
                'sentiment': sentiment,
                'timestamp': datetime.now()
            })
            
            # Alert if significant
            if sentiment['vader']['compound'] < -0.7:
                send_alert(f"Highly negative tweet detected: {tweet.text[:100]}")
        
        # Create stream
        stream = PoliticianStreamListener(
            bearer_token=os.getenv('TWITTER_BEARER_TOKEN'),
            on_tweet_callback=process_tweet
        )
        
        # Add rules for politicians
        for username in politician_usernames:
            stream.add_rules(tweepy.StreamRule(f"from:{username}"))
        
        # Start streaming
        stream.filter()
```

## 6. Comparative Analysis

### 6.1 Cross-Politician Comparison

```python
class PoliticianComparison:
    def compare_twitter_presence(self, politician_ids):
        """
        Compare multiple politicians' Twitter presence
        """
        comparisons = []
        
        for pol_id in politician_ids:
            # Get data
            username = get_politician_twitter_handle(pol_id)
            tweets = get_politician_tweets(pol_id, days=30)
            
            # Analyze
            engagement = EngagementAnalyzer().calculate_engagement_metrics(tweets)
            
            # Sentiment
            sentiments = [
                TweetSentimentAnalyzer().analyze_tweet(t.text)['vader']['compound']
                for t in tweets
            ]
            
            comparisons.append({
                'politician_id': pol_id,
                'username': username,
                'tweets_per_day': len(tweets) / 30,
                'avg_engagement': engagement['avg_engagement'],
                'avg_sentiment': sum(sentiments) / len(sentiments) if sentiments else 0,
                'total_likes': engagement['total_likes'],
                'total_retweets': engagement['total_retweets']
            })
        
        # Rank
        for metric in ['tweets_per_day', 'avg_engagement', 'total_likes']:
            sorted_list = sorted(comparisons, key=lambda x: x[metric], reverse=True)
            for i, item in enumerate(sorted_list):
                item[f'{metric}_rank'] = i + 1
        
        return comparisons
```

## 7. Database Schema

```sql
-- Twitter data tables
CREATE TABLE politician_tweets (
    id BIGINT PRIMARY KEY,
    politician_id INTEGER REFERENCES politicians(id),
    tweet_id VARCHAR(100) UNIQUE,
    text TEXT,
    created_at TIMESTAMP,
    
    -- Metrics
    like_count INTEGER,
    retweet_count INTEGER,
    reply_count INTEGER,
    quote_count INTEGER,
    
    -- Analysis
    sentiment_score DECIMAL(4,3),
    sentiment_label VARCHAR(20),
    topics JSONB,
    event_type VARCHAR(50),
    
    -- Flags
    is_retweet BOOLEAN,
    is_reply BOOLEAN,
    
    collected_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE tweet_replies (
    id SERIAL PRIMARY KEY,
    original_tweet_id BIGINT REFERENCES politician_tweets(id),
    reply_tweet_id VARCHAR(100),
    reply_text TEXT,
    reply_user_id VARCHAR(100),
    created_at TIMESTAMP,
    
    -- Metrics
    like_count INTEGER,
    sentiment_score DECIMAL(4,3),
    toxicity_score DECIMAL(4,3),
    is_toxic BOOLEAN
);

CREATE TABLE tweet_engagement_summary (
    politician_id INTEGER REFERENCES politicians(id),
    date DATE,
    total_tweets INTEGER,
    total_likes INTEGER,
    total_retweets INTEGER,
    total_replies INTEGER,
    avg_sentiment DECIMAL(4,3),
    avg_toxicity_of_replies DECIMAL(4,3),
    PRIMARY KEY (politician_id, date)
);

-- Indexes
CREATE INDEX idx_tweets_politician ON politician_tweets(politician_id);
CREATE INDEX idx_tweets_created ON politician_tweets(created_at);
CREATE INDEX idx_replies_original ON tweet_replies(original_tweet_id);
```

## 8. References

### APIs and Tools
- **Twitter API v2**: https://developer.twitter.com/en/docs/twitter-api
- **Tweepy**: https://www.tweepy.org/
- **VADER Sentiment**: https://github.com/cjhutto/vaderSentiment
- **Botometer**: https://botometer.osome.iu.edu/ (bot detection)

### Research Papers
1. **"Sentiment Analysis on Twitter"** - Pak & Paroubek, 2010
2. **"Political Polarization on Twitter"** - Conover et al., 2011
3. **"Predicting Elections with Twitter"** - Tumasjan et al., 2010

### Best Practices
- Respect rate limits
- Handle privacy appropriately
- Anonymize user data
- Regular data validation
- Ethical use of analysis

---

**Last Updated**: 2025-10-22
**Next**: [06-constituent-impact.md](06-constituent-impact.md)
