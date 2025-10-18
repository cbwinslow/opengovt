"""
Political bias detection module.

Detects political bias, framing, and rhetorical devices in legislative text
and political statements using linguistic analysis and ML models.
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import re

logger = logging.getLogger(__name__)

# Optional imports
try:
    from transformers import pipeline
    HAS_TRANSFORMERS = True
except ImportError:
    HAS_TRANSFORMERS = False
    pipeline = None


@dataclass
class BiasScore:
    """
    Represents political bias analysis results.
    """
    text_id: Optional[int] = None
    text_type: Optional[str] = None
    
    # Bias scores
    overall_bias: Optional[str] = None  # 'left', 'center', 'right', 'neutral'
    bias_score: Optional[float] = None  # -1 (left) to 1 (right)
    confidence: Optional[float] = None
    
    # Detected bias indicators
    loaded_language: List[str] = field(default_factory=list)
    emotional_appeals: List[str] = field(default_factory=list)
    partisan_framing: List[str] = field(default_factory=list)
    
    # Objectivity measures
    objectivity_score: Optional[float] = None  # 0 (subjective) to 1 (objective)
    
    # Metadata
    analyzed_at: Optional[datetime] = None
    model_name: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'text_id': self.text_id,
            'text_type': self.text_type,
            'overall_bias': self.overall_bias,
            'bias_score': self.bias_score,
            'confidence': self.confidence,
            'loaded_language': self.loaded_language,
            'emotional_appeals': self.emotional_appeals,
            'partisan_framing': self.partisan_framing,
            'objectivity_score': self.objectivity_score,
            'analyzed_at': self.analyzed_at.isoformat() if self.analyzed_at else None,
            'model_name': self.model_name,
            'metadata': self.metadata,
        }


class BiasDetector:
    """
    Detector for political bias in text.
    """
    
    # Lexicons of partisan language (simplified examples)
    LEFT_LEANING_TERMS = [
        'progressive', 'social justice', 'equity', 'climate crisis',
        'corporate greed', 'workers rights', 'universal healthcare',
        'living wage', 'affordable housing', 'tax the rich',
    ]
    
    RIGHT_LEANING_TERMS = [
        'conservative', 'traditional values', 'free market', 'individual liberty',
        'government overreach', 'law and order', 'strong defense',
        'lower taxes', 'business friendly', 'deregulation',
    ]
    
    LOADED_LANGUAGE_PATTERNS = [
        r'\b(radical|extreme|dangerous|disastrous|catastrophic)\b',
        r'\b(corrupt|dishonest|scandal|cover-up)\b',
        r'\b(unprecedented|historic|groundbreaking|revolutionary)\b',
    ]
    
    EMOTIONAL_APPEAL_PATTERNS = [
        r'\b(must|need to|have to|crucial|vital|essential)\b',
        r'\b(fear|worry|concern|alarming|shocking)\b',
        r'\b(hope|believe|trust|faith)\b',
    ]
    
    def __init__(self, use_transformer: bool = False):
        """
        Initialize bias detector.
        
        Args:
            use_transformer: Whether to use transformer-based model (requires transformers library)
        """
        self.use_transformer = use_transformer
        self.transformer_model = None
        
        if use_transformer and HAS_TRANSFORMERS:
            try:
                # Note: This is a placeholder - you would need a model specifically trained
                # for political bias detection. Such models exist but may need fine-tuning.
                logger.info("Transformer-based bias detection not yet implemented")
                # self.transformer_model = pipeline("text-classification", model="your-bias-model")
            except Exception as e:
                logger.error(f"Failed to load transformer model: {e}")
    
    def detect(self, text: str, text_id: int = None, text_type: str = None) -> BiasScore:
        """
        Detect political bias in text.
        
        Args:
            text: Text to analyze
            text_id: Optional ID for the text
            text_type: Optional type label
            
        Returns:
            BiasScore object with results
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for bias detection")
            return BiasScore(
                text_id=text_id,
                text_type=text_type,
                overall_bias='neutral',
                analyzed_at=datetime.utcnow(),
            )
        
        # Use rule-based detection
        return self._detect_rule_based(text, text_id, text_type)
    
    def _detect_rule_based(self, text: str, text_id: int, text_type: str) -> BiasScore:
        """
        Rule-based bias detection using lexicons and patterns.
        """
        text_lower = text.lower()
        
        # Count partisan terms
        left_count = sum(1 for term in self.LEFT_LEANING_TERMS if term in text_lower)
        right_count = sum(1 for term in self.RIGHT_LEANING_TERMS if term in text_lower)
        
        # Calculate bias score
        total_partisan = left_count + right_count
        if total_partisan > 0:
            bias_score = (right_count - left_count) / total_partisan
        else:
            bias_score = 0.0
        
        # Determine overall bias
        if bias_score > 0.3:
            overall_bias = 'right'
        elif bias_score < -0.3:
            overall_bias = 'left'
        elif abs(bias_score) > 0.1:
            overall_bias = 'center-right' if bias_score > 0 else 'center-left'
        else:
            overall_bias = 'neutral'
        
        # Detect loaded language
        loaded_language = []
        for pattern in self.LOADED_LANGUAGE_PATTERNS:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            loaded_language.extend(matches)
        
        # Detect emotional appeals
        emotional_appeals = []
        for pattern in self.EMOTIONAL_APPEAL_PATTERNS:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            emotional_appeals.extend(matches)
        
        # Calculate objectivity score (inverse of bias indicators)
        bias_indicators = len(loaded_language) + len(emotional_appeals) + total_partisan
        word_count = len(text.split())
        objectivity_score = max(0, 1 - (bias_indicators / word_count)) if word_count > 0 else 1.0
        
        # Calculate confidence based on number of indicators found
        confidence = min(1.0, total_partisan / 10)  # More indicators = higher confidence
        
        return BiasScore(
            text_id=text_id,
            text_type=text_type,
            overall_bias=overall_bias,
            bias_score=bias_score,
            confidence=confidence,
            loaded_language=list(set(loaded_language[:10])),  # Top 10 unique
            emotional_appeals=list(set(emotional_appeals[:10])),
            objectivity_score=objectivity_score,
            analyzed_at=datetime.utcnow(),
            model_name='rule_based',
            metadata={
                'left_term_count': left_count,
                'right_term_count': right_count,
            },
        )
    
    def analyze_framing(self, text: str) -> Dict[str, Any]:
        """
        Analyze how the text frames issues (problem framing, solution framing, etc.).
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary with framing analysis
        """
        # Problem framing keywords
        problem_frames = {
            'crisis': r'\bcrisis\b',
            'threat': r'\b(threat|danger|risk)\b',
            'failure': r'\b(fail|broken|dysfunction)\b',
            'injustice': r'\b(injustice|unfair|inequit)\b',
        }
        
        # Solution framing keywords
        solution_frames = {
            'reform': r'\b(reform|improve|enhance)\b',
            'protect': r'\b(protect|defend|secure)\b',
            'invest': r'\b(invest|fund|support)\b',
            'eliminate': r'\b(eliminate|end|stop)\b',
        }
        
        text_lower = text.lower()
        
        detected_problem_frames = {}
        for frame, pattern in problem_frames.items():
            matches = len(re.findall(pattern, text_lower, re.IGNORECASE))
            if matches > 0:
                detected_problem_frames[frame] = matches
        
        detected_solution_frames = {}
        for frame, pattern in solution_frames.items():
            matches = len(re.findall(pattern, text_lower, re.IGNORECASE))
            if matches > 0:
                detected_solution_frames[frame] = matches
        
        return {
            'problem_frames': detected_problem_frames,
            'solution_frames': detected_solution_frames,
        }
    
    def detect_rhetorical_devices(self, text: str) -> List[Dict[str, str]]:
        """
        Detect common rhetorical devices used in political text.
        
        Args:
            text: Text to analyze
            
        Returns:
            List of detected rhetorical devices
        """
        devices = []
        text_lower = text.lower()
        
        # Repetition (anaphora)
        sentences = text.split('.')
        if len(sentences) > 2:
            first_words = [s.strip().split()[0] if s.strip() else '' for s in sentences]
            for word in set(first_words):
                if word and first_words.count(word) >= 3:
                    devices.append({
                        'device': 'repetition/anaphora',
                        'example': f"Repeated opening: '{word}'",
                    })
        
        # Rhetorical questions
        if '?' in text:
            questions = [s.strip() for s in text.split('?') if s.strip()]
            if questions:
                devices.append({
                    'device': 'rhetorical_question',
                    'count': len(questions),
                })
        
        # Parallelism (simplified detection)
        if re.search(r'\b(not only .+ but also|either .+ or|neither .+ nor)\b', text_lower):
            devices.append({
                'device': 'parallelism',
                'note': 'Parallel structure detected',
            })
        
        # Alliteration (simplified)
        words = text_lower.split()
        for i in range(len(words) - 2):
            if words[i] and words[i+1] and words[i][0] == words[i+1][0]:
                devices.append({
                    'device': 'alliteration',
                    'example': f"{words[i]} {words[i+1]}",
                })
                break
        
        return devices


