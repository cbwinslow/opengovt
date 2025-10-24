# Political Entity Metrics and Analysis Framework

## Overview

This document details entity-specific metrics for analyzing political behavior, including bias detection, transparency measurement, consistency tracking, and impact assessment.

## 1. Political Bias Detection

### 1.1 Bias Measurement Framework

Political bias operates on multiple dimensions:

```
Economic: Left ←──────────────────→ Right
         Socialist          Free Market

Social: Progressive ←──────────────→ Conservative
        Liberal              Traditional

Authority: Libertarian ←───────────→ Authoritarian
           Freedom             Control
```

### 1.2 Bias Detection Methods

#### Lexicon-Based Approach

```python
class PoliticalBiasDetector:
    def __init__(self):
        self.left_indicators = {
            'progressive', 'reform', 'equality', 'justice', 'social',
            'universal', 'public', 'workers', 'unions', 'regulate',
            'medicare for all', 'green new deal', 'wealth tax'
        }
        
        self.right_indicators = {
            'conservative', 'traditional', 'freedom', 'liberty',
            'free market', 'deregulation', 'private sector', 'tax cuts',
            'individual responsibility', 'strong borders', 'law and order'
        }
        
        self.loaded_language = {
            'left': {
                'crisis': 1.5, 'urgent': 1.2, 'justice': 1.8,
                'exploited': 2.0, 'oppressed': 2.0
            },
            'right': {
                'freedom': 1.8, 'patriot': 1.5, 'traditional values': 1.7,
                'overreach': 2.0, 'socialism': -2.5
            }
        }
    
    def calculate_bias_score(self, text):
        """
        Calculate bias score from -1 (left) to +1 (right)
        """
        text_lower = text.lower()
        
        # Count indicators
        left_count = sum(1 for word in self.left_indicators if word in text_lower)
        right_count = sum(1 for word in self.right_indicators if word in text_lower)
        
        # Weight by loaded language
        left_weight = sum(
            weight for word, weight in self.loaded_language['left'].items()
            if word in text_lower
        )
        right_weight = sum(
            weight for word, weight in self.loaded_language['right'].items()
            if word in text_lower
        )
        
        # Calculate total
        left_total = left_count + left_weight
        right_total = right_count + right_weight
        
        if left_total + right_total == 0:
            return 0  # Neutral
        
        bias_score = (right_total - left_total) / (right_total + left_total)
        
        return {
            'bias_score': bias_score,
            'left_indicators': left_count,
            'right_indicators': right_count,
            'lean': 'left' if bias_score < -0.1 else 'right' if bias_score > 0.1 else 'center'
        }
```

#### Machine Learning Approach

```python
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

class MLBiasDetector:
    def __init__(self):
        # Using a hypothetical pre-trained bias detection model
        self.tokenizer = AutoTokenizer.from_pretrained('bert-base-uncased')
        self.model = AutoModelForSequenceClassification.from_pretrained(
            'bert-base-uncased',
            num_labels=5  # Far-left, Left, Center, Right, Far-right
        )
    
    def predict_bias(self, text):
        """Predict political bias using ML"""
        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            max_length=512,
            truncation=True,
            padding=True
        )
        
        with torch.no_grad():
            outputs = self.model(**inputs)
            probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
        
        labels = ['far-left', 'left', 'center', 'right', 'far-right']
        scores = probs[0].tolist()
        
        # Convert to -1 to 1 scale
        bias_scale = [-1.0, -0.5, 0.0, 0.5, 1.0]
        weighted_bias = sum(s * b for s, b in zip(scores, bias_scale))
        
        return {
            'bias_score': weighted_bias,
            'confidence': max(scores),
            'distribution': dict(zip(labels, scores))
        }
```

### 1.3 Framing Analysis

