# Constituent Impact Measurement and Analysis

## Overview

This document covers methodologies for measuring how politicians impact their constituent base, tracking public opinion changes, analyzing responses to current events, and measuring the effectiveness of political communication.

## 1. Defining Constituent Impact

### 1.1 Impact Dimensions

```python
IMPACT_DIMENSIONS = {
    'opinion_change': 'Shift in constituent views on issues',
    'engagement': 'Level of constituent participation',
    'trust': 'Confidence in the politician',
    'awareness': 'Knowledge of politician positions',
    'mobilization': 'Action taken by constituents',
    'satisfaction': 'Constituent approval ratings'
}
```

### 1.2 Impact Measurement Framework

```
┌─────────────────────────────────────────────────────────┐
│                  POLITICIAN ACTION                       │
│  (Vote, Statement, Tweet, Bill Introduction)            │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              CONSTITUENT EXPOSURE                        │
│  (Social Media, News, Direct Communication)             │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│            CONSTITUENT RESPONSE                          │
│  (Comments, Shares, Polls, Actions)                     │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              MEASURED IMPACT                             │
│  (Opinion Change, Behavior Change, Trust Delta)         │
└─────────────────────────────────────────────────────────┘
```

## 2. Event Response Analysis

### 2.1 Current Events Tracking

```python
from datetime import datetime, timedelta
import numpy as np

class EventResponseTracker:
    def __init__(self):
        self.sentiment_analyzer = TweetSentimentAnalyzer()
        self.engagement_analyzer = EngagementAnalyzer()
    
    def track_event_response(self, politician_id, event_keywords, 
                            event_date, window_days=7):
        """
        Track how constituents respond when politician comments on event
        """
        # Define time windows
        before_window = (event_date - timedelta(days=window_days), event_date)
        after_window = (event_date, event_date + timedelta(days=window_days))
        
        # Get politician's tweets about event
        event_tweets = self._get_event_tweets(
            politician_id, event_keywords, after_window
        )
        
        if not event_tweets:
            return {'error': 'Politician did not tweet about this event'}
        
        # Baseline sentiment before event
        baseline_tweets = get_politician_tweets_in_range(
            politician_id, before_window[0], before_window[1]
        )
        baseline_sentiment = self._calculate_avg_sentiment(baseline_tweets)
        baseline_engagement = self._calculate_avg_engagement(baseline_tweets)
        
        # Response to event tweets
        event_responses = []
        for tweet in event_tweets:
            replies = get_tweet_replies(tweet.id)
            
            reply_analysis = {
                'tweet_id': tweet.id,
                'tweet_text': tweet.text,
                'tweet_time': tweet.created_at,
                'hours_after_event': (tweet.created_at - event_date).total_seconds() / 3600,
                'reply_count': len(replies),
                'avg_reply_sentiment': self._calculate_avg_sentiment(replies),
                'engagement': {
                    'likes': tweet.public_metrics['like_count'],
                    'retweets': tweet.public_metrics['retweet_count'],
                    'replies': tweet.public_metrics['reply_count']
                }
            }
            
            event_responses.append(reply_analysis)
        
        # Calculate impact metrics
        avg_response_sentiment = np.mean([r['avg_reply_sentiment'] for r in event_responses])
        avg_response_engagement = np.mean([
            r['engagement']['likes'] + r['engagement']['retweets'] 
            for r in event_responses
        ])
        
        return {
            'event': ' '.join(event_keywords),
            'event_date': event_date,
            'politician_id': politician_id,
            'baseline': {
                'sentiment': baseline_sentiment,
                'engagement': baseline_engagement
            },
            'response': {
                'sentiment': avg_response_sentiment,
                'engagement': avg_response_engagement,
                'tweet_count': len(event_tweets)
            },
            'impact': {
                'sentiment_change': avg_response_sentiment - baseline_sentiment,
                'engagement_change_pct': (
                    (avg_response_engagement - baseline_engagement) / 
                    max(baseline_engagement, 1) * 100
                ),
                'mobilization_score': self._calculate_mobilization(event_responses)
            },
            'detailed_responses': event_responses
        }
    
    def _get_event_tweets(self, politician_id, keywords, time_range):
        """Get tweets about specific event"""
        all_tweets = get_politician_tweets_in_range(
            politician_id, time_range[0], time_range[1]
        )
        
        return [
            t for t in all_tweets
            if any(kw.lower() in t.text.lower() for kw in keywords)
        ]
    
    def _calculate_avg_sentiment(self, tweets):
        """Calculate average sentiment of tweets/replies"""
        if not tweets:
            return 0
        
        sentiments = [
            self.sentiment_analyzer.analyze_tweet(t.text)['vader']['compound']
            for t in tweets
        ]
        return np.mean(sentiments)
    
    def _calculate_avg_engagement(self, tweets):
        """Calculate average engagement per tweet"""
        if not tweets:
            return 0
        
        engagement_scores = [
            t.public_metrics['like_count'] + 
            t.public_metrics['retweet_count'] * 2 +
            t.public_metrics['reply_count']
            for t in tweets
        ]
        return np.mean(engagement_scores)
    
    def _calculate_mobilization(self, responses):
        """
        Calculate how much the event mobilized constituents
        Based on engagement velocity and reply rate
        """
        if not responses:
            return 0
        
        # High reply rate indicates mobilization
        reply_rates = [r['reply_count'] / max(r['engagement']['likes'], 1) for r in responses]
        avg_reply_rate = np.mean(reply_rates)
        
        # Normalize to 0-100 scale
        mobilization_score = min(100, avg_reply_rate * 100)
        
        return mobilization_score
```

