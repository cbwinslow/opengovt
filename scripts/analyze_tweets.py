#!/usr/bin/env python3
"""
Tweet Analysis Script

Performs sentiment analysis, toxicity detection, and political statement extraction
on tweets and replies stored in the database.

Usage:
    python analyze_tweets.py --analyze-sentiment --analyze-toxicity
    python analyze_tweets.py --person-id 123 --analyze-all
    python analyze_tweets.py --extract-statements
"""

import os
import sys
import argparse
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

import psycopg2
from psycopg2.extras import Json

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SentimentAnalyzer:
    """Analyze sentiment of tweets and replies using VADER and transformers."""
    
    def __init__(self):
        """Initialize sentiment analysis models."""
        try:
            from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
            self.vader = SentimentIntensityAnalyzer()
            self.has_vader = True
            logger.info("VADER sentiment analyzer loaded")
        except ImportError:
            logger.warning("vaderSentiment not available. Install with: pip install vaderSentiment")
            self.has_vader = False
        
        try:
            from transformers import pipeline
            self.transformer = pipeline(
                "sentiment-analysis",
                model="cardiffnlp/twitter-roberta-base-sentiment-latest",
                top_k=None
            )
            self.has_transformer = True
            logger.info("Transformer sentiment analyzer loaded")
        except Exception as e:
            logger.warning(f"Transformers not available: {e}")
            self.has_transformer = False
    
    def analyze_text(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment of a text."""
        results = {
            'compound_score': 0.0,
            'positive_score': 0.0,
            'negative_score': 0.0,
            'neutral_score': 0.0,
            'sentiment_label': 'neutral',
            'confidence': 0.0,
            'emotions': {},
        }
        
        if not text or len(text.strip()) == 0:
            return results
        
        # VADER analysis
        if self.has_vader:
            vader_scores = self.vader.polarity_scores(text)
            results['compound_score'] = vader_scores['compound']
            results['positive_score'] = vader_scores['pos']
            results['negative_score'] = vader_scores['neg']
            results['neutral_score'] = vader_scores['neu']
            
            # Determine label from VADER
            if vader_scores['compound'] >= 0.05:
                results['sentiment_label'] = 'positive'
            elif vader_scores['compound'] <= -0.05:
                results['sentiment_label'] = 'negative'
            else:
                results['sentiment_label'] = 'neutral'
        
        # Transformer analysis (if available, use to refine results)
        if self.has_transformer:
            try:
                transformer_result = self.transformer(text[:512])[0]
                
                # Process transformer results
                scores_map = {}
                for item in transformer_result:
                    label = item['label'].lower()
                    score = item['score']
                    
                    if 'positive' in label:
                        scores_map['positive'] = score
                    elif 'negative' in label:
                        scores_map['negative'] = score
                    elif 'neutral' in label:
                        scores_map['neutral'] = score
                
                # Combine with VADER (transformer has higher weight)
                if scores_map:
                    max_label = max(scores_map, key=scores_map.get)
                    results['sentiment_label'] = max_label
                    results['confidence'] = scores_map[max_label]
                    
                    # Update scores with weighted average
                    vader_weight = 0.3
                    trans_weight = 0.7
                    results['positive_score'] = (
                        results['positive_score'] * vader_weight +
                        scores_map.get('positive', 0) * trans_weight
                    )
                    results['negative_score'] = (
                        results['negative_score'] * vader_weight +
                        scores_map.get('negative', 0) * trans_weight
                    )
                    results['neutral_score'] = (
                        results['neutral_score'] * vader_weight +
                        scores_map.get('neutral', 0) * trans_weight
                    )
            except Exception as e:
                logger.warning(f"Error in transformer analysis: {e}")
        
        return results


class ToxicityAnalyzer:
    """Analyze toxicity and hate speech in tweets and replies."""
    
    def __init__(self):
        """Initialize toxicity detection models."""
        try:
            from detoxify import Detoxify
            self.model = Detoxify('original')
            self.has_detoxify = True
            logger.info("Detoxify model loaded")
        except ImportError:
            logger.warning("Detoxify not available. Install with: pip install detoxify")
            self.has_detoxify = False
    
    def analyze_text(self, text: str) -> Dict[str, Any]:
        """Analyze toxicity of a text."""
        results = {
            'toxicity_score': 0.0,
            'severe_toxicity_score': 0.0,
            'identity_attack_score': 0.0,
            'insult_score': 0.0,
            'profanity_score': 0.0,
            'threat_score': 0.0,
            'is_toxic': False,
            'is_hate_speech': False,
            'toxicity_level': 'low',
        }
        
        if not text or len(text.strip()) == 0:
            return results
        
        if not self.has_detoxify:
            return results
        
        try:
            scores = self.model.predict(text)
            
            results['toxicity_score'] = float(scores.get('toxicity', 0))
            results['severe_toxicity_score'] = float(scores.get('severe_toxicity', 0))
            results['identity_attack_score'] = float(scores.get('identity_attack', 0))
            results['insult_score'] = float(scores.get('insult', 0))
            results['profanity_score'] = float(scores.get('profanity', 0))
            results['threat_score'] = float(scores.get('threat', 0))
            
            # Determine if toxic
            toxicity = results['toxicity_score']
            results['is_toxic'] = toxicity > 0.5
            
            # Determine toxicity level
            if toxicity >= 0.8:
                results['toxicity_level'] = 'severe'
            elif toxicity >= 0.6:
                results['toxicity_level'] = 'high'
            elif toxicity >= 0.4:
                results['toxicity_level'] = 'medium'
            else:
                results['toxicity_level'] = 'low'
            
            # Check for hate speech (combination of identity attack and toxicity)
            results['is_hate_speech'] = (
                results['identity_attack_score'] > 0.5 and
                results['toxicity_score'] > 0.5
            )
        
        except Exception as e:
            logger.error(f"Error in toxicity analysis: {e}")
        
        return results


class TweetAnalysisProcessor:
    """Process tweet analysis and store results."""
    
    def __init__(self, db_connection_string: str):
        """Initialize processor."""
        self.conn = psycopg2.connect(db_connection_string)
        self.cursor = self.conn.cursor()
        self.sentiment_analyzer = SentimentAnalyzer()
        self.toxicity_analyzer = ToxicityAnalyzer()
        logger.info("Analysis processor initialized")
    
    def __del__(self):
        """Clean up database connection."""
        if hasattr(self, 'cursor'):
            self.cursor.close()
        if hasattr(self, 'conn'):
            self.conn.close()
    
    def analyze_tweets_sentiment(self, person_id: Optional[int] = None,
                                 batch_size: int = 100):
        """Analyze sentiment of tweets."""
        # Get tweets that haven't been analyzed
        query = """
            SELECT pt.id, pt.text
            FROM politician_tweets pt
            LEFT JOIN tweet_sentiment ts ON pt.id = ts.tweet_id AND ts.model_name = 'vader'
            WHERE ts.id IS NULL
        """
        params = []
        
        if person_id:
            query += " AND pt.person_id = %s"
            params.append(person_id)
        
        query += f" LIMIT {batch_size}"
        
        self.cursor.execute(query, params)
        tweets = self.cursor.fetchall()
        
        logger.info(f"Analyzing sentiment for {len(tweets)} tweets")
        
        for tweet_id, text in tweets:
            try:
                sentiment = self.sentiment_analyzer.analyze_text(text)
                
                # Store sentiment
                self.cursor.execute(
                    """
                    INSERT INTO tweet_sentiment
                    (tweet_id, compound_score, positive_score, negative_score,
                     neutral_score, sentiment_label, confidence, emotions, model_name)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (tweet_id, model_name) DO UPDATE SET
                        compound_score = EXCLUDED.compound_score,
                        positive_score = EXCLUDED.positive_score,
                        negative_score = EXCLUDED.negative_score,
                        neutral_score = EXCLUDED.neutral_score,
                        sentiment_label = EXCLUDED.sentiment_label,
                        confidence = EXCLUDED.confidence,
                        emotions = EXCLUDED.emotions,
                        analyzed_at = NOW()
                    """,
                    (tweet_id, sentiment['compound_score'],
                     sentiment['positive_score'], sentiment['negative_score'],
                     sentiment['neutral_score'], sentiment['sentiment_label'],
                     sentiment['confidence'], Json(sentiment['emotions']), 'vader')
                )
            except Exception as e:
                logger.error(f"Error analyzing tweet {tweet_id}: {e}")
        
        self.conn.commit()
        logger.info(f"Sentiment analysis complete for {len(tweets)} tweets")
    
    def analyze_replies_sentiment(self, person_id: Optional[int] = None,
                                  batch_size: int = 100):
        """Analyze sentiment of replies."""
        query = """
            SELECT tr.id, tr.reply_text
            FROM tweet_replies tr
            JOIN politician_tweets pt ON tr.original_tweet_id = pt.id
            LEFT JOIN reply_sentiment rs ON tr.id = rs.reply_id AND rs.model_name = 'vader'
            WHERE rs.id IS NULL
        """
        params = []
        
        if person_id:
            query += " AND pt.person_id = %s"
            params.append(person_id)
        
        query += f" LIMIT {batch_size}"
        
        self.cursor.execute(query, params)
        replies = self.cursor.fetchall()
        
        logger.info(f"Analyzing sentiment for {len(replies)} replies")
        
        for reply_id, text in replies:
            try:
                sentiment = self.sentiment_analyzer.analyze_text(text)
                
                # Store sentiment
                self.cursor.execute(
                    """
                    INSERT INTO reply_sentiment
                    (reply_id, compound_score, positive_score, negative_score,
                     neutral_score, sentiment_label, confidence, emotions, model_name)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (reply_id, model_name) DO UPDATE SET
                        compound_score = EXCLUDED.compound_score,
                        positive_score = EXCLUDED.positive_score,
                        negative_score = EXCLUDED.negative_score,
                        neutral_score = EXCLUDED.neutral_score,
                        sentiment_label = EXCLUDED.sentiment_label,
                        confidence = EXCLUDED.confidence,
                        emotions = EXCLUDED.emotions,
                        analyzed_at = NOW()
                    """,
                    (reply_id, sentiment['compound_score'],
                     sentiment['positive_score'], sentiment['negative_score'],
                     sentiment['neutral_score'], sentiment['sentiment_label'],
                     sentiment['confidence'], Json(sentiment['emotions']), 'vader')
                )
            except Exception as e:
                logger.error(f"Error analyzing reply {reply_id}: {e}")
        
        self.conn.commit()
        logger.info(f"Sentiment analysis complete for {len(replies)} replies")
    
    def analyze_tweets_toxicity(self, person_id: Optional[int] = None,
                                batch_size: int = 100):
        """Analyze toxicity of tweets."""
        query = """
            SELECT pt.id, pt.text
            FROM politician_tweets pt
            LEFT JOIN tweet_toxicity tt ON pt.id = tt.tweet_id AND tt.model_name = 'detoxify'
            WHERE tt.id IS NULL
        """
        params = []
        
        if person_id:
            query += " AND pt.person_id = %s"
            params.append(person_id)
        
        query += f" LIMIT {batch_size}"
        
        self.cursor.execute(query, params)
        tweets = self.cursor.fetchall()
        
        logger.info(f"Analyzing toxicity for {len(tweets)} tweets")
        
        for tweet_id, text in tweets:
            try:
                toxicity = self.toxicity_analyzer.analyze_text(text)
                
                # Store toxicity
                self.cursor.execute(
                    """
                    INSERT INTO tweet_toxicity
                    (tweet_id, toxicity_score, severe_toxicity_score,
                     identity_attack_score, insult_score, profanity_score,
                     threat_score, is_toxic, toxicity_level, model_name)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (tweet_id, model_name) DO UPDATE SET
                        toxicity_score = EXCLUDED.toxicity_score,
                        severe_toxicity_score = EXCLUDED.severe_toxicity_score,
                        identity_attack_score = EXCLUDED.identity_attack_score,
                        insult_score = EXCLUDED.insult_score,
                        profanity_score = EXCLUDED.profanity_score,
                        threat_score = EXCLUDED.threat_score,
                        is_toxic = EXCLUDED.is_toxic,
                        toxicity_level = EXCLUDED.toxicity_level,
                        analyzed_at = NOW()
                    """,
                    (tweet_id, toxicity['toxicity_score'],
                     toxicity['severe_toxicity_score'],
                     toxicity['identity_attack_score'],
                     toxicity['insult_score'],
                     toxicity['profanity_score'],
                     toxicity['threat_score'],
                     toxicity['is_toxic'],
                     toxicity['toxicity_level'],
                     'detoxify')
                )
            except Exception as e:
                logger.error(f"Error analyzing tweet {tweet_id}: {e}")
        
        self.conn.commit()
        logger.info(f"Toxicity analysis complete for {len(tweets)} tweets")
    
    def analyze_replies_toxicity(self, person_id: Optional[int] = None,
                                 batch_size: int = 100):
        """Analyze toxicity of replies (hate speech detection)."""
        query = """
            SELECT tr.id, tr.reply_text
            FROM tweet_replies tr
            JOIN politician_tweets pt ON tr.original_tweet_id = pt.id
            LEFT JOIN reply_toxicity rt ON tr.id = rt.reply_id AND rt.model_name = 'detoxify'
            WHERE rt.id IS NULL
        """
        params = []
        
        if person_id:
            query += " AND pt.person_id = %s"
            params.append(person_id)
        
        query += f" LIMIT {batch_size}"
        
        self.cursor.execute(query, params)
        replies = self.cursor.fetchall()
        
        logger.info(f"Analyzing toxicity for {len(replies)} replies")
        
        for reply_id, text in replies:
            try:
                toxicity = self.toxicity_analyzer.analyze_text(text)
                
                # Store toxicity
                self.cursor.execute(
                    """
                    INSERT INTO reply_toxicity
                    (reply_id, toxicity_score, severe_toxicity_score,
                     identity_attack_score, insult_score, profanity_score,
                     threat_score, is_toxic, is_hate_speech, toxicity_level, model_name)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (reply_id, model_name) DO UPDATE SET
                        toxicity_score = EXCLUDED.toxicity_score,
                        severe_toxicity_score = EXCLUDED.severe_toxicity_score,
                        identity_attack_score = EXCLUDED.identity_attack_score,
                        insult_score = EXCLUDED.insult_score,
                        profanity_score = EXCLUDED.profanity_score,
                        threat_score = EXCLUDED.threat_score,
                        is_toxic = EXCLUDED.is_toxic,
                        is_hate_speech = EXCLUDED.is_hate_speech,
                        toxicity_level = EXCLUDED.toxicity_level,
                        analyzed_at = NOW()
                    """,
                    (reply_id, toxicity['toxicity_score'],
                     toxicity['severe_toxicity_score'],
                     toxicity['identity_attack_score'],
                     toxicity['insult_score'],
                     toxicity['profanity_score'],
                     toxicity['threat_score'],
                     toxicity['is_toxic'],
                     toxicity['is_hate_speech'],
                     toxicity['toxicity_level'],
                     'detoxify')
                )
            except Exception as e:
                logger.error(f"Error analyzing reply {reply_id}: {e}")
        
        self.conn.commit()
        logger.info(f"Toxicity analysis complete for {len(replies)} replies")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Analyze tweets and replies')
    parser.add_argument('--person-id', type=int, help='Analyze tweets for specific person')
    parser.add_argument('--analyze-sentiment', action='store_true', help='Analyze sentiment')
    parser.add_argument('--analyze-toxicity', action='store_true', help='Analyze toxicity')
    parser.add_argument('--analyze-all', action='store_true', help='Analyze sentiment and toxicity')
    parser.add_argument('--batch-size', type=int, default=100, help='Batch size for processing')
    parser.add_argument('--db-url', type=str, help='Database connection URL')
    
    args = parser.parse_args()
    
    # Get database URL
    db_url = args.db_url or os.getenv('DATABASE_URL')
    if not db_url:
        logger.error("Database URL is required (--db-url or DATABASE_URL env var)")
        sys.exit(1)
    
    # Initialize processor
    processor = TweetAnalysisProcessor(db_url)
    
    # Run analyses
    if args.analyze_all or args.analyze_sentiment:
        logger.info("Running sentiment analysis...")
        processor.analyze_tweets_sentiment(args.person_id, args.batch_size)
        processor.analyze_replies_sentiment(args.person_id, args.batch_size)
    
    if args.analyze_all or args.analyze_toxicity:
        logger.info("Running toxicity analysis...")
        processor.analyze_tweets_toxicity(args.person_id, args.batch_size)
        processor.analyze_replies_toxicity(args.person_id, args.batch_size)
    
    logger.info("Analysis complete")


if __name__ == '__main__':
    main()