```python
class FramingAnalyzer:
    """Detect how issues are framed"""
    
    FRAMES = {
        'immigration': {
            'security': ['border', 'illegal', 'crime', 'enforcement'],
            'humanitarian': ['families', 'refugees', 'asylum', 'children'],
            'economic': ['jobs', 'workers', 'wages', 'economy']
        },
        'healthcare': {
            'freedom': ['choice', 'free market', 'competition'],
            'access': ['universal', 'coverage', 'affordable', 'right'],
            'cost': ['expensive', 'burden', 'taxpayer', 'sustainable']
        }
    }
    
    def detect_framing(self, text, issue):
        """Detect which frame is used for an issue"""
        if issue not in self.FRAMES:
            return None
        
        text_lower = text.lower()
        frame_scores = {}
        
        for frame_name, keywords in self.FRAMES[issue].items():
            score = sum(1 for kw in keywords if kw in text_lower)
            frame_scores[frame_name] = score
        
        # Determine primary frame
        primary_frame = max(frame_scores.items(), key=lambda x: x[1])
        
        return {
            'issue': issue,
            'primary_frame': primary_frame[0],
            'frame_scores': frame_scores
        }
```

## 2. Transparency Index

### 2.1 Transparency Metrics

Transparency is measured across multiple dimensions:

1. **Disclosure**: Financial, conflicts of interest
2. **Accessibility**: Response to constituents, public events
3. **Clarity**: Readability of communications
4. **Consistency**: Alignment between words and actions

### 2.2 Implementation

```python
class TransparencyScorer:
    def __init__(self):
        self.weights = {
            'financial_disclosure': 0.25,
            'voting_record_public': 0.20,
            'constituent_responsiveness': 0.20,
            'statement_clarity': 0.15,
            'media_accessibility': 0.10,
            'sponsored_bills_public': 0.10
        }
    
    def calculate_transparency_index(self, politician_id):
        """Calculate 0-100 transparency score"""
        
        scores = {}
        
        # 1. Financial disclosure completeness
        scores['financial_disclosure'] = self._check_financial_disclosure(politician_id)
        
        # 2. Voting record accessibility
        scores['voting_record_public'] = self._check_voting_accessibility(politician_id)
        
        # 3. Constituent responsiveness
        scores['constituent_responsiveness'] = self._measure_responsiveness(politician_id)
        
        # 4. Statement clarity (readability)
        scores['statement_clarity'] = self._measure_clarity(politician_id)
        
        # 5. Media accessibility
        scores['media_accessibility'] = self._measure_media_access(politician_id)
        
        # 6. Bill sponsorship transparency
        scores['sponsored_bills_public'] = self._check_bill_transparency(politician_id)
        
        # Weighted average
        total_score = sum(
            scores[metric] * weight
            for metric, weight in self.weights.items()
        )
        
        return {
            'transparency_index': round(total_score, 2),
            'component_scores': scores,
            'grade': self._score_to_grade(total_score)
        }
    
    def _check_financial_disclosure(self, politician_id):
        """Check if financial disclosures are complete and timely"""
        # Query database for disclosure records
        disclosures = get_financial_disclosures(politician_id)
        
        if not disclosures:
            return 0
        
        # Check completeness
        required_fields = ['assets', 'liabilities', 'income', 'transactions']
        completeness = sum(
            1 for field in required_fields if disclosures.get(field)
        ) / len(required_fields)
        
        # Check timeliness
        from datetime import datetime, timedelta
        is_current = disclosures['date'] > datetime.now() - timedelta(days=365)
        
        score = completeness * 100 if is_current else completeness * 50
        return score
    
    def _check_voting_accessibility(self, politician_id):
        """Check if voting record is easily accessible"""
        votes = get_voting_records(politician_id)
        
        if not votes:
            return 0
        
        # Check if explanations are provided
        explained_votes = sum(1 for v in votes if v.get('explanation'))
        explanation_rate = explained_votes / len(votes)
        
        return explanation_rate * 100
    
    def _measure_responsiveness(self, politician_id):
        """Measure responsiveness to constituent requests"""
        # This would integrate with constituent services data
        response_data = get_constituent_responses(politician_id)
        
        if not response_data:
            return 50  # Default score if no data
        
        # Calculate average response time and rate
        avg_response_time = response_data['avg_response_days']
        response_rate = response_data['response_rate']
        
        # Score: faster responses and higher rate = better
        time_score = max(0, 100 - (avg_response_time * 5))  # Penalty for slow responses
        
        return (time_score * 0.5 + response_rate * 0.5)
    
    def _measure_clarity(self, politician_id):
        """Measure clarity of communications"""
        statements = get_politician_statements(politician_id)
        
        if not statements:
            return 50
        
        import textstat
        
        # Calculate average readability
        readability_scores = []
        for statement in statements:
            score = textstat.flesch_reading_ease(statement['text'])
            readability_scores.append(score)
        
        avg_readability = sum(readability_scores) / len(readability_scores)
        
        # Convert to 0-100 scale (higher is better)
        # Flesch: 0 (hard) to 100 (easy)
        return avg_readability
    
    def _score_to_grade(self, score):
        """Convert numerical score to letter grade"""
        if score >= 90: return 'A'
        elif score >= 80: return 'B'
        elif score >= 70: return 'C'
        elif score >= 60: return 'D'
        else: return 'F'
```