### 2.2 Position Shift Detection

```python
class PositionShiftDetector:
    """
    Detect when a politician's position changes and measure constituent reaction
    """
    
    def detect_position_shift(self, politician_id, issue, timeframe_months=12):
        """
        Detect position changes on an issue and measure impact
        """
        from sentence_transformers import SentenceTransformer, util
        
        # Get all statements about issue
        statements = get_politician_statements_about_issue(
            politician_id, issue, months=timeframe_months
        )
        
        if len(statements) < 2:
            return {'error': 'Insufficient data'}
        
        # Sort chronologically
        statements.sort(key=lambda x: x['date'])
        
        # Embed statements
        model = SentenceTransformer('all-mpnet-base-v2')
        embeddings = [model.encode(s['text']) for s in statements]
        
        # Detect shifts (low similarity between consecutive statements)
        shifts = []
        for i in range(len(statements) - 1):
            similarity = util.cos_sim(embeddings[i], embeddings[i+1]).item()
            
            if similarity < 0.7:  # Significant change
                # Also check sentiment change
                sent1 = self.sentiment_analyzer.analyze_tweet(statements[i]['text'])
                sent2 = self.sentiment_analyzer.analyze_tweet(statements[i+1]['text'])
                
                sentiment_flip = (sent1['vader']['compound'] * sent2['vader']['compound']) < 0
                
                if sentiment_flip:
                    # Measure constituent reaction
                    reaction = self._measure_shift_reaction(
                        politician_id,
                        statements[i],
                        statements[i+1]
                    )
                    
                    shifts.append({
                        'issue': issue,
                        'before': statements[i],
                        'after': statements[i+1],
                        'similarity': similarity,
                        'sentiment_flip': sentiment_flip,
                        'reaction': reaction
                    })
        
        return {
            'position_shifts_detected': len(shifts),
            'shifts': shifts
        }
    
    def _measure_shift_reaction(self, politician_id, before_statement, after_statement):
        """Measure how constituents reacted to position shift"""
        
        # Get social media engagement before and after
        before_date = before_statement['date']
        after_date = after_statement['date']
        
        # Get tweets in windows around each statement
        before_tweets = get_politician_tweets_in_range(
            politician_id,
            before_date - timedelta(days=3),
            before_date + timedelta(days=3)
        )
        
        after_tweets = get_politician_tweets_in_range(
            politician_id,
            after_date - timedelta(days=3),
            after_date + timedelta(days=3)
        )
        
        # Compare engagement and sentiment
        before_engagement = self._calculate_avg_engagement(before_tweets)
        after_engagement = self._calculate_avg_engagement(after_tweets)
        
        # Get replies to measure reaction
        after_replies = []
        for tweet in after_tweets:
            after_replies.extend(get_tweet_replies(tweet.id))
        
        reply_sentiment = self._calculate_avg_sentiment(after_replies)
        
        # Check for backlash keywords
        backlash_keywords = ['flip-flop', 'hypocrite', 'changed', 'liar', 'betrayed']
        backlash_count = sum(
            1 for reply in after_replies
            if any(kw in reply.text.lower() for kw in backlash_keywords)
        )
        
        return {
            'engagement_change_pct': (
                (after_engagement - before_engagement) / 
                max(before_engagement, 1) * 100
            ),
            'reply_sentiment': reply_sentiment,
            'backlash_mentions': backlash_count,
            'backlash_rate': backlash_count / max(len(after_replies), 1) * 100,
            'severity': 'high' if backlash_count > 10 else 'medium' if backlash_count > 3 else 'low'
        }
```

