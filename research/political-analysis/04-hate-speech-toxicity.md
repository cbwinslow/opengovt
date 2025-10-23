# Hate Speech and Toxicity Detection in Political Discourse

## Overview

This document covers methods for detecting hate speech, toxic language, and inflammatory rhetoric in political communications, with emphasis on ethical considerations and accuracy.

## 1. Understanding Toxicity in Political Context

### 1.1 Definitions

**Toxicity**: Language that is rude, disrespectful, or likely to make someone leave a discussion

**Hate Speech**: Speech attacking a person or group based on attributes such as race, religion, ethnic origin, sexual orientation, disability, or gender

**Political Toxicity Types**:
- Personal attacks and ad hominem
- Inflammatory rhetoric
- Dog whistles and coded language
- Dehumanizing language
- Conspiracy theories and misinformation
- Calls for violence

### 1.2 Challenges in Political Context

Political discourse has unique challenges:
- **Free speech considerations**: Balancing detection with democratic values
- **Context matters**: Same words have different meanings in different contexts
- **Subjectivity**: Political opinions vs. toxic content
- **False positives**: Quoting hate speech to condemn it
- **Evolution**: Language evolves; new dog whistles emerge

## 2. Detection Methods

### 2.1 Perspective API (Google Jigsaw)

```python
from googleapiclient import discovery
import json

class PerspectiveAPIAnalyzer:
    def __init__(self, api_key):
        self.client = discovery.build(
            "commentanalyzer",
            "v1alpha1",
            developerKey=api_key,
            discoveryServiceUrl="https://commentanalyzer.googleapis.com/$discovery/rest?version=v1alpha1",
            static_discovery=False,
        )
    
    def analyze_text(self, text):
        """
        Analyze text for multiple toxicity attributes
        """
        analyze_request = {
            'comment': {'text': text},
            'requestedAttributes': {
                'TOXICITY': {},
                'SEVERE_TOXICITY': {},
                'IDENTITY_ATTACK': {},
                'INSULT': {},
                'PROFANITY': {},
                'THREAT': {},
                'SEXUALLY_EXPLICIT': {},
                'FLIRTATION': {}
            }
        }
        
        response = self.client.comments().analyze(body=analyze_request).execute()
        
        scores = {}
        for attr, data in response['attributeScores'].items():
            scores[attr.lower()] = data['summaryScore']['value']
        
        return {
            'scores': scores,
            'is_toxic': scores.get('toxicity', 0) > 0.7,
            'severity': self._categorize_severity(scores.get('toxicity', 0))
        }
    
    def _categorize_severity(self, score):
        if score < 0.3:
            return 'low'
        elif score < 0.6:
            return 'moderate'
        elif score < 0.8:
            return 'high'
        else:
            return 'severe'
```

### 2.2 Detoxify (Unitary AI)

```python
from detoxify import Detoxify

class DetoxifyAnalyzer:
    def __init__(self, model_type='original'):
        """
        model_type: 'original', 'unbiased', or 'multilingual'
        """
        self.model = Detoxify(model_type)
    
    def analyze(self, text):
        """
        Analyze text for toxicity
        Returns: toxicity, severe_toxicity, obscene, threat, insult, identity_attack
        """
        results = self.model.predict(text)
        
        return {
            'toxicity': float(results['toxicity']),
            'severe_toxicity': float(results['severe_toxicity']),
            'obscene': float(results['obscene']),
            'threat': float(results['threat']),
            'insult': float(results['insult']),
            'identity_attack': float(results['identity_attack']),
            'max_toxicity': max(results.values()),
            'is_toxic': results['toxicity'] > 0.5
        }
    
    def batch_analyze(self, texts):
        """Efficiently analyze multiple texts"""
        results = self.model.predict(texts)
        
        analyzed = []
        for i in range(len(texts)):
            analyzed.append({
                'text': texts[i],
                'toxicity': float(results['toxicity'][i]),
                'severe_toxicity': float(results['severe_toxicity'][i]),
                'is_toxic': results['toxicity'][i] > 0.5
            })
        
        return analyzed
```