## 3. Consistency Analysis

### 3.1 Voting Consistency

```python
class ConsistencyAnalyzer:
    def calculate_voting_consistency(self, politician_id):
        """
        Measure how consistently a politician votes on similar issues
        """
        votes = get_politician_votes(politician_id)
        
        # Group votes by issue
        from collections import defaultdict
        issue_votes = defaultdict(list)
        
        for vote in votes:
            issue = vote['bill']['primary_subject']
            issue_votes[issue].append(vote)
        
        # Calculate consistency per issue
        issue_consistency = {}
        for issue, votes_list in issue_votes.items():
            if len(votes_list) < 2:
                continue
            
            # Count yes vs no votes
            yes_votes = sum(1 for v in votes_list if v['vote'] == 'Yea')
            no_votes = sum(1 for v in votes_list if v['vote'] == 'Nay')
            
            # Consistency = how often they vote the same way
            total = yes_votes + no_votes
            if total == 0:
                continue
            
            consistency = max(yes_votes, no_votes) / total
            issue_consistency[issue] = consistency
        
        # Overall consistency
        if issue_consistency:
            overall = sum(issue_consistency.values()) / len(issue_consistency)
        else:
            overall = 0
        
        return {
            'overall_consistency': round(overall * 100, 2),
            'by_issue': {k: round(v * 100, 2) for k, v in issue_consistency.items()}
        }
```

### 3.2 Position Change Detection

```python
class PositionChangeDetector:
    def detect_flip_flops(self, politician_id, min_similarity=0.7):
        """
        Detect when politician changes position on similar bills
        """
        votes = get_politician_votes(politician_id)
        
        # Get bill embeddings for similarity
        from sentence_transformers import SentenceTransformer, util
        model = SentenceTransformer('all-mpnet-base-v2')
        
        flip_flops = []
        
        # Compare each pair of votes
        for i, vote1 in enumerate(votes):
            for vote2 in votes[i+1:]:
                # Only compare if votes were different
                if vote1['vote'] == vote2['vote']:
                    continue
                
                # Check if bills are similar
                emb1 = model.encode(vote1['bill']['summary'])
                emb2 = model.encode(vote2['bill']['summary'])
                similarity = util.cos_sim(emb1, emb2).item()
                
                if similarity >= min_similarity:
                    flip_flops.append({
                        'bill_1': vote1['bill'],
                        'bill_2': vote2['bill'],
                        'vote_1': vote1['vote'],
                        'vote_2': vote2['vote'],
                        'similarity': round(similarity, 3),
                        'date_1': vote1['date'],
                        'date_2': vote2['date']
                    })
        
        return {
            'flip_flop_count': len(flip_flops),
            'flip_flops': sorted(flip_flops, key=lambda x: x['similarity'], reverse=True)
        }
```

### 3.3 Statement-Action Alignment

