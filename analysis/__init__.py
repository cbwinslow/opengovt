"""
Analysis package for NLP, sentiment, embeddings, and other text analysis on legislative data.

This package provides modules for:
- Text preprocessing and tokenization
- Named Entity Recognition and attribution
- Sentiment analysis
- Political bias detection
- Embeddings generation and similarity
- Hate speech detection
- Consistency and honesty analysis
"""

from .embeddings import BillEmbeddings, SpeechEmbeddings, create_embeddings
from .sentiment import SentimentAnalyzer, analyze_sentiment
from .nlp_processor import NLPProcessor, extract_entities
from .bias_detector import BiasDetector, detect_political_bias
from .consistency_analyzer import ConsistencyAnalyzer, analyze_voting_consistency

__all__ = [
    'BillEmbeddings',
    'SpeechEmbeddings',
    'create_embeddings',
    'SentimentAnalyzer',
    'analyze_sentiment',
    'NLPProcessor',
    'extract_entities',
    'BiasDetector',
    'detect_political_bias',
    'ConsistencyAnalyzer',
    'analyze_voting_consistency',
]
