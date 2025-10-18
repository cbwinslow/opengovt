"""
Sentiment analysis module for political text analysis.

Performs sentiment analysis on bills, speeches, and other legislative text
using multiple models including VADER, TextBlob, and transformers-based models.
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

# Optional imports
try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer as VaderAnalyzer
    HAS_VADER = True
except ImportError:
    HAS_VADER = False
    VaderAnalyzer = None

try:
    from textblob import TextBlob
    HAS_TEXTBLOB = True
except ImportError:
    HAS_TEXTBLOB = False
    TextBlob = None

try:
    from transformers import pipeline
    HAS_TRANSFORMERS = True
except ImportError:
    HAS_TRANSFORMERS = False
    pipeline = None

logger = logging.getLogger(__name__)


@dataclass
class SentimentScore:
    """
    Represents sentiment analysis results.
    """
    text_id: Optional[int] = None  # Bill ID, speech ID, etc.
    text_type: Optional[str] = None  # 'bill', 'speech', 'statement'
    
    # Sentiment scores (-1 to 1, where -1=negative, 0=neutral, 1=positive)
    compound_score: Optional[float] = None
    positive_score: Optional[float] = None
    negative_score: Optional[float] = None
    neutral_score: Optional[float] = None
    
    # Model used
    model_name: Optional[str] = None
    
    # Classification
    sentiment_label: Optional[str] = None  # 'positive', 'negative', 'neutral'
    confidence: Optional[float] = None
    
    # Metadata
    analyzed_at: Optional[datetime] = None
    text_length: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'text_id': self.text_id,
            'text_type': self.text_type,
            'compound_score': self.compound_score,
            'positive_score': self.positive_score,
            'negative_score': self.negative_score,
            'neutral_score': self.neutral_score,
            'model_name': self.model_name,
            'sentiment_label': self.sentiment_label,
            'confidence': self.confidence,
            'analyzed_at': self.analyzed_at.isoformat() if self.analyzed_at else None,
            'text_length': self.text_length,
            'metadata': self.metadata,
        }


class SentimentAnalyzer:
    """
    Multi-model sentiment analyzer for political text.
    """
    
    def __init__(self, models: List[str] = None):
        """
        Initialize sentiment analyzer.
        
        Args:
            models: List of models to use. Options: 'vader', 'textblob', 'transformers'
                   Default: ['vader'] (fastest and works well for political text)
        """
        self.models = models or ['vader']
        self.analyzers = {}
        
        # Initialize requested models
        if 'vader' in self.models:
            if HAS_VADER:
                self.analyzers['vader'] = VaderAnalyzer()
                logger.info("Initialized VADER sentiment analyzer")
            else:
                logger.warning("VADER not available. Install with: pip install vaderSentiment")
        
        if 'textblob' in self.models:
            if HAS_TEXTBLOB:
                self.analyzers['textblob'] = True  # TextBlob doesn't need initialization
                logger.info("TextBlob sentiment analyzer available")
            else:
                logger.warning("TextBlob not available. Install with: pip install textblob")
        
        if 'transformers' in self.models:
            if HAS_TRANSFORMERS:
                try:
                    # Use a pre-trained sentiment model
                    self.analyzers['transformers'] = pipeline(
                        "sentiment-analysis",
                        model="distilbert-base-uncased-finetuned-sst-2-english",
                        device=-1,  # CPU
                    )
                    logger.info("Initialized transformers sentiment analyzer")
                except Exception as e:
                    logger.error(f"Failed to initialize transformers model: {e}")
            else:
                logger.warning("Transformers not available. Install with: pip install transformers torch")
        
        if not self.analyzers:
            logger.error("No sentiment analyzers available!")
    
    def analyze(self, text: str, text_id: int = None, text_type: str = None) -> SentimentScore:
        """
        Analyze sentiment of text using available models.
        
        Args:
            text: Text to analyze
            text_id: Optional ID for the text (bill ID, etc.)
            text_type: Optional type label ('bill', 'speech', etc.)
            
        Returns:
            SentimentScore object with results
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for sentiment analysis")
            return SentimentScore(
                text_id=text_id,
                text_type=text_type,
                sentiment_label='neutral',
                analyzed_at=datetime.utcnow(),
            )
        
        # Use VADER by default (best for political text)
        if 'vader' in self.analyzers:
            return self._analyze_vader(text, text_id, text_type)
        elif 'textblob' in self.analyzers:
            return self._analyze_textblob(text, text_id, text_type)
        elif 'transformers' in self.analyzers:
            return self._analyze_transformers(text, text_id, text_type)
        else:
            logger.error("No sentiment analyzer available")
            return SentimentScore(
                text_id=text_id,
                text_type=text_type,
                analyzed_at=datetime.utcnow(),
            )
    
    def _analyze_vader(self, text: str, text_id: int, text_type: str) -> SentimentScore:
        """Analyze using VADER."""
        vader = self.analyzers['vader']
        scores = vader.polarity_scores(text)
        
        # Determine label based on compound score
        compound = scores['compound']
        if compound >= 0.05:
            label = 'positive'
        elif compound <= -0.05:
            label = 'negative'
        else:
            label = 'neutral'
        
        return SentimentScore(
            text_id=text_id,
            text_type=text_type,
            compound_score=scores['compound'],
            positive_score=scores['pos'],
            negative_score=scores['neg'],
            neutral_score=scores['neu'],
            model_name='vader',
            sentiment_label=label,
            confidence=abs(compound),  # Use absolute compound as confidence
            analyzed_at=datetime.utcnow(),
            text_length=len(text),
        )
    
    def _analyze_textblob(self, text: str, text_id: int, text_type: str) -> SentimentScore:
        """Analyze using TextBlob."""
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity  # -1 to 1
        subjectivity = blob.sentiment.subjectivity  # 0 to 1
        
        # Determine label
        if polarity > 0.1:
            label = 'positive'
        elif polarity < -0.1:
            label = 'negative'
        else:
            label = 'neutral'
        
        return SentimentScore(
            text_id=text_id,
            text_type=text_type,
            compound_score=polarity,
            positive_score=max(0, polarity),
            negative_score=max(0, -polarity),
            neutral_score=1 - abs(polarity),
            model_name='textblob',
            sentiment_label=label,
            confidence=abs(polarity),
            analyzed_at=datetime.utcnow(),
            text_length=len(text),
            metadata={'subjectivity': subjectivity},
        )
    
    def _analyze_transformers(self, text: str, text_id: int, text_type: str) -> SentimentScore:
        """Analyze using transformers model."""
        model = self.analyzers['transformers']
        
        # Truncate if too long (model max length is typically 512 tokens)
        max_chars = 2000
        if len(text) > max_chars:
            text = text[:max_chars]
        
        result = model(text)[0]
        label = result['label'].lower()  # 'POSITIVE' or 'NEGATIVE'
        score = result['score']
        
        # Convert to compound score
        if label == 'positive':
            compound = score
        else:  # negative
            compound = -score
        
        return SentimentScore(
            text_id=text_id,
            text_type=text_type,
            compound_score=compound,
            positive_score=score if label == 'positive' else 0,
            negative_score=score if label == 'negative' else 0,
            neutral_score=1 - score,
            model_name='transformers_distilbert',
            sentiment_label=label,
            confidence=score,
            analyzed_at=datetime.utcnow(),
            text_length=len(text),
        )
    
    def analyze_batch(
        self,
        texts: List[str],
        text_ids: List[int] = None,
        text_types: List[str] = None,
    ) -> List[SentimentScore]:
        """
        Analyze multiple texts.
        
        Args:
            texts: List of texts to analyze
            text_ids: Optional list of IDs
            text_types: Optional list of type labels
            
        Returns:
            List of SentimentScore objects
        """
        results = []
        
        for i, text in enumerate(texts):
            text_id = text_ids[i] if text_ids else None
            text_type = text_types[i] if text_types else None
            
            result = self.analyze(text, text_id, text_type)
            results.append(result)
        
        return results
    
    def get_aggregate_sentiment(self, scores: List[SentimentScore]) -> Dict[str, Any]:
        """
        Get aggregate sentiment statistics from multiple scores.
        
        Args:
            scores: List of sentiment scores
            
        Returns:
            Dictionary with aggregate statistics
        """
        if not scores:
            return {}
        
        compound_scores = [s.compound_score for s in scores if s.compound_score is not None]
        
        if not compound_scores:
            return {}
        
        import statistics
        
        return {
            'mean_compound': statistics.mean(compound_scores),
            'median_compound': statistics.median(compound_scores),
            'stdev_compound': statistics.stdev(compound_scores) if len(compound_scores) > 1 else 0,
            'positive_count': sum(1 for s in scores if s.sentiment_label == 'positive'),
            'negative_count': sum(1 for s in scores if s.sentiment_label == 'negative'),
            'neutral_count': sum(1 for s in scores if s.sentiment_label == 'neutral'),
            'total_count': len(scores),
        }