```python
class StatementActionAlignment:
    def measure_alignment(self, politician_id):
        """
        Measure how well politician's votes align with their statements
        """
        statements = get_politician_statements(politician_id)
        votes = get_politician_votes(politician_id)
        
        from sentence_transformers import SentenceTransformer, util
        model = SentenceTransformer('all-mpnet-base-v2')
        
        misalignments = []
        
        for statement in statements:
            # Extract position from statement using sentiment
            statement_position = self._extract_position(statement['text'])
            
            if not statement_position:
                continue
            
            # Find related votes
            statement_emb = model.encode(statement['text'])
            
            for vote in votes:
                # Check if vote is about same topic
                bill_emb = model.encode(vote['bill']['summary'])
                similarity = util.cos_sim(statement_emb, bill_emb).item()
                
                if similarity < 0.5:
                    continue
                
                # Check if vote aligns with statement
                vote_position = 'support' if vote['vote'] == 'Yea' else 'oppose'
                
                if vote_position != statement_position:
                    misalignments.append({
                        'statement': statement,
                        'vote': vote,
                        'similarity': round(similarity, 3)
                    })
        
        total_matches = len(statements) + len(votes) - len(misalignments)
        alignment_rate = 1 - (len(misalignments) / max(1, total_matches))
        
        return {
            'alignment_percentage': round(alignment_rate * 100, 2),
            'misalignments': misalignments
        }
    
    def _extract_position(self, text):
        """Extract support/oppose position from text"""
        support_keywords = ['support', 'favor', 'back', 'endorse', 'agree']
        oppose_keywords = ['oppose', 'against', 'reject', 'disagree']
        
        text_lower = text.lower()
        
        support_count = sum(1 for kw in support_keywords if kw in text_lower)
        oppose_count = sum(1 for kw in oppose_keywords if kw in text_lower)
        
        if support_count > oppose_count:
            return 'support'
        elif oppose_count > support_count:
            return 'oppose'
        else:
            return None
```

## 4. Hate Speech and Toxicity Detection

### 4.1 Toxicity Scoring

```python
from transformers import pipeline

class ToxicityDetector:
    def __init__(self):
        # Use pre-trained toxicity detection model
        self.classifier = pipeline(
            "text-classification",
            model="unitary/toxic-bert",
            return_all_scores=True
        )
    
    def analyze_toxicity(self, text):
        """
        Analyze text for toxic content
        Returns scores for: toxic, severe_toxic, obscene, threat, insult, identity_hate
        """
        results = self.classifier(text)[0]
        
        toxicity_scores = {item['label']: item['score'] for item in results}
        
        # Calculate overall toxicity
        overall_toxicity = max(toxicity_scores.values())
        
        return {
            'overall_toxicity': round(overall_toxicity, 3),
            'is_toxic': overall_toxicity > 0.5,
            'toxicity_breakdown': toxicity_scores,
            'severity': self._categorize_severity(overall_toxicity)
        }
    
    def _categorize_severity(self, score):
        """Categorize toxicity severity"""
        if score < 0.3:
            return 'low'
        elif score < 0.6:
            return 'moderate'
        elif score < 0.8:
            return 'high'
        else:
            return 'severe'
    
    def analyze_politician_toxicity(self, politician_id):
        """Analyze toxicity across all politician communications"""
        statements = get_politician_statements(politician_id)
        tweets = get_politician_tweets(politician_id)
        
        all_texts = [s['text'] for s in statements] + [t['text'] for t in tweets]
        
        toxicity_scores = []
        toxic_count = 0
        
        for text in all_texts:
            result = self.analyze_toxicity(text)
            toxicity_scores.append(result['overall_toxicity'])
            if result['is_toxic']:
                toxic_count += 1
        
        return {
            'avg_toxicity': round(sum(toxicity_scores) / len(toxicity_scores), 3),
            'max_toxicity': round(max(toxicity_scores), 3),
            'toxic_content_percentage': round(toxic_count / len(all_texts) * 100, 2),
            'total_analyzed': len(all_texts)
        }
```

### 4.2 Hate Speech Detection

```python
class HateSpeechDetector:
    def __init__(self):
        self.hate_keywords = {
            'racial': ['racial slur examples'],  # Would use actual slurs
            'religious': ['religious hate terms'],
            'gender': ['sexist terms'],
            'orientation': ['homophobic terms']
        }
    
    def detect_hate_speech(self, text):
        """Detect potential hate speech"""
        # Use transformer model for better detection
        from transformers import pipeline
        
        classifier = pipeline(
            "text-classification",
            model="IMSyPP/hate_speech_en"
        )
        
        result = classifier(text)[0]
        
        return {
            'is_hate_speech': result['label'] == 'hate',
            'confidence': result['score'],
            'text_snippet': text[:100] + '...' if len(text) > 100 else text
        }
```

## 5. Impact Measurement

### 5.1 Constituent Impact Score