### 2.3 Custom Political Hate Speech Detector

```python
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

class PoliticalHateSpeechDetector:
    def __init__(self):
        # Using hate speech detection model
        self.tokenizer = AutoTokenizer.from_pretrained(
            "IMSyPP/hate_speech_en"
        )
        self.model = AutoModelForSequenceClassification.from_pretrained(
            "IMSyPP/hate_speech_en"
        )
        
        # Political context keywords
        self.political_context_markers = {
            'policy_critique': [
                'policy', 'legislation', 'bill', 'vote', 'position',
                'stance', 'record', 'voting'
            ],
            'personal_attack': [
                'idiot', 'stupid', 'corrupt', 'liar', 'traitor',
                'evil', 'criminal', 'scum'
            ]
        }
    
    def detect(self, text):
        """Detect hate speech with political context awareness"""
        
        # Tokenize and predict
        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=512
        )
        
        with torch.no_grad():
            outputs = self.model(**inputs)
            probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
        
        # Get prediction
        hate_prob = probs[0][1].item()  # Probability of hate speech
        
        # Context analysis
        context = self._analyze_political_context(text)
        
        # Adjust score based on context
        adjusted_score = self._adjust_for_context(hate_prob, context)
        
        return {
            'raw_hate_score': hate_prob,
            'adjusted_hate_score': adjusted_score,
            'is_hate_speech': adjusted_score > 0.7,
            'context': context,
            'confidence': abs(adjusted_score - 0.5) * 2  # Distance from uncertain (0.5)
        }
    
    def _analyze_political_context(self, text):
        """Analyze if text is policy critique vs personal attack"""
        text_lower = text.lower()
        
        policy_score = sum(
            1 for word in self.political_context_markers['policy_critique']
            if word in text_lower
        )
        attack_score = sum(
            1 for word in self.political_context_markers['personal_attack']
            if word in text_lower
        )
        
        return {
            'has_policy_context': policy_score > 0,
            'has_personal_attacks': attack_score > 0,
            'policy_score': policy_score,
            'attack_score': attack_score
        }
    
    def _adjust_for_context(self, base_score, context):
        """Adjust hate speech score based on political context"""
        
        # If discussing policy, slightly reduce hate score
        # If personal attacks present, slightly increase
        
        adjustment = 0
        
        if context['has_policy_context']:
            adjustment -= 0.1
        
        if context['has_personal_attacks']:
            adjustment += 0.15
        
        return max(0, min(1, base_score + adjustment))
```

## 3. Dog Whistle Detection

### 3.1 Coded Language Patterns

```python
class DogWhistleDetector:
    """
    Detect coded language and dog whistles in political discourse
    """
    
    def __init__(self):
        # Known dog whistles (examples - incomplete for ethical reasons)
        self.dog_whistles = {
            'racial': {
                'urban': ['context: crime, welfare'],
                'inner city': ['context: problems, violence'],
                'thugs': ['context: protesters, youth'],
                'welfare queens': ['context: social programs'],
                'law and order': ['context: specific communities']
            },
            'immigration': {
                'anchor babies': ['dehumanizing term'],
                'illegal aliens': ['vs undocumented immigrants'],
                'invasion': ['militaristic framing']
            },
            'antisemitic': {
                'globalists': ['context: conspiracy theories'],
                'international bankers': ['context: control, manipulation']
            },
            'islamophobic': {
                'no-go zones': ['context: Muslim areas'],
                'sharia law': ['context: fear-mongering']
            }
        }
    
    def detect_dog_whistles(self, text):
        """
        Detect potential dog whistles
        Returns suspicious phrases with context
        """
        text_lower = text.lower()
        detected = []
        
        for category, whistles in self.dog_whistles.items():
            for phrase, contexts in whistles.items():
                if phrase in text_lower:
                    # Get surrounding context
                    index = text_lower.find(phrase)
                    start = max(0, index - 50)
                    end = min(len(text), index + len(phrase) + 50)
                    context = text[start:end]
                    
                    detected.append({
                        'phrase': phrase,
                        'category': category,
                        'context': context,
                        'known_contexts': contexts,
                        'confidence': 'medium'  # Would use ML for better confidence
                    })
        
        return {
            'dog_whistles_found': len(detected),
            'detections': detected,
            'requires_human_review': len(detected) > 0
        }
```

