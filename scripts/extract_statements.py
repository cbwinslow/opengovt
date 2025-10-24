#!/usr/bin/env python3
"""
Political Statement Extraction Script

Extracts political statements, actions, and declarations from tweets, bills, and votes
at multiple granularity levels for analysis and display.

Example extractions:
- Full: "Senator X voted to increase taxes 5 percent in VA last year"
- Medium: "Senator X voted to increase taxes 5 percent"
- Short: "Senator X voted to increase taxes"

Usage:
    export DATABASE_URL="postgresql://username:password@host:port/database"
    python extract_statements.py --source tweets --person-id 123
    python extract_statements.py --source bills --extract-all

Note: DATABASE_URL must be set as an environment variable for security.
"""

import os
import sys
import argparse
import logging
import re
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

import psycopg2
from psycopg2.extras import Json

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class StatementExtractor:
    """Extract political statements at multiple granularity levels."""
    
    # Common political action verbs
    ACTION_VERBS = [
        'voted', 'vote', 'voted for', 'voted against',
        'proposed', 'introduced', 'sponsored', 'cosponsored',
        'supported', 'opposed', 'backed', 'endorsed',
        'announced', 'declared', 'stated', 'said',
        'passed', 'enacted', 'signed',
        'blocked', 'vetoed', 'rejected',
        'increased', 'decreased', 'raised', 'lowered', 'cut',
    ]
    
    # Political subjects
    SUBJECTS = [
        'taxes', 'tax', 'healthcare', 'health care', 'insurance',
        'immigration', 'border', 'climate', 'environment',
        'education', 'schools', 'gun control', 'guns', 'second amendment',
        'abortion', 'reproductive rights', 'infrastructure',
        'defense', 'military', 'veterans', 'social security',
        'medicare', 'medicaid', 'minimum wage', 'jobs', 'economy',
        'budget', 'spending', 'debt', 'deficit',
    ]
    
    # State abbreviations
    STATES = [
        'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
        'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
        'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
        'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
        'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY',
    ]
    
    def __init__(self):
        """Initialize the extractor."""
        self.magnitude_pattern = re.compile(
            r'\b(\d+(?:\.\d+)?)\s*(percent|%|dollars?|million|billion|trillion)\b',
            re.IGNORECASE
        )
        self.time_pattern = re.compile(
            r'\b(last|this|next)\s+(year|month|week|quarter)\b|\b\d{4}\b',
            re.IGNORECASE
        )
        self.location_pattern = re.compile(
            r'\bin\s+(' + '|'.join(self.STATES) + r')\b',
            re.IGNORECASE
        )
    
    def extract_from_text(self, text: str, person_name: str) -> List[Dict[str, Any]]:
        """Extract statements from text."""
        if not text or not person_name:
            return []
        
        statements = []
        text_lower = text.lower()
        
        # Look for action verbs
        for action in self.ACTION_VERBS:
            if action in text_lower:
                # Look for subjects
                for subject in self.SUBJECTS:
                    if subject in text_lower:
                        statement = self._extract_statement(
                            text, person_name, action, subject
                        )
                        if statement:
                            statements.append(statement)
        
        return statements
    
    def _extract_statement(self, text: str, person_name: str,
                          action: str, subject: str) -> Optional[Dict[str, Any]]:
        """Extract a single statement with multiple granularities."""
        try:
            # Extract magnitude (e.g., "5 percent", "$1 billion")
            magnitude = None
            mag_match = self.magnitude_pattern.search(text)
            if mag_match:
                magnitude = mag_match.group(0)
            
            # Extract timeframe
            timeframe = None
            time_match = self.time_pattern.search(text)
            if time_match:
                timeframe = time_match.group(0)
            
            # Extract location
            location = None
            loc_match = self.location_pattern.search(text)
            if loc_match:
                location = loc_match.group(1)
            
            # Determine stance (for/against/neutral)
            stance = 'for'
            if any(neg in text.lower() for neg in ['against', 'oppose', 'block', 'veto', 'reject']):
                stance = 'against'
            elif any(pos in text.lower() for pos in ['for', 'support', 'back', 'endorse', 'pass']):
                stance = 'for'
            else:
                stance = 'neutral'
            
            # Build statements at different granularity levels
            
            # Short version (person + action + subject)
            statement_short = f"{person_name} {action} {subject}"
            
            # Medium version (add magnitude if available)
            statement_medium = statement_short
            if magnitude:
                statement_medium = f"{person_name} {action} {subject} {magnitude}"
            
            # Full version (add all details)
            statement_full = statement_medium
            if location and timeframe:
                statement_full = f"{statement_medium} in {location} {timeframe}"
            elif location:
                statement_full = f"{statement_medium} in {location}"
            elif timeframe:
                statement_full = f"{statement_medium} {timeframe}"
            
            # Classify action type
            action_type = 'statement'
            if any(v in action.lower() for v in ['vote', 'voted']):
                action_type = 'vote'
            elif any(v in action.lower() for v in ['propose', 'introduce', 'sponsor']):
                action_type = 'proposal'
            elif any(v in action.lower() for v in ['announce', 'declare']):
                action_type = 'declaration'
            
            # Calculate confidence (simple heuristic)
            confidence = 0.5
            if magnitude:
                confidence += 0.2
            if timeframe:
                confidence += 0.15
            if location:
                confidence += 0.15
            
            return {
                'statement_full': statement_full,
                'statement_medium': statement_medium,
                'statement_short': statement_short,
                'action_type': action_type,
                'subject': subject,
                'stance': stance,
                'magnitude': magnitude,
                'location': location,
                'timeframe': timeframe,
                'confidence': min(confidence, 1.0),
                'extraction_method': 'rule_based',
            }
        
        except Exception as e:
            logger.error(f"Error extracting statement: {e}")
            return None
    
    def extract_from_vote(self, vote_data: Dict[str, Any],
                         person_name: str) -> List[Dict[str, Any]]:
        """Extract statements from vote records."""
        statements = []
        
        try:
            # Get bill title or description
            bill_title = vote_data.get('bill_title', '')
            vote_choice = vote_data.get('vote_choice', '').lower()
            
            # Determine stance
            stance = 'for' if vote_choice in ['yes', 'aye', 'yea'] else 'against'
            
            # Extract subject from title
            subject = 'legislation'
            for subj in self.SUBJECTS:
                if subj in bill_title.lower():
                    subject = subj
                    break
            
            # Build statements
            statement_short = f"{person_name} voted {stance} {subject}"
            statement_medium = f"{person_name} voted {stance} {subject}"
            statement_full = f"{person_name} voted {vote_choice} on {bill_title[:100]}"
            
            statements.append({
                'statement_full': statement_full,
                'statement_medium': statement_medium,
                'statement_short': statement_short,
                'action_type': 'vote',
                'subject': subject,
                'stance': stance,
                'magnitude': None,
                'location': None,
                'timeframe': None,
                'confidence': 0.9,
                'extraction_method': 'vote_record',
            })
        
        except Exception as e:
            logger.error(f"Error extracting from vote: {e}")
        
        return statements


