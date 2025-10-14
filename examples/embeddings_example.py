"""
Example: Using embeddings to find similar bills.

This example demonstrates how to:
1. Load bill data from the database
2. Generate embeddings for bill text
3. Find similar bills using cosine similarity
4. Store results back to the database
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis.embeddings import EmbeddingsGenerator, BillEmbeddings
import psycopg2
from typing import List, Dict, Any
import numpy as np


def connect_to_db(conn_string: str):
    """Connect to PostgreSQL database."""
    return psycopg2.connect(conn_string)


def fetch_bills(conn, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Fetch bills from database.
    
    Args:
        conn: Database connection
        limit: Maximum number of bills to fetch
        
    Returns:
        List of bill dictionaries
    """
    cursor = conn.cursor()
    
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


def generate_bill_embeddings(bills: List[Dict[str, Any]]) -> List[BillEmbeddings]:
    """
    Generate embeddings for all bills.
    
    Args:
        bills: List of bill dictionaries with 'id' and 'full_text'
        
    Returns:
        List of BillEmbeddings objects
    """
    print(f"Generating embeddings for {len(bills)} bills...")
    
    # Initialize embeddings generator
    generator = EmbeddingsGenerator(model_name='all-MiniLM-L6-v2')
    
    # Prepare bills for batch processing
    bill_data = [(b['id'], b['full_text']) for b in bills]
    
    # Generate embeddings in batch
    embeddings = generator.encode_bills_batch(bill_data, batch_size=8)
    
    print(f"Generated {len(embeddings)} embeddings")
    return embeddings


def store_embeddings(conn, embeddings: List[BillEmbeddings]):
    """
    Store embeddings in the database.
    
    Args:
        conn: Database connection
        embeddings: List of BillEmbeddings objects
    """
    cursor = conn.cursor()
    
    print(f"Storing {len(embeddings)} embeddings in database...")
    
    for emb in embeddings:
        # Convert numpy array to list for PostgreSQL
        vector_list = emb.embedding_vector.tolist()
        
        query = """
            INSERT INTO bill_embeddings
                (bill_id, model_name, embedding_vector, embedding_dim, text_hash, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (bill_id, model_name)
            DO UPDATE SET
                embedding_vector = EXCLUDED.embedding_vector,
                text_hash = EXCLUDED.text_hash,
                created_at = EXCLUDED.created_at
        """
        
        cursor.execute(query, (
            emb.bill_id,
            emb.model_name,
            vector_list,
            len(vector_list),
            emb.text_hash,
            emb.created_at,
        ))
    
    conn.commit()
    cursor.close()
    print("Embeddings stored successfully")


def find_similar_bills(
    generator: EmbeddingsGenerator,
    query_bill: Dict[str, Any],
    all_embeddings: List[BillEmbeddings],
    top_k: int = 5,
) -> List[tuple]:
    """
    Find bills most similar to a query bill.
    
    Args:
        generator: EmbeddingsGenerator instance
        query_bill: Dictionary with bill data including 'id' and 'full_text'
        all_embeddings: List of all bill embeddings
        top_k: Number of similar bills to return
        
    Returns:
        List of (bill_id, similarity_score) tuples
    """
    # Generate embedding for query bill
    query_embedding = generator.encode_bill(
        query_bill['full_text'],
        query_bill['id'],
    )
    
    # Find similar bills
    similar = generator.find_similar_bills(
        query_embedding.embedding_vector,
        all_embeddings,
        top_k=top_k + 1,  # +1 to exclude self
    )
    
    # Remove self from results
    similar = [(bid, score) for bid, score in similar if bid != query_bill['id']]
    
    return similar[:top_k]


