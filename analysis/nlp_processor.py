"""
NLP processing module using spaCy for entity extraction, POS tagging, and text analysis.

This module provides comprehensive NLP processing for legislative text including:
- Named Entity Recognition (NER)
- Part-of-Speech tagging
- Dependency parsing
- Text preprocessing and tokenization
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

# Optional imports
try:
    import spacy
    from spacy.tokens import Doc
    HAS_SPACY = True
except ImportError:
    HAS_SPACY = False
    spacy = None
    Doc = None

logger = logging.getLogger(__name__)


@dataclass
class Entity:
    """
    Represents a named entity extracted from text.
    """
    text: str
    label: str  # PERSON, ORG, GPE, LAW, etc.
    start_char: int
    end_char: int
    confidence: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'text': self.text,
            'label': self.label,
            'start_char': self.start_char,
            'end_char': self.end_char,
            'confidence': self.confidence,
        }


@dataclass
class ProcessedText:
    """
    Represents processed text with entities and linguistic features.
    """
    text_id: Optional[int] = None
    text_type: Optional[str] = None
    
    # Extracted entities
    entities: List[Entity] = field(default_factory=list)
    
    # Linguistic features
    sentences: List[str] = field(default_factory=list)
    tokens: List[str] = field(default_factory=list)
    lemmas: List[str] = field(default_factory=list)
    pos_tags: List[str] = field(default_factory=list)
    
    # Statistics
    sentence_count: int = 0
    token_count: int = 0
    avg_sentence_length: float = 0.0
    
    # Metadata
    processed_at: Optional[datetime] = None
    model_name: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'text_id': self.text_id,
            'text_type': self.text_type,
            'entities': [e.to_dict() for e in self.entities],
            'sentence_count': self.sentence_count,
            'token_count': self.token_count,
            'avg_sentence_length': self.avg_sentence_length,
            'processed_at': self.processed_at.isoformat() if self.processed_at else None,
            'model_name': self.model_name,
            'metadata': self.metadata,
        }


class NLPProcessor:
    """
    NLP processor using spaCy for comprehensive text analysis.
    """
    
    DEFAULT_MODEL = 'en_core_web_sm'  # Small English model
    LARGE_MODEL = 'en_core_web_lg'    # Large model with word vectors
    
    def __init__(self, model_name: str = None, disable: List[str] = None):
        """
        Initialize NLP processor.
        
        Args:
            model_name: Name of spaCy model to use
            disable: List of pipeline components to disable for speed
        """
        if not HAS_SPACY:
            raise ImportError(
                "spaCy not installed. Install with: "
                "pip install spacy && python -m spacy download en_core_web_sm"
            )
        
        self.model_name = model_name or self.DEFAULT_MODEL
        self.disable = disable or []
        
        try:
            logger.info(f"Loading spaCy model: {self.model_name}")
            self.nlp = spacy.load(self.model_name, disable=self.disable)
        except OSError:
            logger.error(f"Model {self.model_name} not found. Downloading...")
            # Try to download the model
            import subprocess
            subprocess.run(["python", "-m", "spacy", "download", self.model_name])
            self.nlp = spacy.load(self.model_name, disable=self.disable)
        
        logger.info(f"Loaded spaCy model: {self.model_name}")
    
    def process(self, text: str, text_id: int = None, text_type: str = None) -> ProcessedText:
        """
        Process text and extract entities and linguistic features.
        
        Args:
            text: Text to process
            text_id: Optional ID for the text
            text_type: Optional type label
            
        Returns:
            ProcessedText object with results
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for NLP processing")
            return ProcessedText(
                text_id=text_id,
                text_type=text_type,
                processed_at=datetime.utcnow(),
                model_name=self.model_name,
            )
        
        # Process with spaCy
        doc = self.nlp(text)
        
        # Extract entities
        entities = []
        for ent in doc.ents:
            entities.append(Entity(
                text=ent.text,
                label=ent.label_,
                start_char=ent.start_char,
                end_char=ent.end_char,
            ))
        
        # Extract sentences
        sentences = [sent.text.strip() for sent in doc.sents]
        
        # Extract tokens and linguistic features
        tokens = [token.text for token in doc if not token.is_space]
        lemmas = [token.lemma_ for token in doc if not token.is_space]
        pos_tags = [token.pos_ for token in doc if not token.is_space]
        
        # Calculate statistics
        sentence_count = len(sentences)
        token_count = len(tokens)
        avg_sentence_length = token_count / sentence_count if sentence_count > 0 else 0
        
        return ProcessedText(
            text_id=text_id,
            text_type=text_type,
            entities=entities,
            sentences=sentences,
            tokens=tokens,
            lemmas=lemmas,
            pos_tags=pos_tags,
            sentence_count=sentence_count,
            token_count=token_count,
            avg_sentence_length=avg_sentence_length,
            processed_at=datetime.utcnow(),
            model_name=self.model_name,
        )
    
    def extract_entities_by_type(self, text: str, entity_types: List[str] = None) -> List[Entity]:
        """
        Extract specific types of entities from text.
        
        Args:
            text: Text to process
            entity_types: List of entity types to extract (e.g., ['PERSON', 'ORG', 'GPE'])
                         If None, extracts all entities
            
        Returns:
            List of Entity objects
        """
        doc = self.nlp(text)
        entities = []
        
        for ent in doc.ents:
            if entity_types is None or ent.label_ in entity_types:
                entities.append(Entity(
                    text=ent.text,
                    label=ent.label_,
                    start_char=ent.start_char,
                    end_char=ent.end_char,
                ))
        
        return entities
    
    def extract_political_entities(self, text: str) -> Dict[str, List[Entity]]:
        """
        Extract politically relevant entities (people, organizations, locations, laws).
        
        Args:
            text: Text to process
            
        Returns:
            Dictionary with entity types as keys and lists of entities as values
        """
        doc = self.nlp(text)
        
        result = {
            'people': [],
            'organizations': [],
            'locations': [],
            'laws': [],
            'dates': [],
            'other': [],
        }
        
        for ent in doc.ents:
            entity = Entity(
                text=ent.text,
                label=ent.label_,
                start_char=ent.start_char,
                end_char=ent.end_char,
            )
            
            if ent.label_ == 'PERSON':
                result['people'].append(entity)
            elif ent.label_ in ['ORG', 'NORP']:  # Organization or political group
                result['organizations'].append(entity)
            elif ent.label_ in ['GPE', 'LOC']:  # Geopolitical entity or location
                result['locations'].append(entity)
            elif ent.label_ == 'LAW':
                result['laws'].append(entity)
            elif ent.label_ == 'DATE':
                result['dates'].append(entity)
            else:
                result['other'].append(entity)
        
        return result
    
    def get_key_phrases(self, text: str, top_n: int = 10) -> List[str]:
        """
        Extract key noun phrases from text.
        
        Args:
            text: Text to process
            top_n: Number of top phrases to return
            
        Returns:
            List of key noun phrases
        """
        doc = self.nlp(text)
        
        # Extract noun chunks (noun phrases)
        phrases = []
        for chunk in doc.noun_chunks:
            # Clean up the phrase
            phrase = chunk.text.strip().lower()
            if len(phrase) > 3 and phrase not in phrases:  # Avoid duplicates and very short phrases
                phrases.append(phrase)
        
        # Return top N
        return phrases[:top_n]
    
    def analyze_complexity(self, text: str) -> Dict[str, float]:
        """
        Analyze text complexity using various metrics.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary with complexity metrics
        """
        doc = self.nlp(text)
        
        # Count various elements
        sentence_count = len(list(doc.sents))
        token_count = len([t for t in doc if not t.is_space])
        word_count = len([t for t in doc if not t.is_space and not t.is_punct])
        
        # Calculate metrics
        avg_sentence_length = word_count / sentence_count if sentence_count > 0 else 0
        
        # Count complex words (more than 2 syllables - rough estimate)
        complex_words = len([t for t in doc if not t.is_space and not t.is_punct and len(t.text) > 7])
        
        # Lexical diversity (unique words / total words)
        unique_words = len(set([t.lemma_.lower() for t in doc if not t.is_space and not t.is_punct]))
        lexical_diversity = unique_words / word_count if word_count > 0 else 0
        
        return {
            'sentence_count': sentence_count,
            'word_count': word_count,
            'avg_sentence_length': avg_sentence_length,
            'complex_word_count': complex_words,
            'lexical_diversity': lexical_diversity,
        }