### 3.2 Framing and Rhetoric Analysis

```python
class RhetoricalAnalyzer:
    """
    Analyze rhetorical devices that can indicate inflammatory speech
    """
    
    def __init__(self):
        self.inflammatory_patterns = {
            'dehumanization': [
                'animals', 'vermin', 'infestation', 'plague',
                'cockroaches', 'rats', 'parasites'
            ],
            'militaristic': [
                'war on', 'battle', 'fight', 'enemy', 'invasion',
                'attack', 'destroy', 'eliminate'
            ],
            'apocalyptic': [
                'end of civilization', 'destroy America', 'collapse',
                'catastrophe', 'existential threat'
            ],
            'conspiracy': [
                'deep state', 'shadow government', 'rigged',
                'stolen', 'fake', 'hoax', 'puppet'
            ]
        }
    
    def analyze_rhetoric(self, text):
        """Analyze rhetorical patterns"""
        text_lower = text.lower()
        
        patterns_found = {}
        total_score = 0
        
        for pattern_type, keywords in self.inflammatory_patterns.items():
            count = sum(1 for kw in keywords if kw in text_lower)
            if count > 0:
                patterns_found[pattern_type] = count
                total_score += count
        
        return {
            'inflammatory_score': min(1.0, total_score / 10),  # Normalize
            'patterns': patterns_found,
            'is_inflammatory': total_score >= 3,
            'severity': 'high' if total_score >= 5 else 'medium' if total_score >= 2 else 'low'
        }
```

## 4. Monitoring Politician Communications

### 4.1 Continuous Monitoring System

```python
class PoliticianToxicityMonitor:
    def __init__(self):
        self.detoxify = DetoxifyAnalyzer()
        self.hate_detector = PoliticalHateSpeechDetector()
        self.dog_whistle = DogWhistleDetector()
        self.rhetoric = RhetoricalAnalyzer()
    
    def monitor_politician(self, politician_id):
        """
        Monitor all communications from a politician
        """
        # Get all recent communications
        statements = get_politician_statements(politician_id, days=30)
        tweets = get_politician_tweets(politician_id, days=30)
        speeches = get_politician_speeches(politician_id, days=30)
        
        all_comms = statements + tweets + speeches
        
        results = {
            'politician_id': politician_id,
            'period': '30 days',
            'total_analyzed': len(all_comms),
            'toxic_items': [],
            'hate_speech_items': [],
            'dog_whistles': [],
            'inflammatory': [],
            'summary': {}
        }
        
        toxic_count = 0
        hate_count = 0
        
        for comm in all_comms:
            text = comm['text']
            
            # Toxicity check
            tox = self.detoxify.analyze(text)
            if tox['is_toxic']:
                toxic_count += 1
                results['toxic_items'].append({
                    'text': text[:200],
                    'score': tox['toxicity'],
                    'type': comm['type'],
                    'date': comm['date']
                })
            
            # Hate speech check
            hate = self.hate_detector.detect(text)
            if hate['is_hate_speech']:
                hate_count += 1
                results['hate_speech_items'].append({
                    'text': text[:200],
                    'score': hate['adjusted_hate_score'],
                    'type': comm['type'],
                    'date': comm['date']
                })
            
            # Dog whistle check
            whistles = self.dog_whistle.detect_dog_whistles(text)
            if whistles['dog_whistles_found'] > 0:
                results['dog_whistles'].extend(whistles['detections'])
            
            # Rhetoric check
            rhet = self.rhetoric.analyze_rhetoric(text)
            if rhet['is_inflammatory']:
                results['inflammatory'].append({
                    'text': text[:200],
                    'score': rhet['inflammatory_score'],
                    'patterns': rhet['patterns']
                })
        
        # Summary statistics
        results['summary'] = {
            'toxicity_rate': round(toxic_count / len(all_comms) * 100, 2),
            'hate_speech_rate': round(hate_count / len(all_comms) * 100, 2),
            'dog_whistle_count': len(results['dog_whistles']),
            'inflammatory_count': len(results['inflammatory']),
            'overall_rating': self._calculate_overall_rating(results)
        }
        
        return results
    
    def _calculate_overall_rating(self, results):
        """Calculate A-F rating for toxicity"""
        summary = results['summary']
        
        # Deduct points for issues
        score = 100
        score -= summary['toxicity_rate'] * 2
        score -= summary['hate_speech_rate'] * 5
        score -= summary['dog_whistle_count']
        score -= summary['inflammatory_count'] * 0.5
        
        score = max(0, score)
        
        if score >= 90: return 'A'
        elif score >= 80: return 'B'
        elif score >= 70: return 'C'
        elif score >= 60: return 'D'
        else: return 'F'
```

