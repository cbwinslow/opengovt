"""
Embeddings module for generating vector representations of bills and speeches.

This module uses sentence transformers and other embedding models to create
vector representations of legislative text for similarity search and analysis.
"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import logging

# Optional imports - gracefully handle if not installed
try:
    from sentence_transformers import SentenceTransformer
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False
    SentenceTransformer = None

try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

logger = logging.getLogger(__name__)


@dataclass
class BillEmbeddings:
    """
    Represents embeddings for a bill's text.
    """
    bill_id: int
    model_name: str
    embedding_vector: np.ndarray
    text_hash: Optional[str] = None
    created_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (for JSON serialization)."""
        return {
            'bill_id': self.bill_id,
            'model_name': self.model_name,
            'embedding_vector': self.embedding_vector.tolist(),
            'text_hash': self.text_hash,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'metadata': self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BillEmbeddings':
        """Create from dictionary."""
        return cls(
            bill_id=data['bill_id'],
            model_name=data['model_name'],
            embedding_vector=np.array(data['embedding_vector']),
            text_hash=data.get('text_hash'),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else None,
            metadata=data.get('metadata', {}),
        )


@dataclass
class SpeechEmbeddings:
    """
    Represents embeddings for a speech or statement by a politician.
    """
    person_id: int
    speech_id: Optional[str] = None
    model_name: Optional[str] = None
    embedding_vector: Optional[np.ndarray] = None
    text_hash: Optional[str] = None
    created_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'person_id': self.person_id,
            'speech_id': self.speech_id,
            'model_name': self.model_name,
            'embedding_vector': self.embedding_vector.tolist() if self.embedding_vector is not None else None,
            'text_hash': self.text_hash,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'metadata': self.metadata,
        }


