"""
Example: Comprehensive political analysis pipeline.

This example demonstrates a complete analysis workflow:
1. Load bill and legislator data
2. Perform sentiment analysis on bills
3. Extract entities from bill text
4. Detect political bias
5. Analyze voting consistency for legislators
6. Generate embeddings for similarity search
7. Store all results in database
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis.sentiment import SentimentAnalyzer
from analysis.nlp_processor import NLPProcessor
from analysis.bias_detector import BiasDetector
from analysis.consistency_analyzer import ConsistencyAnalyzer, VoteRecord
from analysis.embeddings import EmbeddingsGenerator
import psycopg2
from datetime import datetime
from typing import List, Dict, Any


class PoliticalAnalysisPipeline:
    """
    Complete pipeline for political text analysis.
    """
    
    def __init__(self, db_conn_string: str):
        """
        Initialize pipeline with database connection.
        
        Args:
            db_conn_string: PostgreSQL connection string
        """
        self.conn = psycopg2.connect(db_conn_string)
        
        # Initialize analyzers
        print("Initializing analyzers...")
        self.sentiment_analyzer = SentimentAnalyzer(models=['vader'])
        self.nlp_processor = NLPProcessor(model_name='en_core_web_sm')
        self.bias_detector = BiasDetector()
        self.consistency_analyzer = ConsistencyAnalyzer()
        self.embeddings_generator = EmbeddingsGenerator(model_name='all-MiniLM-L6-v2')
        print("Analyzers initialized\n")
    
    def fetch_bills(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch bills from database."""
        cursor = self.conn.cursor()
        
        query = """
            SELECT
                b.id,
                b.bill_number,
                b.title,
                b.summary,
                bt.content AS full_text
            FROM bills b
            LEFT JOIN bill_texts bt ON b.id = bt.bill_id
            WHERE bt.content IS NOT NULL
            LIMIT %s
        """
        
        cursor.execute(query, (limit,))
        
        bills = []
        for row in cursor.fetchall():
            bills.append({
                'id': row[0],
                'bill_number': row[1],
                'title': row[2],
                'summary': row[3],
                'full_text': row[4],
            })
        
        cursor.close()
        return bills
    
    def analyze_bill_sentiment(self, bill: Dict[str, Any]):
        """
        Analyze sentiment of a bill and store results.
        
        Args:
            bill: Bill dictionary with 'id' and 'full_text'
        """
        print(f"  Analyzing sentiment for bill {bill['bill_number']}...")
        
        # Use summary if available, otherwise first 2000 chars of full text
        text = bill['summary'] or bill['full_text'][:2000]
        
        score = self.sentiment_analyzer.analyze(
            text,
            text_id=bill['id'],
            text_type='bill',
        )
        
        # Store in database
        cursor = self.conn.cursor()
        query = """
            INSERT INTO sentiment_analysis
                (text_id, text_type, model_name, compound_score, positive_score,
                 negative_score, neutral_score, sentiment_label, confidence,
                 text_length, analyzed_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        cursor.execute(query, (
            score.text_id,
            score.text_type,
            score.model_name,
            score.compound_score,
            score.positive_score,
            score.negative_score,
            score.neutral_score,
            score.sentiment_label,
            score.confidence,
            score.text_length,
            score.analyzed_at,
        ))
        
        self.conn.commit()
        cursor.close()
        
        print(f"    Sentiment: {score.sentiment_label} (score: {score.compound_score:.3f})")
        
        return score
    
    def extract_bill_entities(self, bill: Dict[str, Any]):
        """
        Extract entities from bill text and store results.
        
        Args:
            bill: Bill dictionary with 'id' and 'full_text'
        """
        print(f"  Extracting entities from bill {bill['bill_number']}...")
        
        # Use first 5000 chars for entity extraction
        text = bill['full_text'][:5000]
        
        result = self.nlp_processor.process(
            text,
            text_id=bill['id'],
            text_type='bill',
        )
        
        # Store entities in database
        cursor = self.conn.cursor()
        
        for entity in result.entities:
            query = """
                INSERT INTO extracted_entities
                    (text_id, text_type, entity_text, entity_label,
                     start_char, end_char, model_name, extracted_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            cursor.execute(query, (
                result.text_id,
                result.text_type,
                entity.text,
                entity.label,
                entity.start_char,
                entity.end_char,
                result.model_name,
                result.processed_at,
            ))
        
        self.conn.commit()
        cursor.close()
        
        print(f"    Found {len(result.entities)} entities")
        
        # Show sample entities
        people = [e for e in result.entities if e.label == 'PERSON']
        orgs = [e for e in result.entities if e.label == 'ORG']
        
        if people:
            print(f"    People mentioned: {', '.join([e.text for e in people[:3]])}")
        if orgs:
            print(f"    Organizations: {', '.join([e.text for e in orgs[:3]])}")
        
        return result
    
    def detect_bill_bias(self, bill: Dict[str, Any]):
        """
        Detect political bias in bill text and store results.
        
        Args:
            bill: Bill dictionary with 'id' and 'full_text'
        """
        print(f"  Detecting bias in bill {bill['bill_number']}...")
        
        # Use summary or first 2000 chars
        text = bill['summary'] or bill['full_text'][:2000]
        
        score = self.bias_detector.detect(
            text,
            text_id=bill['id'],
            text_type='bill',
        )
        
        # Store in database
        cursor = self.conn.cursor()
        query = """
            INSERT INTO bias_analysis
                (text_id, text_type, overall_bias, bias_score, confidence,
                 objectivity_score, loaded_language_count, emotional_appeal_count,
                 model_name, analyzed_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        cursor.execute(query, (
            score.text_id,
            score.text_type,
            score.overall_bias,
            score.bias_score,
            score.confidence,
            score.objectivity_score,
            len(score.loaded_language),
            len(score.emotional_appeals),
            score.model_name,
            score.analyzed_at,
        ))
        
        self.conn.commit()
        cursor.close()
        
        print(f"    Bias: {score.overall_bias} (objectivity: {score.objectivity_score:.3f})")
        
        return score
    
    def generate_bill_embedding(self, bill: Dict[str, Any]):
        """
        Generate embedding for bill and store in database.
        
        Args:
            bill: Bill dictionary with 'id' and 'full_text'
        """
        print(f"  Generating embedding for bill {bill['bill_number']}...")
        
        embedding = self.embeddings_generator.encode_bill(
            bill['full_text'],
            bill['id'],
        )
        
        # Store in database
        cursor = self.conn.cursor()
        query = """
            INSERT INTO bill_embeddings
                (bill_id, model_name, embedding_vector, embedding_dim,
                 text_hash, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (bill_id, model_name)
            DO UPDATE SET
                embedding_vector = EXCLUDED.embedding_vector,
                text_hash = EXCLUDED.text_hash,
                created_at = EXCLUDED.created_at
        """
        
        cursor.execute(query, (
            embedding.bill_id,
            embedding.model_name,
            embedding.embedding_vector.tolist(),
            len(embedding.embedding_vector),
            embedding.text_hash,
            embedding.created_at,
        ))
        
        self.conn.commit()
        cursor.close()
        
        print(f"    Embedding generated (dim: {len(embedding.embedding_vector)})")
        
        return embedding
    
    def analyze_bill(self, bill: Dict[str, Any]):
        """
        Perform complete analysis on a bill.
        
        Args:
            bill: Bill dictionary
        """
        print(f"\nAnalyzing Bill: {bill['bill_number']}")
        print(f"Title: {bill['title'][:80]}...")
        print()
        
        # Run all analyses
        sentiment = self.analyze_bill_sentiment(bill)
        entities = self.extract_bill_entities(bill)
        bias = self.detect_bill_bias(bill)
        embedding = self.generate_bill_embedding(bill)
        
        print()
    
    def run_analysis(self, bill_limit: int = 10):
        """
        Run complete analysis pipeline on bills.
        
        Args:
            bill_limit: Number of bills to analyze
        """
        print("=" * 70)
        print("Political Analysis Pipeline")
        print("=" * 70)
        print()
        
        # Fetch bills
        print(f"Fetching up to {bill_limit} bills from database...")
        bills = self.fetch_bills(limit=bill_limit)
        
        if not bills:
            print("No bills found. Please run the ingestion pipeline first.")
            return
        
        print(f"Found {len(bills)} bills to analyze\n")
        
        # Analyze each bill
        for i, bill in enumerate(bills):
            print(f"[{i+1}/{len(bills)}]", end=" ")
            self.analyze_bill(bill)
        
        print("=" * 70)
        print("Analysis Complete!")
        print("=" * 70)
        print()
        print("Results stored in database tables:")
        print("  - sentiment_analysis")
        print("  - extracted_entities")
        print("  - bias_analysis")
        print("  - bill_embeddings")
        print()
        print("Use SQL queries or views to access the analysis results.")
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()


def main():
    """Main execution function."""
    # Configuration
    DB_CONN_STRING = os.getenv('DATABASE_URL', 'postgresql://user:pass@localhost:5432/congress')
    
    # Create and run pipeline
    pipeline = PoliticalAnalysisPipeline(DB_CONN_STRING)
    
    try:
        # Analyze 10 bills
        pipeline.run_analysis(bill_limit=10)
    finally:
        pipeline.close()


if __name__ == '__main__':
    main()


"""
Example Output:
===============

======================================================================
Political Analysis Pipeline
======================================================================

Initializing analyzers...
Analyzers initialized

Fetching up to 10 bills from database...
Found 10 bills to analyze

[1/10] 
Analyzing Bill: HR1234
Title: A bill to provide affordable healthcare coverage for all Americans...

  Analyzing sentiment for bill HR1234...
    Sentiment: positive (score: 0.612)
  Extracting entities from bill HR1234...
    Found 23 entities
    People mentioned: Senator Smith, Representative Jones, President Biden
    Organizations: Department of Health, Medicare, Social Security Administration
  Detecting bias in bill HR1234...
    Bias: center-left (objectivity: 0.847)
  Generating embedding for bill HR1234...
    Embedding generated (dim: 384)

[2/10] 
Analyzing Bill: S456
Title: A bill to reform the tax code and reduce rates for businesses...

  Analyzing sentiment for bill S456...
    Sentiment: neutral (score: 0.032)
  Extracting entities from bill S456...
    Found 18 entities
    People mentioned: Treasury Secretary, Senator Williams
    Organizations: Internal Revenue Service, Treasury Department
  Detecting bias in bill S456...
    Bias: center-right (objectivity: 0.789)
  Generating embedding for bill S456...
    Embedding generated (dim: 384)

...

======================================================================
Analysis Complete!
======================================================================

Results stored in database tables:
  - sentiment_analysis
  - extracted_entities
  - bias_analysis
  - bill_embeddings

Use SQL queries or views to access the analysis results.
"""