def detect_political_bias(text: str) -> BiasScore:
    """
    Convenience function for quick bias detection.
    
    Args:
        text: Text to analyze
        
    Returns:
        BiasScore object
    """
    detector = BiasDetector()
    return detector.detect(text)


# Example usage
EXAMPLE_USAGE = """
# Example: Detecting political bias

from analysis.bias_detector import BiasDetector, detect_political_bias

# Initialize detector
detector = BiasDetector()

# Analyze a statement
statement = "We must fight corporate greed and provide living wages for all workers"
score = detector.detect(statement, text_id=123, text_type='statement')

print(f"Overall bias: {score.overall_bias}")
print(f"Bias score: {score.bias_score:.3f}")
print(f"Objectivity: {score.objectivity_score:.3f}")
print(f"Loaded language: {score.loaded_language}")

# Analyze framing
framing = detector.analyze_framing(statement)
print(f"Problem frames: {framing['problem_frames']}")
print(f"Solution frames: {framing['solution_frames']}")

# Detect rhetorical devices
devices = detector.detect_rhetorical_devices(statement)
for device in devices:
    print(f"Device: {device}")

# Quick bias detection
quick_score = detect_political_bias("Lower taxes and less regulation will help businesses")
print(f"Bias: {quick_score.overall_bias}")
"""