### 4.2 Trend Analysis

```python
class ToxicityTrendAnalyzer:
    def analyze_trends(self, politician_id, months=12):
        """Analyze toxicity trends over time"""
        import pandas as pd
        import numpy as np
        
        # Get historical data
        monthly_data = []
        
        for month in range(months):
            start_date = datetime.now() - timedelta(days=30 * (month + 1))
            end_date = datetime.now() - timedelta(days=30 * month)
            
            comms = get_politician_comms_in_range(
                politician_id, start_date, end_date
            )
            
            if not comms:
                continue
            
            # Analyze
            detoxify = DetoxifyAnalyzer()
            scores = [detoxify.analyze(c['text'])['toxicity'] for c in comms]
            
            monthly_data.append({
                'month': start_date.strftime('%Y-%m'),
                'avg_toxicity': np.mean(scores),
                'max_toxicity': np.max(scores),
                'toxic_pct': sum(1 for s in scores if s > 0.5) / len(scores) * 100,
                'count': len(comms)
            })
        
        df = pd.DataFrame(monthly_data)
        
        # Calculate trend
        if len(df) > 1:
            trend = np.polyfit(range(len(df)), df['avg_toxicity'], 1)[0]
            trend_direction = 'increasing' if trend > 0.01 else 'decreasing' if trend < -0.01 else 'stable'
        else:
            trend_direction = 'insufficient_data'
        
        return {
            'monthly_data': monthly_data,
            'trend_direction': trend_direction,
            'current_avg': monthly_data[0]['avg_toxicity'] if monthly_data else 0,
            'peak_month': max(monthly_data, key=lambda x: x['avg_toxicity']) if monthly_data else None
        }
```

## 5. Ethical Considerations

### 5.1 Best Practices

```python
class EthicalToxicityAnalysis:
    """
    Ethical framework for toxicity detection
    """
    
    PRINCIPLES = {
        'transparency': 'Always disclose when content is flagged by AI',
        'appeals': 'Provide mechanism to contest false positives',
        'context': 'Consider context, not just individual words',
        'fairness': 'Avoid bias against particular political views',
        'privacy': 'Protect user privacy in reporting',
        'human_review': 'High-stakes decisions require human review'
    }
    
    def flag_content(self, text, analysis_results, threshold=0.7):
        """
        Flag content with ethical safeguards
        """
        flag = {
            'flagged': False,
            'reason': None,
            'confidence': 0,
            'requires_human_review': False,
            'appeal_available': True,
            'context_considered': True
        }
        
        # Check if meets threshold
        max_score = max([
            analysis_results.get('toxicity', 0),
            analysis_results.get('hate_speech', 0)
        ])
        
        if max_score > threshold:
            flag['flagged'] = True
            flag['confidence'] = max_score
            
            # Determine reason
            if analysis_results.get('hate_speech', 0) > threshold:
                flag['reason'] = 'potential_hate_speech'
                flag['requires_human_review'] = True  # Always review hate speech
            elif analysis_results.get('toxicity', 0) > threshold:
                flag['reason'] = 'high_toxicity'
                flag['requires_human_review'] = max_score > 0.85
        
        return flag
    
    def generate_report(self, politician_id, analysis):
        """Generate ethical transparency report"""
        report = {
            'politician_id': politician_id,
            'analysis_date': datetime.now().isoformat(),
            'methodology': {
                'models_used': ['Detoxify', 'PerspectiveAPI'],
                'thresholds': {'toxicity': 0.7, 'hate_speech': 0.7},
                'human_review': 'Required for hate speech flags'
            },
            'results': analysis,
            'limitations': [
                'AI models may have false positives',
                'Context interpretation is limited',
                'Political speech has unique characteristics',
                'Results should be interpreted with caution'
            ],
            'appeal_process': 'Contact admin@example.com for review'
        }
        
        return report
```