def store_similarity_scores(conn, bill_id: int, similar_bills: List[tuple], model_name: str):
    """
    Store bill similarity scores in the database.
    
    Args:
        conn: Database connection
        bill_id: Query bill ID
        similar_bills: List of (bill_id, similarity_score) tuples
        model_name: Name of the embedding model used
    """
    cursor = conn.cursor()
    
    for similar_id, score in similar_bills:
        # Ensure bill_id_1 < bill_id_2 for uniqueness constraint
        id1, id2 = (bill_id, similar_id) if bill_id < similar_id else (similar_id, bill_id)
        
        query = """
            INSERT INTO bill_similarities
                (bill_id_1, bill_id_2, similarity_score, model_name)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (bill_id_1, bill_id_2, model_name)
            DO UPDATE SET
                similarity_score = EXCLUDED.similarity_score,
                calculated_at = now()
        """
        
        cursor.execute(query, (id1, id2, score, model_name))
    
    conn.commit()
    cursor.close()


def main():
    """Main execution function."""
    # Configuration
    DB_CONN_STRING = os.getenv('DATABASE_URL', 'postgresql://user:pass@localhost:5432/congress')
    
    print("=== Bill Similarity Analysis with Embeddings ===\n")
    
    # Connect to database
    print("Connecting to database...")
    conn = connect_to_db(DB_CONN_STRING)
    
    # Fetch bills
    print("Fetching bills from database...")
    bills = fetch_bills(conn, limit=100)
    
    if not bills:
        print("No bills found in database. Please run the ingestion pipeline first.")
        return
    
    print(f"Fetched {len(bills)} bills\n")
    
    # Generate embeddings
    embeddings = generate_bill_embeddings(bills)
    
    # Store embeddings
    store_embeddings(conn, embeddings)
    
    # Initialize generator for similarity search
    generator = EmbeddingsGenerator(model_name='all-MiniLM-L6-v2')
    
    # Find similar bills for each bill and store results
    print("\nFinding similar bills...")
    
    for i, bill in enumerate(bills[:10]):  # Process first 10 bills as examples
        print(f"\nBill {i+1}/{min(10, len(bills))}: {bill['bill_number']}")
        print(f"Title: {bill['title'][:80]}...")
        
        similar = find_similar_bills(generator, bill, embeddings, top_k=5)
        
        print("Most similar bills:")
        for similar_id, score in similar:
            similar_bill = next((b for b in bills if b['id'] == similar_id), None)
            if similar_bill:
                print(f"  {similar_bill['bill_number']} (similarity: {score:.3f})")
                print(f"    {similar_bill['title'][:60]}...")
        
        # Store similarity scores
        store_similarity_scores(conn, bill['id'], similar, 'all-MiniLM-L6-v2')
    
    # Close connection
    conn.close()
    
    print("\n=== Analysis Complete ===")
    print("Embeddings and similarity scores have been stored in the database.")
    print("Query the 'bill_similarities' table or use the 'top_similar_bills' view to access results.")


if __name__ == '__main__':
    main()


"""
Example Output:
===============

=== Bill Similarity Analysis with Embeddings ===

Connecting to database...
Fetching bills from database...
Fetched 100 bills

Generating embeddings for 100 bills...
Generated 100 embeddings
Storing 100 embeddings in database...
Embeddings stored successfully

Finding similar bills...

Bill 1/10: HR1234
Title: A bill to provide affordable healthcare coverage for all Americans...
Most similar bills:
  HR2345 (similarity: 0.892)
    A bill to expand Medicare and provide universal healthcare coverage...
  S456 (similarity: 0.847)
    A bill to reform the healthcare system and reduce costs...
  HR789 (similarity: 0.823)
    A bill to improve access to healthcare in rural areas...

Bill 2/10: S789
Title: A bill to invest in renewable energy infrastructure...
Most similar bills:
  HR3456 (similarity: 0.901)
    A bill to accelerate the transition to clean energy...
  S234 (similarity: 0.878)
    A bill to combat climate change through green infrastructure...

...

=== Analysis Complete ===
Embeddings and similarity scores have been stored in the database.
Query the 'bill_similarities' table or use the 'top_similar_bills' view to access results.
"""