## 3. Polling and Opinion Tracking

### 3.1 Sentiment Polling

```python
class SentimentPoller:
    """
    Track constituent sentiment over time using social media as proxy polling
    """
    
    def conduct_sentiment_poll(self, politician_id, sample_size=1000):
        """
        Sample recent constituent interactions for sentiment
        """
        # Get recent tweets
        politician_tweets = get_politician_tweets(politician_id, days=7)
        
        # Sample replies
        sampled_replies = []
        for tweet in politician_tweets:
            replies = get_tweet_replies(tweet.id, max_results=100)
            sampled_replies.extend(replies)
            
            if len(sampled_replies) >= sample_size:
                break
        
        # Random sample
        import random
        if len(sampled_replies) > sample_size:
            sampled_replies = random.sample(sampled_replies, sample_size)
        
        # Analyze sentiment
        sentiment_counts = {'positive': 0, 'neutral': 0, 'negative': 0}
        sentiment_scores = []
        
        for reply in sampled_replies:
            analysis = self.sentiment_analyzer.analyze_tweet(reply.text)
            sentiment = analysis['overall_sentiment']
            sentiment_counts[sentiment] += 1
            sentiment_scores.append(analysis['vader']['compound'])
        
        # Calculate statistics
        total = len(sampled_replies)
        
        return {
            'sample_size': total,
            'date': datetime.now(),
            'distribution': {
                'positive': round(sentiment_counts['positive'] / total * 100, 2),
                'neutral': round(sentiment_counts['neutral'] / total * 100, 2),
                'negative': round(sentiment_counts['negative'] / total * 100, 2)
            },
            'avg_sentiment': round(np.mean(sentiment_scores), 3),
            'approval_rating_proxy': round(sentiment_counts['positive'] / total * 100, 2),
            'disapproval_rating_proxy': round(sentiment_counts['negative'] / total * 100, 2),
            'net_approval': round(
                (sentiment_counts['positive'] - sentiment_counts['negative']) / total * 100, 2
            )
        }
    
    def track_approval_over_time(self, politician_id, months=6):
        """Track approval trends over time"""
        
        polls = []
        for month in range(months):
            start_date = datetime.now() - timedelta(days=30 * (month + 1))
            
            # Get historical data
            # In practice, you'd have stored polls
            poll_data = self._get_historical_poll(politician_id, start_date)
            polls.append(poll_data)
        
        # Calculate trend
        approvals = [p['approval_rating_proxy'] for p in polls]
        trend = np.polyfit(range(len(approvals)), approvals, 1)[0]
        
        return {
            'polls': polls,
            'trend': 'improving' if trend > 0.5 else 'declining' if trend < -0.5 else 'stable',
            'current_approval': polls[0]['approval_rating_proxy'],
            'avg_approval': np.mean(approvals),
            'volatility': np.std(approvals)
        }
```

### 3.2 Issue-Specific Opinion Tracking

