#!/usr/bin/env python3
"""
Twitter/X Data Ingestion Script

This script ingests tweets from politicians' Twitter accounts, including:
- Original tweets and engagement metrics
- Replies to tweets with author profile information
- Media attachments
- Real-time sentiment and toxicity analysis
- Political statement extraction

Usage:
    export DATABASE_URL="postgresql://user:pass@localhost:5432/opengovt"
    python twitter_ingestion.py --person-id 123 --days 30
    python twitter_ingestion.py --username SenatorSmith --include-replies
    python twitter_ingestion.py --config config.json --batch

Note: DATABASE_URL must be set as an environment variable for security.
"""

import os
import sys
import argparse
import json
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import asdict

import psycopg2
from psycopg2.extras import Json, execute_values

try:
    import tweepy
except ImportError:
    print("Error: tweepy is required. Install with: pip install tweepy")
    sys.exit(1)

# Import our models
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from models.social_media import (
    SocialMediaProfile,
    Tweet,
    TweetReply,
    TweetSentiment,
    TweetToxicity,
    ReplyAuthorProfile,
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TwitterAPIClient:
    """Wrapper for Twitter API v2 using tweepy."""
    
    def __init__(self, bearer_token: str = None, api_key: str = None,
                 api_secret: str = None, access_token: str = None,
                 access_secret: str = None):
        """Initialize Twitter API client."""
        self.bearer_token = bearer_token or os.getenv('TWITTER_BEARER_TOKEN')
        self.api_key = api_key or os.getenv('TWITTER_API_KEY')
        self.api_secret = api_secret or os.getenv('TWITTER_API_SECRET')
        self.access_token = access_token or os.getenv('TWITTER_ACCESS_TOKEN')
        self.access_secret = access_secret or os.getenv('TWITTER_ACCESS_SECRET')
        
        if not self.bearer_token:
            raise ValueError("Twitter Bearer Token is required")
        
        self.client = tweepy.Client(
            bearer_token=self.bearer_token,
            consumer_key=self.api_key,
            consumer_secret=self.api_secret,
            access_token=self.access_token,
            access_token_secret=self.access_secret,
            wait_on_rate_limit=True
        )
        
        logger.info("Twitter API client initialized")
    
    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user information by username."""
        try:
            user = self.client.get_user(
                username=username,
                user_fields=['id', 'name', 'username', 'description', 'public_metrics',
                           'verified', 'profile_image_url', 'created_at']
            )
            if user.data:
                return {
                    'user_id': user.data.id,
                    'username': user.data.username,
                    'display_name': user.data.name,
                    'bio': user.data.description,
                    'verified': user.data.verified if hasattr(user.data, 'verified') else False,
                    'profile_image_url': user.data.profile_image_url,
                    'account_created_at': user.data.created_at,
                    'followers_count': user.data.public_metrics['followers_count'],
                    'following_count': user.data.public_metrics['following_count'],
                    'tweet_count': user.data.public_metrics['tweet_count'],
                }
            return None
        except Exception as e:
            logger.error(f"Error fetching user {username}: {e}")
            return None
    
    def get_user_tweets(self, user_id: str, max_results: int = 100,
                       start_time: datetime = None, end_time: datetime = None,
                       pagination_token: str = None) -> Dict[str, Any]:
        """Fetch tweets from a user."""
        try:
            kwargs = {
                'id': user_id,
                'max_results': min(max_results, 100),
                'tweet_fields': ['created_at', 'public_metrics', 'entities', 
                               'referenced_tweets', 'conversation_id', 'lang'],
                'expansions': ['attachments.media_keys', 'referenced_tweets.id'],
                'media_fields': ['url', 'preview_image_url', 'type', 'duration_ms'],
            }
            
            if start_time:
                kwargs['start_time'] = start_time.isoformat()
            if end_time:
                kwargs['end_time'] = end_time.isoformat()
            if pagination_token:
                kwargs['pagination_token'] = pagination_token
            
            response = self.client.get_users_tweets(**kwargs)
            
            result = {
                'tweets': response.data if response.data else [],
                'media': response.includes.get('media', []) if response.includes else [],
                'meta': response.meta,
            }
            
            return result
        except Exception as e:
            logger.error(f"Error fetching tweets for user {user_id}: {e}")
            return {'tweets': [], 'media': [], 'meta': {}}
    
    def get_tweet_replies(self, tweet_id: str, max_results: int = 100) -> List[Any]:
        """Get replies to a specific tweet."""
        try:
            # Search for tweets in the conversation
            query = f"conversation_id:{tweet_id}"
            response = self.client.search_recent_tweets(
                query=query,
                max_results=min(max_results, 100),
                tweet_fields=['created_at', 'public_metrics', 'author_id', 'lang'],
                expansions=['author_id'],
                user_fields=['username', 'name', 'verified', 'public_metrics']
            )
            
            if not response.data:
                return []
            
            # Create a map of users
            users_map = {}
            if response.includes and 'users' in response.includes:
                for user in response.includes['users']:
                    users_map[user.id] = user
            
            # Combine tweet data with user data
            replies = []
            for tweet in response.data:
                user = users_map.get(tweet.author_id)
                reply_data = {
                    'tweet': tweet,
                    'user': user
                }
                replies.append(reply_data)
            
            return replies
        except Exception as e:
            logger.error(f"Error fetching replies for tweet {tweet_id}: {e}")
            return []


class TwitterDataProcessor:
    """Process and store Twitter data."""
    
    def __init__(self, db_connection_string: str):
        """Initialize data processor."""
        self.conn = psycopg2.connect(db_connection_string)
        self.cursor = self.conn.cursor()
        logger.info("Database connection established")
    
    def __del__(self):
        """Clean up database connection."""
        if hasattr(self, 'cursor'):
            self.cursor.close()
        if hasattr(self, 'conn'):
            self.conn.close()
    
    def get_or_create_profile(self, person_id: int, platform: str,
                              username: str, profile_data: Dict[str, Any]) -> int:
        """Get or create a social media profile."""
        # Check if profile exists
        self.cursor.execute(
            """
            SELECT id FROM social_media_profiles
            WHERE person_id = %s AND platform = %s AND username = %s
            """,
            (person_id, platform, username)
        )
        result = self.cursor.fetchone()
        
        if result:
            profile_id = result[0]
            # Update metrics
            self.cursor.execute(
                """
                UPDATE social_media_profiles
                SET followers_count = %s, following_count = %s, posts_count = %s,
                    last_updated_at = NOW()
                WHERE id = %s
                """,
                (profile_data.get('followers_count'), profile_data.get('following_count'),
                 profile_data.get('tweet_count'), profile_id)
            )
        else:
            # Create new profile
            self.cursor.execute(
                """
                INSERT INTO social_media_profiles
                (person_id, platform, username, display_name, bio, verified,
                 followers_count, following_count, posts_count, profile_image_url,
                 account_created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (person_id, platform, username, profile_data.get('display_name'),
                 profile_data.get('bio'), profile_data.get('verified'),
                 profile_data.get('followers_count'), profile_data.get('following_count'),
                 profile_data.get('tweet_count'), profile_data.get('profile_image_url'),
                 profile_data.get('account_created_at'))
            )
            profile_id = self.cursor.fetchone()[0]
        
        self.conn.commit()
        return profile_id
    
    def store_tweet(self, profile_id: int, person_id: int, tweet_data: Any,
                   media_data: List[Any] = None) -> int:
        """Store a tweet in the database."""
        # Extract tweet metadata
        tweet_type = 'original'
        is_retweet = False
        is_reply = False
        is_quote = False
        reply_to_id = None
        retweet_of_id = None
        quote_of_id = None
        
        if hasattr(tweet_data, 'referenced_tweets') and tweet_data.referenced_tweets:
            for ref in tweet_data.referenced_tweets:
                if ref.type == 'retweeted':
                    is_retweet = True
                    tweet_type = 'retweet'
                    retweet_of_id = ref.id
                elif ref.type == 'replied_to':
                    is_reply = True
                    tweet_type = 'reply'
                    reply_to_id = ref.id
                elif ref.type == 'quoted':
                    is_quote = True
                    tweet_type = 'quote'
                    quote_of_id = ref.id
        
        # Extract entities
        urls = []
        hashtags = []
        mentions = []
        
        if hasattr(tweet_data, 'entities') and tweet_data.entities:
            if 'urls' in tweet_data.entities:
                urls = [u.get('expanded_url', u.get('url')) for u in tweet_data.entities['urls']]
            if 'hashtags' in tweet_data.entities:
                hashtags = [h['tag'] for h in tweet_data.entities['hashtags']]
            if 'mentions' in tweet_data.entities:
                mentions = [m['username'] for m in tweet_data.entities['mentions']]
        
        # Extract media
        media_urls = []
        media_types = []
        has_media = False
        
        if media_data:
            has_media = True
            for media in media_data:
                media_urls.append(media.url if hasattr(media, 'url') else None)
                media_types.append(media.type if hasattr(media, 'type') else None)
        
        # Check if tweet already exists
        self.cursor.execute(
            "SELECT id FROM politician_tweets WHERE tweet_id = %s",
            (tweet_data.id,)
        )
        result = self.cursor.fetchone()
        
        if result:
            tweet_id = result[0]
            # Update metrics
            self.cursor.execute(
                """
                UPDATE politician_tweets
                SET like_count = %s, retweet_count = %s, reply_count = %s,
                    quote_count = %s, last_metrics_update = NOW()
                WHERE id = %s
                """,
                (tweet_data.public_metrics['like_count'],
                 tweet_data.public_metrics['retweet_count'],
                 tweet_data.public_metrics['reply_count'],
                 tweet_data.public_metrics.get('quote_count', 0),
                 tweet_id)
            )
        else:
            # Insert new tweet
            self.cursor.execute(
                """
                INSERT INTO politician_tweets
                (profile_id, person_id, tweet_id, conversation_id, text, language,
                 created_at, tweet_type, is_retweet, is_reply, is_quote,
                 reply_to_tweet_id, retweet_of_tweet_id, quote_of_tweet_id,
                 like_count, retweet_count, reply_count, quote_count,
                 has_media, media_urls, media_types, urls, hashtags, mentions)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (profile_id, person_id, tweet_data.id,
                 tweet_data.conversation_id if hasattr(tweet_data, 'conversation_id') else None,
                 tweet_data.text, tweet_data.lang if hasattr(tweet_data, 'lang') else None,
                 tweet_data.created_at, tweet_type, is_retweet, is_reply, is_quote,
                 reply_to_id, retweet_of_id, quote_of_id,
                 tweet_data.public_metrics['like_count'],
                 tweet_data.public_metrics['retweet_count'],
                 tweet_data.public_metrics['reply_count'],
                 tweet_data.public_metrics.get('quote_count', 0),
                 has_media, Json(media_urls), Json(media_types),
                 Json(urls), Json(hashtags), Json(mentions))
            )
            tweet_id = self.cursor.fetchone()[0]
        
        self.conn.commit()
        return tweet_id
    
    def store_reply(self, original_tweet_db_id: int, reply_data: Dict[str, Any]) -> int:
        """Store a reply to a tweet."""
        tweet = reply_data['tweet']
        user = reply_data.get('user')
        
        # Check if reply already exists
        self.cursor.execute(
            "SELECT id FROM tweet_replies WHERE reply_tweet_id = %s",
            (tweet.id,)
        )
        result = self.cursor.fetchone()
        
        if result:
            return result[0]
        
        # Insert new reply
        self.cursor.execute(
            """
            INSERT INTO tweet_replies
            (original_tweet_id, reply_tweet_id, conversation_id,
             reply_user_id, reply_username, reply_user_display_name,
             reply_user_verified, reply_user_followers,
             reply_text, language, like_count, retweet_count, reply_count,
             created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (original_tweet_db_id, tweet.id,
             tweet.conversation_id if hasattr(tweet, 'conversation_id') else None,
             str(tweet.author_id), user.username if user else None,
             user.name if user else None,
             user.verified if user and hasattr(user, 'verified') else False,
             user.public_metrics['followers_count'] if user else None,
             tweet.text, tweet.lang if hasattr(tweet, 'lang') else None,
             tweet.public_metrics['like_count'],
             tweet.public_metrics['retweet_count'],
             tweet.public_metrics['reply_count'],
             tweet.created_at)
        )
        reply_id = self.cursor.fetchone()[0]
        self.conn.commit()
        
        # Store reply author profile if available
        if user:
            self._store_reply_author_profile(user)
        
        return reply_id
    
    def _store_reply_author_profile(self, user: Any):
        """Store or update reply author profile."""
        self.cursor.execute(
            """
            INSERT INTO reply_author_profiles
            (user_id, username, display_name, verified, followers_count,
             following_count, tweet_count)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id) DO UPDATE SET
                username = EXCLUDED.username,
                display_name = EXCLUDED.display_name,
                verified = EXCLUDED.verified,
                followers_count = EXCLUDED.followers_count,
                following_count = EXCLUDED.following_count,
                tweet_count = EXCLUDED.tweet_count,
                last_updated_at = NOW()
            """,
            (str(user.id), user.username, user.name,
             user.verified if hasattr(user, 'verified') else False,
             user.public_metrics['followers_count'],
             user.public_metrics['following_count'],
             user.public_metrics['tweet_count'])
        )
        self.conn.commit()


class TwitterIngestionPipeline:
    """Main pipeline for ingesting Twitter data."""
    
    def __init__(self, api_client: TwitterAPIClient, processor: TwitterDataProcessor):
        """Initialize the pipeline."""
        self.api = api_client
        self.processor = processor
    
    def ingest_person_tweets(self, person_id: int, username: str,
                            days: int = 30, include_replies: bool = False,
                            max_tweets: int = 1000):
        """Ingest tweets for a person."""
        logger.info(f"Ingesting tweets for {username} (person_id={person_id})")
        
        # Get user profile
        user_data = self.api.get_user_by_username(username)
        if not user_data:
            logger.error(f"Could not find user {username}")
            return
        
        # Create or update profile
        profile_id = self.processor.get_or_create_profile(
            person_id, 'twitter', username, user_data
        )
        
        # Calculate time range
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days)
        
        # Fetch tweets with pagination
        pagination_token = None
        total_tweets = 0
        
        while total_tweets < max_tweets:
            result = self.api.get_user_tweets(
                user_data['user_id'],
                max_results=100,
                start_time=start_time,
                end_time=end_time,
                pagination_token=pagination_token
            )
            
            tweets = result['tweets']
            media = result['media']
            
            if not tweets:
                break
            
            # Create media map
            media_map = {}
            for m in media:
                media_map[m.media_key if hasattr(m, 'media_key') else m.get('media_key')] = m
            
            # Process each tweet
            for tweet in tweets:
                try:
                    # Get media for this tweet
                    tweet_media = []
                    if hasattr(tweet, 'attachments') and tweet.attachments:
                        media_keys = tweet.attachments.get('media_keys', [])
                        tweet_media = [media_map[k] for k in media_keys if k in media_map]
                    
                    # Store tweet
                    tweet_db_id = self.processor.store_tweet(
                        profile_id, person_id, tweet, tweet_media
                    )
                    
                    # Fetch and store replies if requested
                    if include_replies:
                        self._ingest_tweet_replies(tweet_db_id, tweet.id)
                    
                    total_tweets += 1
                    
                except Exception as e:
                    logger.error(f"Error processing tweet {tweet.id}: {e}")
            
            # Check for more pages
            if 'next_token' in result['meta']:
                pagination_token = result['meta']['next_token']
                time.sleep(1)  # Rate limiting
            else:
                break
        
        logger.info(f"Ingested {total_tweets} tweets for {username}")
    
    def _ingest_tweet_replies(self, tweet_db_id: int, tweet_id: str):
        """Ingest replies for a tweet."""
        try:
            replies = self.api.get_tweet_replies(tweet_id, max_results=100)
            
            for reply_data in replies:
                try:
                    self.processor.store_reply(tweet_db_id, reply_data)
                except Exception as e:
                    logger.error(f"Error storing reply: {e}")
        
        except Exception as e:
            logger.error(f"Error fetching replies for tweet {tweet_id}: {e}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Ingest Twitter data for politicians')
    parser.add_argument('--person-id', type=int, help='Database person ID')
    parser.add_argument('--username', type=str, help='Twitter username')
    parser.add_argument('--days', type=int, default=30, help='Days of history to fetch')
    parser.add_argument('--include-replies', action='store_true', help='Include replies to tweets')
    parser.add_argument('--max-tweets', type=int, default=1000, help='Maximum tweets to fetch')
    
    args = parser.parse_args()
    
    if not args.person_id or not args.username:
        parser.print_help()
        sys.exit(1)
    
    # Get database URL from environment variable only (more secure than CLI argument)
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        logger.error("DATABASE_URL environment variable is required")
        sys.exit(1)
    
    # Initialize components
    api_client = TwitterAPIClient()
    processor = TwitterDataProcessor(db_url)
    pipeline = TwitterIngestionPipeline(api_client, processor)
    
    # Run ingestion
    pipeline.ingest_person_tweets(
        args.person_id,
        args.username,
        days=args.days,
        include_replies=args.include_replies,
        max_tweets=args.max_tweets
    )
    
    logger.info("Ingestion complete")


if __name__ == '__main__':
    main()