def analyze_sentiment(text: str, model: str = 'vader') -> SentimentScore:
    """
    Convenience function for quick sentiment analysis.
    
    Args:
        text: Text to analyze
        model: Model to use ('vader', 'textblob', 'transformers')
        
    Returns:
        SentimentScore object
    """
    analyzer = SentimentAnalyzer(models=[model])
    return analyzer.analyze(text)


# Example usage
EXAMPLE_USAGE = """
# Example: Analyzing bill sentiment

from analysis.sentiment import SentimentAnalyzer, analyze_sentiment

# Initialize analyzer
analyzer = SentimentAnalyzer(models=['vader'])

# Analyze a bill
bill_text = "A bill to provide healthcare benefits..."
score = analyzer.analyze(bill_text, text_id=123, text_type='bill')

print(f"Sentiment: {score.sentiment_label}")
print(f"Compound score: {score.compound_score:.3f}")
print(f"Confidence: {score.confidence:.3f}")

# Analyze multiple texts
bills = ["Bill 1 text...", "Bill 2 text...", "Bill 3 text..."]
scores = analyzer.analyze_batch(bills, text_ids=[1, 2, 3], text_types=['bill']*3)

# Get aggregate statistics
stats = analyzer.get_aggregate_sentiment(scores)
print(f"Average sentiment: {stats['mean_compound']:.3f}")

# Quick analysis
quick_score = analyze_sentiment("This is a positive statement", model='vader')
"""