```python
class IssueOpinionTracker:
    """
    Track constituent opinions on specific issues
    """
    
    ISSUE_KEYWORDS = {
        'healthcare': ['healthcare', 'medicare', 'medicaid', 'insurance', 'ACA'],
        'immigration': ['immigration', 'border', 'DACA', 'asylum', 'refugees'],
        'climate': ['climate', 'environment', 'green', 'renewable', 'emissions'],
        'economy': ['economy', 'jobs', 'unemployment', 'inflation', 'wages'],
        'gun_control': ['gun', 'second amendment', '2A', 'firearm', 'NRA']
    }
    
    def track_issue_opinion(self, politician_id, issue, days=30):
        """
        Track what constituents think about politician's stance on an issue
        """
        if issue not in self.ISSUE_KEYWORDS:
            return {'error': f'Unknown issue: {issue}'}
        
        keywords = self.ISSUE_KEYWORDS[issue]
        
        # Get politician tweets about issue
        pol_tweets = get_politician_tweets(politician_id, days=days)
        issue_tweets = [
            t for t in pol_tweets
            if any(kw.lower() in t.text.lower() for kw in keywords)
        ]
        
        if not issue_tweets:
            return {'error': f'Politician has not tweeted about {issue} recently'}
        
        # Analyze politician's position
        pol_sentiments = [
            self.sentiment_analyzer.analyze_tweet(t.text)['vader']['compound']
            for t in issue_tweets
        ]
        pol_position = np.mean(pol_sentiments)
        
        # Get constituent responses
        constituent_replies = []
        for tweet in issue_tweets:
            replies = get_tweet_replies(tweet.id)
            constituent_replies.extend(replies)
        
        # Analyze constituent sentiment
        const_sentiments = [
            self.sentiment_analyzer.analyze_tweet(r.text)['vader']['compound']
            for r in constituent_replies
        ]
        const_position = np.mean(const_sentiments) if const_sentiments else 0
        
        # Calculate agreement
        agreement = 1 - abs(pol_position - const_position) / 2  # 0 to 1 scale
        
        # Categorize responses
        support_count = sum(1 for s in const_sentiments if s > 0.1)
        oppose_count = sum(1 for s in const_sentiments if s < -0.1)
        
        return {
            'issue': issue,
            'politician_position': pol_position,
            'constituent_position': const_position,
            'agreement_score': round(agreement * 100, 2),
            'constituent_breakdown': {
                'support': round(support_count / max(len(const_sentiments), 1) * 100, 2),
                'oppose': round(oppose_count / max(len(const_sentiments), 1) * 100, 2),
                'neutral': round(
                    (len(const_sentiments) - support_count - oppose_count) / 
                    max(len(const_sentiments), 1) * 100, 2
                )
            },
            'sample_size': len(constituent_replies)
        }
```

## 4. Mobilization Measurement

### 4.1 Action Tracking

```python
class MobilizationTracker:
    """
    Track when constituents take action based on politician's messaging
    """
    
    ACTION_INDICATORS = {
        'donation': ['donate', 'contribute', 'chip in', 'ActBlue', 'WinRed'],
        'volunteering': ['volunteer', 'canvass', 'phone bank', 'knock doors'],
        'voting': ['register to vote', 'vote', 'ballot', 'polls'],
        'contacting': ['call your senator', 'contact', 'write to'],
        'attending': ['rally', 'town hall', 'event', 'meeting'],
        'sharing': ['share this', 'retweet', 'spread the word']
    }
    
    def measure_call_to_action_effectiveness(self, politician_id, days=7):
        """
        Measure how effective calls to action are
        """
        tweets = get_politician_tweets(politician_id, days=days)
        
        cta_analysis = []
        
        for tweet in tweets:
            # Detect call to action
            cta_type = self._detect_cta(tweet.text)
            
            if not cta_type:
                continue
            
            # Measure response
            replies = get_tweet_replies(tweet.id)
            
            # Count action mentions in replies
            action_count = sum(
                1 for reply in replies
                if any(
                    indicator in reply.text.lower()
                    for indicators in self.ACTION_INDICATORS.values()
                    for indicator in indicators
                )
            )
            
            # Engagement
            engagement = (
                tweet.public_metrics['like_count'] +
                tweet.public_metrics['retweet_count'] * 2 +
                tweet.public_metrics['reply_count']
            )
            
            cta_analysis.append({
                'tweet': tweet.text,
                'cta_type': cta_type,
                'engagement': engagement,
                'replies_with_action': action_count,
                'action_rate': action_count / max(len(replies), 1) * 100,
                'effectiveness_score': self._calculate_effectiveness(
                    engagement, action_count, len(replies)
                )
            })
        
        # Aggregate results
        if not cta_analysis:
            return {'error': 'No calls to action found'}
        
        return {
            'total_ctas': len(cta_analysis),
            'avg_effectiveness': np.mean([c['effectiveness_score'] for c in cta_analysis]),
            'most_effective_cta_type': max(
                set(c['cta_type'] for c in cta_analysis),
                key=lambda x: np.mean([
                    c['effectiveness_score'] 
                    for c in cta_analysis if c['cta_type'] == x
                ])
            ),
            'detailed_ctas': sorted(
                cta_analysis,
                key=lambda x: x['effectiveness_score'],
                reverse=True
            )
        }
    
    def _detect_cta(self, text):
        """Detect type of call to action"""
        text_lower = text.lower()
        
        for action_type, indicators in self.ACTION_INDICATORS.items():
            if any(ind in text_lower for ind in indicators):
                return action_type
        
        return None
    
    def _calculate_effectiveness(self, engagement, action_mentions, reply_count):
        """
        Calculate CTA effectiveness score (0-100)
        Combines engagement with actual action mentions
        """
        # Normalize engagement (assuming 1000 is high engagement)
        engagement_score = min(100, (engagement / 1000) * 100)
        
        # Action rate score
        action_score = (action_mentions / max(reply_count, 1)) * 100
        
        # Weighted combination
        effectiveness = (engagement_score * 0.4 + action_score * 0.6)
        
        return round(effectiveness, 2)
```