class EmbeddingsGenerator:
    """
    Generator for creating embeddings from text using various models.
    """
    
    DEFAULT_MODEL = 'all-MiniLM-L6-v2'  # Fast and efficient
    LEGAL_MODEL = 'nlpaueb/legal-bert-base-uncased'  # Specialized for legal text
    
    def __init__(self, model_name: str = None, device: str = None):
        """
        Initialize embeddings generator.
        
        Args:
            model_name: Name of the sentence transformer model to use
            device: Device to run on ('cuda', 'cpu', or None for auto-detect)
        """
        if not HAS_SENTENCE_TRANSFORMERS:
            raise ImportError(
                "sentence-transformers not installed. "
                "Install with: pip install sentence-transformers"
            )
        
        self.model_name = model_name or self.DEFAULT_MODEL
        
        # Auto-detect device if not specified
        if device is None:
            if HAS_TORCH and torch.cuda.is_available():
                device = 'cuda'
            else:
                device = 'cpu'
        
        self.device = device
        logger.info(f"Loading embedding model: {self.model_name} on {self.device}")
        
        try:
            self.model = SentenceTransformer(self.model_name, device=self.device)
        except Exception as e:
            logger.error(f"Failed to load model {self.model_name}: {e}")
            logger.info(f"Falling back to default model: {self.DEFAULT_MODEL}")
            self.model_name = self.DEFAULT_MODEL
            self.model = SentenceTransformer(self.model_name, device=self.device)
    
    def encode(self, texts: List[str], batch_size: int = 32, show_progress: bool = False) -> np.ndarray:
        """
        Encode texts into embeddings.
        
        Args:
            texts: List of texts to encode
            batch_size: Batch size for encoding
            show_progress: Whether to show progress bar
            
        Returns:
            Array of embeddings with shape (len(texts), embedding_dim)
        """
        if not texts:
            return np.array([])
        
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=show_progress,
            convert_to_numpy=True,
        )
        
        return embeddings
    
    def encode_bill(self, bill_text: str, bill_id: int, metadata: Dict[str, Any] = None) -> BillEmbeddings:
        """
        Encode a bill's text into embeddings.
        
        Args:
            bill_text: Full text of the bill
            bill_id: ID of the bill
            metadata: Additional metadata to store
            
        Returns:
            BillEmbeddings object
        """
        # Truncate very long texts (models typically have max length limits)
        max_length = 5000  # characters
        if len(bill_text) > max_length:
            logger.warning(f"Bill {bill_id} text truncated from {len(bill_text)} to {max_length} chars")
            bill_text = bill_text[:max_length]
        
        embedding = self.encode([bill_text])[0]
        
        return BillEmbeddings(
            bill_id=bill_id,
            model_name=self.model_name,
            embedding_vector=embedding,
            text_hash=str(hash(bill_text)),
            created_at=datetime.utcnow(),
            metadata=metadata or {},
        )
    
    def encode_bills_batch(self, bills: List[Tuple[int, str]], batch_size: int = 8) -> List[BillEmbeddings]:
        """
        Encode multiple bills in batch.
        
        Args:
            bills: List of (bill_id, bill_text) tuples
            batch_size: Batch size for encoding
            
        Returns:
            List of BillEmbeddings objects
        """
        texts = [text[:5000] for _, text in bills]  # Truncate long texts
        embeddings = self.encode(texts, batch_size=batch_size, show_progress=True)
        
        results = []
        for (bill_id, text), embedding in zip(bills, embeddings):
            results.append(BillEmbeddings(
                bill_id=bill_id,
                model_name=self.model_name,
                embedding_vector=embedding,
                text_hash=str(hash(text)),
                created_at=datetime.utcnow(),
            ))
        
        return results
    
    def compute_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Compute cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Cosine similarity score (0 to 1)
        """
        # Normalize vectors
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        # Cosine similarity
        similarity = np.dot(embedding1, embedding2) / (norm1 * norm2)
        
        return float(similarity)
    
    def find_similar_bills(
        self,
        query_embedding: np.ndarray,
        bill_embeddings: List[BillEmbeddings],
        top_k: int = 10,
    ) -> List[Tuple[int, float]]:
        """
        Find bills most similar to a query embedding.
        
        Args:
            query_embedding: Query embedding vector
            bill_embeddings: List of bill embeddings to search
            top_k: Number of top results to return
            
        Returns:
            List of (bill_id, similarity_score) tuples, sorted by similarity
        """
        similarities = []
        
        for bill_emb in bill_embeddings:
            similarity = self.compute_similarity(query_embedding, bill_emb.embedding_vector)
            similarities.append((bill_emb.bill_id, similarity))
        
        # Sort by similarity (descending) and return top k
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]


def create_embeddings(
    texts: List[str],
    model_name: str = None,
    batch_size: int = 32,
) -> np.ndarray:
    """
    Convenience function to create embeddings from texts.
    
    Args:
        texts: List of texts to encode
        model_name: Name of model to use (default: all-MiniLM-L6-v2)
        batch_size: Batch size for encoding
        
    Returns:
        Array of embeddings
    """
    generator = EmbeddingsGenerator(model_name=model_name)
    return generator.encode(texts, batch_size=batch_size)


def compute_bill_similarity_matrix(bill_embeddings: List[BillEmbeddings]) -> np.ndarray:
    """
    Compute pairwise similarity matrix for all bills.
    
    Args:
        bill_embeddings: List of bill embeddings
        
    Returns:
        Similarity matrix of shape (n_bills, n_bills)
    """
    n = len(bill_embeddings)
    similarity_matrix = np.zeros((n, n))
    
    generator = EmbeddingsGenerator()
    
    for i in range(n):
        for j in range(i, n):
            sim = generator.compute_similarity(
                bill_embeddings[i].embedding_vector,
                bill_embeddings[j].embedding_vector,
            )
            similarity_matrix[i, j] = sim
            similarity_matrix[j, i] = sim  # Symmetric
    
    return similarity_matrix


# Example usage and documentation
EXAMPLE_USAGE = """
# Example: Creating embeddings for bills

from analysis.embeddings import EmbeddingsGenerator, create_embeddings

# Initialize generator
generator = EmbeddingsGenerator(model_name='all-MiniLM-L6-v2')

# Encode a single bill
bill_text = "A bill to provide healthcare..."
bill_embedding = generator.encode_bill(bill_text, bill_id=123)

# Encode multiple bills in batch
bills = [(1, "Bill text 1..."), (2, "Bill text 2..."), (3, "Bill text 3...")]
embeddings = generator.encode_bills_batch(bills)

# Find similar bills
query_embedding = bill_embedding.embedding_vector
similar_bills = generator.find_similar_bills(query_embedding, embeddings, top_k=5)

for bill_id, similarity in similar_bills:
    print(f"Bill {bill_id}: similarity={similarity:.3f}")

# Quick embeddings without class
texts = ["Text 1", "Text 2", "Text 3"]
embeddings_array = create_embeddings(texts)
"""