class StatementProcessor:
    """Process and store extracted statements."""
    
    def __init__(self, db_connection_string: str):
        """Initialize processor."""
        self.conn = psycopg2.connect(db_connection_string)
        self.cursor = self.conn.cursor()
        self.extractor = StatementExtractor()
        logger.info("Statement processor initialized")
    
    def __del__(self):
        """Clean up database connection."""
        if hasattr(self, 'cursor'):
            self.cursor.close()
        if hasattr(self, 'conn'):
            self.conn.close()
    
    def extract_from_tweets(self, person_id: Optional[int] = None,
                           batch_size: int = 100):
        """Extract statements from tweets."""
        # Get tweets that haven't been processed
        query = """
            SELECT pt.id, pt.text, pt.person_id, l.name
            FROM politician_tweets pt
            JOIN legislators l ON pt.person_id = l.id
            LEFT JOIN political_statements ps ON ps.source_type = 'tweet'
                AND ps.source_id = pt.id
            WHERE ps.id IS NULL
            AND pt.is_retweet = FALSE
        """
        params = []
        
        if person_id:
            query += " AND pt.person_id = %s"
            params.append(person_id)
        
        query += f" LIMIT {batch_size}"
        
        self.cursor.execute(query, params)
        tweets = self.cursor.fetchall()
        
        logger.info(f"Extracting statements from {len(tweets)} tweets")
        
        total_extracted = 0
        for tweet_id, text, pid, person_name in tweets:
            try:
                statements = self.extractor.extract_from_text(text, person_name)
                
                for stmt in statements:
                    self._store_statement(
                        person_id=pid,
                        source_type='tweet',
                        source_id=tweet_id,
                        statement_data=stmt
                    )
                    total_extracted += 1
            
            except Exception as e:
                logger.error(f"Error processing tweet {tweet_id}: {e}")
        
        self.conn.commit()
        logger.info(f"Extracted {total_extracted} statements from tweets")
    
    def extract_from_votes(self, person_id: Optional[int] = None,
                          batch_size: int = 100):
        """Extract statements from vote records."""
        query = """
            SELECT rv.id, rv.vote_choice, v.result, b.title, rv.member_bioguide,
                   l.id, l.name
            FROM rollcall_votes rv
            JOIN votes v ON rv.vote_id = v.id
            LEFT JOIN bills b ON v.congress = b.congress
            JOIN legislators l ON rv.member_bioguide = l.bioguide
            LEFT JOIN political_statements ps ON ps.source_type = 'vote'
                AND ps.source_id = rv.id
            WHERE ps.id IS NULL
        """
        params = []
        
        if person_id:
            query += " AND l.id = %s"
            params.append(person_id)
        
        query += f" LIMIT {batch_size}"
        
        self.cursor.execute(query, params)
        votes = self.cursor.fetchall()
        
        logger.info(f"Extracting statements from {len(votes)} votes")
        
        total_extracted = 0
        for vote_id, vote_choice, result, bill_title, bioguide, pid, person_name in votes:
            try:
                vote_data = {
                    'vote_choice': vote_choice,
                    'result': result,
                    'bill_title': bill_title or '',
                }
                
                statements = self.extractor.extract_from_vote(vote_data, person_name)
                
                for stmt in statements:
                    self._store_statement(
                        person_id=pid,
                        source_type='vote',
                        source_id=vote_id,
                        statement_data=stmt
                    )
                    total_extracted += 1
            
            except Exception as e:
                logger.error(f"Error processing vote {vote_id}: {e}")
        
        self.conn.commit()
        logger.info(f"Extracted {total_extracted} statements from votes")
    
    def _store_statement(self, person_id: int, source_type: str,
                        source_id: int, statement_data: Dict[str, Any]):
        """Store an extracted statement."""
        try:
            self.cursor.execute(
                """
                INSERT INTO political_statements
                (person_id, source_type, source_id, statement_full,
                 statement_medium, statement_short, action_type, subject,
                 stance, magnitude, location, timeframe, confidence,
                 extraction_method, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (person_id, source_type, source_id,
                 statement_data['statement_full'],
                 statement_data['statement_medium'],
                 statement_data['statement_short'],
                 statement_data['action_type'],
                 statement_data['subject'],
                 statement_data['stance'],
                 statement_data.get('magnitude'),
                 statement_data.get('location'),
                 statement_data.get('timeframe'),
                 statement_data['confidence'],
                 statement_data['extraction_method'],
                 Json({}))
            )
        except Exception as e:
            logger.error(f"Error storing statement: {e}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Extract political statements')
    parser.add_argument('--source', type=str, choices=['tweets', 'votes', 'all'],
                       default='all', help='Source to extract from')
    parser.add_argument('--person-id', type=int, help='Extract for specific person')
    parser.add_argument('--batch-size', type=int, default=100, help='Batch size')
    
    args = parser.parse_args()
    
    # Get database URL from environment variable only (more secure than CLI argument)
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        logger.error("DATABASE_URL environment variable is required")
        sys.exit(1)
    
    # Initialize processor
    processor = StatementProcessor(db_url)
    
    # Extract statements
    if args.source in ['tweets', 'all']:
        logger.info("Extracting from tweets...")
        processor.extract_from_tweets(args.person_id, args.batch_size)
    
    if args.source in ['votes', 'all']:
        logger.info("Extracting from votes...")
        processor.extract_from_votes(args.person_id, args.batch_size)
    
    logger.info("Extraction complete")


if __name__ == '__main__':
    main()