```python
class ImpactAnalyzer:
    def calculate_impact_score(self, politician_id):
        """
        Measure politician's impact on their constituency
        """
        # Multiple dimensions of impact
        dimensions = {
            'legislative': self._legislative_impact(politician_id),
            'media': self._media_impact(politician_id),
            'constituent_service': self._constituent_service_impact(politician_id),
            'social_media': self._social_media_impact(politician_id),
            'committee': self._committee_impact(politician_id)
        }
        
        # Weighted average
        weights = {
            'legislative': 0.30,
            'media': 0.20,
            'constituent_service': 0.20,
            'social_media': 0.15,
            'committee': 0.15
        }
        
        total_impact = sum(
            dimensions[dim] * weights[dim]
            for dim in dimensions
        )
        
        return {
            'impact_score': round(total_impact, 2),
            'dimensions': dimensions,
            'percentile': self._calculate_percentile(total_impact, politician_id)
        }
    
    def _legislative_impact(self, politician_id):
        """Measure legislative effectiveness"""
        bills = get_sponsored_bills(politician_id)
        
        if not bills:
            return 0
        
        # Count bills by status
        introduced = len(bills)
        passed_committee = sum(1 for b in bills if b['status'] in ['passed_committee', 'passed_house', 'passed_senate', 'enacted'])
        enacted = sum(1 for b in bills if b['status'] == 'enacted')
        
        # Calculate score
        score = (
            (introduced * 1) +
            (passed_committee * 5) +
            (enacted * 20)
        ) / max(1, introduced)
        
        return min(100, score)
    
    def _media_impact(self, politician_id):
        """Measure media presence and influence"""
        mentions = get_media_mentions(politician_id)
        
        if not mentions:
            return 0
        
        # Weight by source credibility and reach
        weighted_mentions = sum(
            mention['credibility_score'] * mention['reach']
            for mention in mentions
        )
        
        # Normalize to 0-100
        return min(100, weighted_mentions / 1000)
    
    def _constituent_service_impact(self, politician_id):
        """Measure constituent service effectiveness"""
        cases = get_constituent_cases(politician_id)
        
        if not cases:
            return 50  # Default
        
        resolved = sum(1 for c in cases if c['status'] == 'resolved')
        resolution_rate = resolved / len(cases)
        
        return resolution_rate * 100
    
    def _social_media_impact(self, politician_id):
        """Measure social media influence"""
        # Covered in detail in 05-social-media-analysis.md
        social_stats = get_social_media_stats(politician_id)
        
        engagement_rate = social_stats['total_engagement'] / social_stats['followers']
        
        return min(100, engagement_rate * 1000)
    
    def _committee_impact(self, politician_id):
        """Measure committee influence"""
        committees = get_committee_assignments(politician_id)
        
        if not committees:
            return 0
        
        # Weight by committee importance and role
        importance_weights = {
            'chair': 10,
            'ranking_member': 8,
            'member': 5
        }
        
        score = sum(
            importance_weights.get(c['role'], 0) * c['committee_importance']
            for c in committees
        )
        
        return min(100, score)
```

### 5.2 Policy Influence Network

```python
import networkx as nx

class PolicyInfluenceNetwork:
    def build_influence_network(self):
        """Build network graph of policy influence"""
        G = nx.DiGraph()
        
        politicians = get_all_politicians()
        
        for pol in politicians:
            G.add_node(pol['id'], **pol)
        
        # Add edges based on co-sponsorship
        sponsorships = get_all_cosponsorships()
        
        for sponsor, cosponsor in sponsorships:
            if G.has_edge(sponsor, cosponsor):
                G[sponsor][cosponsor]['weight'] += 1
            else:
                G.add_edge(sponsor, cosponsor, weight=1)
        
        return G
    
    def calculate_centrality(self, G):
        """Calculate influence centrality measures"""
        return {
            'degree_centrality': nx.degree_centrality(G),
            'betweenness_centrality': nx.betweenness_centrality(G),
            'eigenvector_centrality': nx.eigenvector_centrality(G),
            'pagerank': nx.pagerank(G)
        }
```

## 6. Comprehensive Politician Profile

### 6.1 Complete Metrics Dashboard