## 6. Database Schema

```sql
-- Toxicity analysis table
CREATE TABLE toxicity_analysis (
    id SERIAL PRIMARY KEY,
    politician_id INTEGER REFERENCES politicians(id),
    content_type VARCHAR(50),  -- 'tweet', 'statement', 'speech'
    content_id INTEGER,
    content_text TEXT,
    analysis_date TIMESTAMP DEFAULT NOW(),
    
    -- Scores
    toxicity_score DECIMAL(4,3),
    severe_toxicity_score DECIMAL(4,3),
    identity_attack_score DECIMAL(4,3),
    insult_score DECIMAL(4,3),
    threat_score DECIMAL(4,3),
    
    -- Flags
    is_toxic BOOLEAN,
    is_hate_speech BOOLEAN,
    has_dog_whistles BOOLEAN,
    is_inflammatory BOOLEAN,
    
    -- Review
    flagged_for_review BOOLEAN,
    human_reviewed BOOLEAN,
    review_outcome VARCHAR(50),
    
    -- Metadata
    model_version VARCHAR(50),
    confidence DECIMAL(4,3)
);

CREATE INDEX idx_toxicity_politician ON toxicity_analysis(politician_id);
CREATE INDEX idx_toxicity_flagged ON toxicity_analysis(flagged_for_review);
CREATE INDEX idx_toxicity_date ON toxicity_analysis(analysis_date);

-- Trend tracking view
CREATE VIEW politician_toxicity_trends AS
SELECT 
    politician_id,
    DATE_TRUNC('month', analysis_date) as month,
    AVG(toxicity_score) as avg_toxicity,
    MAX(toxicity_score) as max_toxicity,
    COUNT(*) as total_analyzed,
    SUM(CASE WHEN is_toxic THEN 1 ELSE 0 END) as toxic_count,
    SUM(CASE WHEN is_hate_speech THEN 1 ELSE 0 END) as hate_speech_count
FROM toxicity_analysis
GROUP BY politician_id, DATE_TRUNC('month', analysis_date);
```

## 7. Case Studies

### 7.1 Real-World Implementations

**Twitter's Content Moderation**
- Multi-stage review process
- AI flags + human moderators
- Transparency in enforcement

**Facebook's Community Standards**
- Combination of AI and human review
- Appeals process
- Regular transparency reports

**Reddit's Hate Speech Detection**
- AutoModerator + manual moderation
- Community-driven standards
- Quarantine and removal policies

## 8. References

### Tools and APIs
- **Perspective API**: https://perspectiveapi.com/
- **Detoxify**: https://github.com/unitaryai/detoxify
- **HateBase**: https://hatebase.org/
- **OpenAI Moderation API**: https://platform.openai.com/docs/guides/moderation

### Academic Papers
1. **"Automated Hate Speech Detection and the Problem of Offensive Language"** - Davidson et al., 2017
2. **"Ex Machina: Personal Attacks Seen at Scale"** - Wulczyn et al., 2017
3. **"Hate Speech Detection with Comment Embeddings"** - Djuric et al., 2015

### Ethical Guidelines
- **ACM Code of Ethics**: https://www.acm.org/code-of-ethics
- **AI Ethics Guidelines**: Partnership on AI
- **Content Moderation Best Practices**: Santa Clara Principles

---

**Last Updated**: 2025-10-23
**Next**: [05-social-media-analysis.md](05-social-media-analysis.md)