### 4.2 Viral Content Analysis

```python
class ViralContentAnalyzer:
    """
    Analyze what content goes viral and its impact
    """
    
    def identify_viral_content(self, politician_id, days=30, viral_threshold=1000):
        """
        Identify viral tweets and analyze their impact
        """
        tweets = get_politician_tweets(politician_id, days=days)
        
        viral_tweets = []
        
        for tweet in tweets:
            engagement = (
                tweet.public_metrics['like_count'] +
                tweet.public_metrics['retweet_count'] * 3  # Retweets weighted more
            )
            
            if engagement >= viral_threshold:
                # Analyze spread
                spread_analysis = self._analyze_spread(tweet)
                
                # Sentiment of spread
                retweet_sentiment = self._analyze_retweet_sentiment(tweet)
                
                viral_tweets.append({
                    'tweet': tweet.text,
                    'date': tweet.created_at,
                    'engagement': engagement,
                    'reach_estimate': engagement * 100,  # Rough estimate
                    'spread_analysis': spread_analysis,
                    'retweet_sentiment': retweet_sentiment,
                    'topic': TweetTopicClassifier().classify_tweet(tweet.text)
                })
        
        if not viral_tweets:
            return {'message': 'No viral content in this period'}
        
        return {
            'viral_tweet_count': len(viral_tweets),
            'total_reach': sum(v['reach_estimate'] for v in viral_tweets),
            'viral_tweets': sorted(
                viral_tweets,
                key=lambda x: x['engagement'],
                reverse=True
            ),
            'common_topics': self._find_common_topics([v['topic'] for v in viral_tweets])
        }
    
    def _analyze_spread(self, tweet):
        """Analyze how tweet spread"""
        # Would need graph analysis of retweet network
        # Simplified version:
        return {
            'retweets': tweet.public_metrics['retweet_count'],
            'quotes': tweet.public_metrics['quote_count'],
            'spread_rate': 'viral' if tweet.public_metrics['retweet_count'] > 500 else 'moderate'
        }
    
    def _analyze_retweet_sentiment(self, tweet):
        """Analyze sentiment of people retweeting"""
        # Would analyze quote tweets
        # Simplified: assume retweets indicate agreement
        likes = tweet.public_metrics['like_count']
        retweets = tweet.public_metrics['retweet_count']
        
        agreement_ratio = retweets / max(likes, 1)
        
        return {
            'likely_agreement': agreement_ratio > 0.3,
            'engagement_type': 'supportive' if agreement_ratio > 0.3 else 'observational'
        }
```

## 5. Comparative Constituent Analysis

### 5.1 District vs. National Sentiment

```python
class DistrictSentimentComparer:
    """
    Compare district sentiment to national sentiment
    """
    
    def compare_district_national(self, politician_id, issue):
        """
        Compare how politician's district feels vs. nation
        """
        # Get politician's district
        politician = get_politician(politician_id)
        district = politician['district']
        
        # District sentiment (from followers in district)
        district_sentiment = self._get_district_sentiment(politician_id, district, issue)
        
        # National sentiment (from all Americans)
        national_sentiment = self._get_national_sentiment(issue)
        
        # Compare
        difference = district_sentiment - national_sentiment
        
        return {
            'issue': issue,
            'district': district,
            'district_sentiment': district_sentiment,
            'national_sentiment': national_sentiment,
            'difference': difference,
            'district_is_more': 'positive' if difference > 0.1 else 'negative' if difference < -0.1 else 'similar',
            'politician_alignment': self._check_politician_alignment(
                politician_id, issue, district_sentiment
            )
        }
    
    def _get_district_sentiment(self, politician_id, district, issue):
        """Get sentiment from politician's district"""
        # Would filter followers by location
        # Simplified version
        return 0.2  # Placeholder
    
    def _get_national_sentiment(self, issue):
        """Get national sentiment on issue"""
        # Would use polling aggregators or broad Twitter sample
        return 0.1  # Placeholder
    
    def _check_politician_alignment(self, politician_id, issue, district_sentiment):
        """Check if politician aligns with district"""
        opinion = IssueOpinionTracker().track_issue_opinion(politician_id, issue)
        
        if opinion.get('error'):
            return 'unknown'
        
        pol_position = opinion['politician_position']
        alignment = 1 - abs(pol_position - district_sentiment) / 2
        
        return {
            'alignment_score': round(alignment * 100, 2),
            'is_aligned': alignment > 0.6
        }
```