```python
class PoliticianProfileGenerator:
    def __init__(self):
        self.bias_detector = PoliticalBiasDetector()
        self.transparency_scorer = TransparencyScorer()
        self.consistency_analyzer = ConsistencyAnalyzer()
        self.toxicity_detector = ToxicityDetector()
        self.impact_analyzer = ImpactAnalyzer()
    
    def generate_complete_profile(self, politician_id):
        """Generate comprehensive politician profile"""
        
        profile = {
            'politician_id': politician_id,
            'basic_info': self._get_basic_info(politician_id),
            'bias_analysis': None,
            'transparency': None,
            'consistency': None,
            'toxicity': None,
            'impact': None,
            'overall_score': None
        }
        
        # Get all statements for analysis
        statements = get_politician_statements(politician_id)
        all_text = ' '.join([s['text'] for s in statements])
        
        # Run analyses
        profile['bias_analysis'] = self.bias_detector.calculate_bias_score(all_text)
        profile['transparency'] = self.transparency_scorer.calculate_transparency_index(politician_id)
        profile['consistency'] = self.consistency_analyzer.calculate_voting_consistency(politician_id)
        profile['toxicity'] = self.toxicity_detector.analyze_politician_toxicity(politician_id)
        profile['impact'] = self.impact_analyzer.calculate_impact_score(politician_id)
        
        # Calculate overall score (weighted)
        profile['overall_score'] = self._calculate_overall_score(profile)
        
        return profile
    
    def _calculate_overall_score(self, profile):
        """Calculate overall politician score"""
        scores = {
            'transparency': profile['transparency']['transparency_index'],
            'consistency': profile['consistency']['overall_consistency'],
            'low_toxicity': 100 - (profile['toxicity']['avg_toxicity'] * 100),
            'impact': profile['impact']['impact_score']
        }
        
        weights = {
            'transparency': 0.25,
            'consistency': 0.25,
            'low_toxicity': 0.25,
            'impact': 0.25
        }
        
        overall = sum(scores[k] * weights[k] for k in scores)
        
        return {
            'overall': round(overall, 2),
            'components': scores,
            'grade': self._score_to_grade(overall)
        }
    
    def _score_to_grade(self, score):
        if score >= 90: return 'A'
        elif score >= 80: return 'B'
        elif score >= 70: return 'C'
        elif score >= 60: return 'D'
        else: return 'F'
```

## 7. Database Schema for Metrics

```sql
-- Politician metrics table
CREATE TABLE politician_metrics (
    id SERIAL PRIMARY KEY,
    politician_id INTEGER REFERENCES politicians(id),
    calculated_date TIMESTAMP DEFAULT NOW(),
    
    -- Bias
    bias_score DECIMAL(3,2),  -- -1 to 1
    bias_lean VARCHAR(20),
    
    -- Transparency
    transparency_index DECIMAL(5,2),  -- 0 to 100
    transparency_grade CHAR(1),
    
    -- Consistency
    voting_consistency DECIMAL(5,2),  -- 0 to 100
    flip_flop_count INTEGER,
    
    -- Toxicity
    avg_toxicity DECIMAL(3,2),  -- 0 to 1
    toxic_content_pct DECIMAL(5,2),
    
    -- Impact
    impact_score DECIMAL(5,2),  -- 0 to 100
    impact_percentile DECIMAL(5,2),
    
    -- Overall
    overall_score DECIMAL(5,2),
    overall_grade CHAR(1)
);

CREATE INDEX idx_metrics_politician ON politician_metrics(politician_id);
CREATE INDEX idx_metrics_date ON politician_metrics(calculated_date);
```

## 8. References

### Academic Research
1. **"Measuring Political Polarization with Text Analysis"** - Gentzkow et al., 2019
2. **"Detecting Hate Speech on Twitter"** - Davidson et al., 2017
3. **"Congressional Influence and Legislative Effectiveness"** - Volden & Wiseman, 2014

### Tools and Libraries
- **Perspective API**: Google's toxicity detection
- **OpenAI Moderation API**: Content policy violations
- **Detoxify**: Toxicity prediction library

---

**Last Updated**: 2025-10-23
**Next**: [04-hate-speech-toxicity.md](04-hate-speech-toxicity.md)