def extract_entities(text: str, entity_types: List[str] = None) -> List[Entity]:
    """
    Convenience function to extract entities from text.
    
    Args:
        text: Text to process
        entity_types: Optional list of entity types to extract
        
    Returns:
        List of Entity objects
    """
    processor = NLPProcessor()
    return processor.extract_entities_by_type(text, entity_types)


# Example usage
EXAMPLE_USAGE = """
# Example: Processing legislative text with NLP

from analysis.nlp_processor import NLPProcessor, extract_entities

# Initialize processor
processor = NLPProcessor(model_name='en_core_web_sm')

# Process a bill
bill_text = "Senator Jane Smith introduced a bill to reform healthcare..."
result = processor.process(bill_text, text_id=123, text_type='bill')

print(f"Found {len(result.entities)} entities")
for entity in result.entities:
    print(f"  {entity.text}: {entity.label}")

# Extract specific entity types
people = processor.extract_entities_by_type(bill_text, entity_types=['PERSON'])
print(f"Found {len(people)} people mentioned")

# Extract political entities
political = processor.extract_political_entities(bill_text)
print(f"People: {[e.text for e in political['people']]}")
print(f"Organizations: {[e.text for e in political['organizations']]}")

# Get key phrases
phrases = processor.get_key_phrases(bill_text, top_n=5)
print(f"Key phrases: {phrases}")

# Analyze complexity
complexity = processor.analyze_complexity(bill_text)
print(f"Complexity metrics: {complexity}")

# Quick entity extraction
entities = extract_entities("President Biden signed the bill", entity_types=['PERSON'])
"""