## 6. Database Schema

```sql
-- Constituent impact tracking
CREATE TABLE constituent_impact_events (
    id SERIAL PRIMARY KEY,
    politician_id INTEGER REFERENCES politicians(id),
    event_type VARCHAR(50),  -- 'vote', 'statement', 'tweet', 'bill'
    event_id VARCHAR(100),
    event_date TIMESTAMP,
    
    -- Pre-event baseline
    baseline_sentiment DECIMAL(4,3),
    baseline_engagement DECIMAL(10,2),
    
    -- Post-event metrics
    response_sentiment DECIMAL(4,3),
    response_engagement DECIMAL(10,2),
    mobilization_score DECIMAL(5,2),
    
    -- Impact calculation
    sentiment_change DECIMAL(4,3),
    engagement_change_pct DECIMAL(6,2),
    impact_score DECIMAL(5,2),
    
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE opinion_polls (
    id SERIAL PRIMARY KEY,
    politician_id INTEGER REFERENCES politicians(id),
    poll_date DATE,
    sample_size INTEGER,
    
    -- Sentiment distribution
    positive_pct DECIMAL(5,2),
    neutral_pct DECIMAL(5,2),
    negative_pct DECIMAL(5,2),
    
    -- Scores
    avg_sentiment DECIMAL(4,3),
    approval_proxy DECIMAL(5,2),
    net_approval DECIMAL(6,2)
);

CREATE TABLE issue_opinions (
    id SERIAL PRIMARY KEY,
    politician_id INTEGER REFERENCES politicians(id),
    issue VARCHAR(100),
    poll_date DATE,
    
    -- Positions
    politician_position DECIMAL(4,3),
    constituent_position DECIMAL(4,3),
    
    -- Agreement
    agreement_score DECIMAL(5,2),
    support_pct DECIMAL(5,2),
    oppose_pct DECIMAL(5,2),
    
    sample_size INTEGER
);

-- Indexes
CREATE INDEX idx_impact_politician ON constituent_impact_events(politician_id);
CREATE INDEX idx_impact_date ON constituent_impact_events(event_date);
CREATE INDEX idx_polls_politician ON opinion_polls(politician_id);
CREATE INDEX idx_opinions_issue ON issue_opinions(politician_id, issue);
```

## 7. Real-World Applications

### 7.1 Campaign Dashboard

```python
class CampaignImpactDashboard:
    """
    Real-time dashboard for campaign impact
    """
    
    def generate_dashboard(self, politician_id):
        """Generate comprehensive impact dashboard"""
        
        return {
            'current_approval': SentimentPoller().conduct_sentiment_poll(politician_id),
            'recent_events': EventResponseTracker().get_recent_event_responses(politician_id),
            'issue_positions': self._get_all_issue_positions(politician_id),
            'mobilization': MobilizationTracker().measure_call_to_action_effectiveness(politician_id),
            'viral_content': ViralContentAnalyzer().identify_viral_content(politician_id),
            'trends': SentimentPoller().track_approval_over_time(politician_id),
            'key_insights': self._generate_insights(politician_id)
        }
    
    def _get_all_issue_positions(self, politician_id):
        """Get positions on all major issues"""
        tracker = IssueOpinionTracker()
        issues = list(tracker.ISSUE_KEYWORDS.keys())
        
        return {
            issue: tracker.track_issue_opinion(politician_id, issue)
            for issue in issues
        }
    
    def _generate_insights(self, politician_id):
        """Generate actionable insights"""
        insights = []
        
        # Would analyze trends and patterns
        insights.append("Healthcare messaging resonates well with base")
        insights.append("Consider more engagement on economic issues")
        
        return insights
```

## 8. References

### Research Papers
1. **"Social Media and Political Engagement"** - Boulianne, 2015
2. **"Measuring Political Polarization with Social Media"** - Barbera et al., 2015
3. **"Twitter as a Proxy for Political Opinion"** - O'Connor et al., 2010

### Tools
- **Pew Research**: Public opinion data
- **FiveThirtyEight**: Polling aggregation
- **RealClearPolitics**: Approval ratings
- **Gallup**: Long-term polling trends

---

**Last Updated**: 2025-10-23
**Next**: [07-implementation-guide.md](07-implementation-guide.md)
