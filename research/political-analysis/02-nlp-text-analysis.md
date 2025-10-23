# NLP and Text Analysis for Political Documents

## Overview

This document covers Natural Language Processing (NLP), text analysis techniques, and machine learning models used to analyze political documents, speeches, and communications.

## 1. Text Processing Pipeline

### 1.1 Standard NLP Pipeline

```
Raw Text → Tokenization → Normalization → POS Tagging → NER → Parsing → Analysis
```

### 1.2 Implementation with spaCy

```python
import spacy
from spacy.tokens import Doc

# Load model
nlp = spacy.load("en_core_web_lg")

class PoliticalTextProcessor:
    def __init__(self):
        self.nlp = spacy.load("en_core_web_lg")
        # Add custom components
        self.nlp.add_pipe("sentencizer")
    
    def process_bill(self, bill_text):
        """Process a bill's text with full NLP pipeline"""
        doc = self.nlp(bill_text)
        
        return {
            'tokens': [token.text for token in doc],
            'lemmas': [token.lemma_ for token in doc],
            'pos_tags': [(token.text, token.pos_) for token in doc],
            'entities': [(ent.text, ent.label_) for ent in doc.ents],
            'sentences': [sent.text for sent in doc.sents],
            'noun_chunks': [chunk.text for chunk in doc.noun_chunks]
        }
    
    def extract_political_entities(self, doc):
        """Extract politician names, organizations, legislation"""
        entities = {
            'people': [],
            'organizations': [],
            'laws': [],
            'locations': [],
            'dates': []
        }
        
        for ent in doc.ents:
            if ent.label_ == 'PERSON':
                entities['people'].append(ent.text)
            elif ent.label_ in ['ORG', 'FAC']:
                entities['organizations'].append(ent.text)
            elif ent.label_ == 'LAW':
                entities['laws'].append(ent.text)
            elif ent.label_ in ['GPE', 'LOC']:
                entities['locations'].append(ent.text)
            elif ent.label_ == 'DATE':
                entities['dates'].append(ent.text)
        
        return entities
```

### 1.3 Custom Political NER

Train custom NER for political entities:

```python
import spacy
from spacy.training import Example

def train_political_ner():
    """Train custom NER for political entities"""
    
    # Training data
    TRAIN_DATA = [
        ("Senator Elizabeth Warren introduced the bill.", {
            "entities": [(0, 23, "POLITICIAN"), (37, 45, "LEGISLATIVE_ACTION")]
        }),
        ("The Healthcare Reform Act of 2024 was signed into law.", {
            "entities": [(4, 34, "LEGISLATION")]
        }),
        ("Representative from California's 12th district voted yes.", {
            "entities": [(0, 14, "TITLE"), (20, 43, "DISTRICT")]
        })
    ]
    
    # Create blank model
    nlp = spacy.blank("en")
    ner = nlp.add_pipe("ner")
    
    # Add labels
    for _, annotations in TRAIN_DATA:
        for ent in annotations.get("entities"):
            ner.add_label(ent[2])
    
    # Train
    optimizer = nlp.begin_training()
    for epoch in range(30):
        losses = {}
        for text, annotations in TRAIN_DATA:
            doc = nlp.make_doc(text)
            example = Example.from_dict(doc, annotations)
            nlp.update([example], drop=0.5, losses=losses)
        print(f"Epoch {epoch}, Loss: {losses['ner']}")
    
    return nlp
```

## 2. Sentence Transformers and Embeddings

### 2.1 Why Embeddings for Political Text?

Embeddings capture semantic meaning:
- Similar bills have similar embeddings
- Find related legislation by meaning, not keywords
- Cluster bills by topic
- Detect plagiarism or copy-paste legislation

### 2.2 Popular Embedding Models

| Model | Dimensions | Best For | Speed |
|-------|-----------|----------|-------|
| all-MiniLM-L6-v2 | 384 | General purpose, fast | Very Fast |
| all-mpnet-base-v2 | 768 | Higher quality | Medium |
| legal-bert-base-uncased | 768 | Legal/legislative text | Medium |
| sentence-t5-base | 768 | Long documents | Slow |

### 2.3 Implementation

```python
from sentence_transformers import SentenceTransformer, util
import numpy as np

class BillEmbeddingEngine:
    def __init__(self, model_name='all-mpnet-base-v2'):
        self.model = SentenceTransformer(model_name)
        self.embeddings_cache = {}
    
    def embed_bill(self, bill_id, bill_text):
        """Generate embedding for a bill"""
        # Truncate to max length
        max_length = 5000  # Characters
        text = bill_text[:max_length]
        
        embedding = self.model.encode(
            text,
            convert_to_tensor=True,
            show_progress_bar=False
        )
        
        self.embeddings_cache[bill_id] = embedding
        return embedding
    
    def find_similar_bills(self, query_bill_id, top_k=10):
        """Find most similar bills using cosine similarity"""
        query_embedding = self.embeddings_cache[query_bill_id]
        
        similarities = []
        for bill_id, embedding in self.embeddings_cache.items():
            if bill_id != query_bill_id:
                similarity = util.cos_sim(query_embedding, embedding).item()
                similarities.append((bill_id, similarity))
        
        # Sort by similarity
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]
    
    def cluster_bills(self, n_clusters=10):
        """Cluster bills by topic using embeddings"""
        from sklearn.cluster import KMeans
        
        # Get all embeddings
        bill_ids = list(self.embeddings_cache.keys())
        embeddings = np.array([
            self.embeddings_cache[bid].cpu().numpy() 
            for bid in bill_ids
        ])
        
        # Cluster
        kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        labels = kmeans.fit_predict(embeddings)
        
        # Group by cluster
        clusters = {}
        for bill_id, label in zip(bill_ids, labels):
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(bill_id)
        
        return clusters
```

### 2.4 Batch Processing for Performance

```python
def batch_embed_bills(bills, batch_size=32):
    """Efficiently embed many bills at once"""
    model = SentenceTransformer('all-mpnet-base-v2')
    
    # Prepare texts
    texts = [bill['summary'] for bill in bills]
    
    # Encode in batches
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=True,
        convert_to_numpy=True
    )
    
    # Store in database
    for bill, embedding in zip(bills, embeddings):
        store_embedding(bill['id'], embedding)
```

## 3. BERT and Transformer Models

### 3.1 BERT for Political Text Classification

```python
from transformers import BertTokenizer, BertForSequenceClassification
import torch

class PoliticalBiasClassifier:
    def __init__(self):
        self.tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')
        self.model = BertForSequenceClassification.from_pretrained(
            'bert-base-uncased',
            num_labels=3  # Left, Center, Right
        )
    
    def predict_bias(self, text):
        """Classify political bias of text"""
        # Tokenize
        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            max_length=512,
            truncation=True,
            padding=True
        )
        
        # Predict
        with torch.no_grad():
            outputs = self.model(**inputs)
            predictions = torch.nn.functional.softmax(outputs.logits, dim=-1)
        
        labels = ['Left', 'Center', 'Right']
        scores = predictions[0].tolist()
        
        return {label: score for label, score in zip(labels, scores)}
```

### 3.2 Fine-tuning BERT on Political Data

```python
from transformers import Trainer, TrainingArguments
from datasets import Dataset

def fine_tune_political_bert(training_data):
    """Fine-tune BERT on labeled political texts"""
    
    # Prepare dataset
    dataset = Dataset.from_dict({
        'text': [item['text'] for item in training_data],
        'label': [item['label'] for item in training_data]
    })
    
    # Tokenize
    def tokenize_function(examples):
        return tokenizer(
            examples['text'],
            padding='max_length',
            truncation=True,
            max_length=512
        )
    
    tokenized_dataset = dataset.map(tokenize_function, batched=True)
    
    # Training arguments
    training_args = TrainingArguments(
        output_dir='./political_bert',
        num_train_epochs=3,
        per_device_train_batch_size=16,
        learning_rate=2e-5,
        warmup_steps=500,
        weight_decay=0.01,
        logging_dir='./logs',
        logging_steps=10
    )
    
    # Train
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_dataset
    )
    
    trainer.train()
    return trainer.model
```

### 3.3 Domain-Specific Models

**LegalBERT**: Pre-trained on legal documents

```python
from transformers import AutoTokenizer, AutoModel

tokenizer = AutoTokenizer.from_pretrained("nlpaueb/legal-bert-base-uncased")
model = AutoModel.from_pretrained("nlpaueb/legal-bert-base-uncased")

# Use for legislative text
bill_text = "An Act to amend the Internal Revenue Code..."
inputs = tokenizer(bill_text, return_tensors="pt")
outputs = model(**inputs)
```

**PoliBERT**: Fine-tuned on political manifestos

```python
# Hypothetical - would need to be trained
from transformers import BertForSequenceClassification

model = BertForSequenceClassification.from_pretrained(
    "path/to/polibert",
    num_labels=8  # Political ideologies
)
```

## 4. Named Entity Recognition (NER)

### 4.1 Political Entity Types

- **POLITICIAN**: Names of politicians
- **PARTY**: Political parties
- **LEGISLATION**: Bill names, acts
- **COMMITTEE**: Congressional committees
- **DISTRICT**: Geographic districts
- **VOTING_RECORD**: Vote references
- **POLICY_AREA**: Issue domains

### 4.2 Advanced NER with Transformers

```python
from transformers import pipeline

class PoliticalNER:
    def __init__(self):
        self.ner = pipeline(
            "ner",
            model="dslim/bert-base-NER",
            aggregation_strategy="simple"
        )
    
    def extract_entities(self, text):
        """Extract all entities from political text"""
        entities = self.ner(text)
        
        # Post-process
        processed = []
        for entity in entities:
            processed.append({
                'text': entity['word'],
                'label': entity['entity_group'],
                'score': entity['score'],
                'start': entity['start'],
                'end': entity['end']
            })
        
        return processed
    
    def extract_politician_mentions(self, text):
        """Specifically extract politician names"""
        entities = self.extract_entities(text)
        politicians = [
            e for e in entities 
            if e['label'] == 'PER' and self._is_politician(e['text'])
        ]
        return politicians
    
    def _is_politician(self, name):
        """Check if entity is a known politician"""
        # Query database or use list
        known_politicians = load_politician_database()
        return name in known_politicians
```

## 5. Topic Modeling

### 5.1 Latent Dirichlet Allocation (LDA)

```python
from gensim import corpora, models
from gensim.models import CoherenceModel
import nltk
from nltk.corpus import stopwords

class BillTopicModeler:
    def __init__(self, num_topics=20):
        self.num_topics = num_topics
        self.stop_words = set(stopwords.words('english'))
        # Add political stopwords
        self.stop_words.update(['act', 'bill', 'section', 'amendment'])
    
    def preprocess(self, texts):
        """Preprocess bill texts for topic modeling"""
        processed = []
        for text in texts:
            # Tokenize
            tokens = nltk.word_tokenize(text.lower())
            # Remove stopwords and short words
            tokens = [
                t for t in tokens 
                if t not in self.stop_words and len(t) > 3
            ]
            processed.append(tokens)
        return processed
    
    def train_lda(self, bills):
        """Train LDA topic model"""
        # Preprocess
        texts = [bill['summary'] for bill in bills]
        processed_texts = self.preprocess(texts)
        
        # Create dictionary and corpus
        dictionary = corpora.Dictionary(processed_texts)
        corpus = [dictionary.doc2bow(text) for text in processed_texts]
        
        # Train LDA
        lda_model = models.LdaMulticore(
            corpus=corpus,
            id2word=dictionary,
            num_topics=self.num_topics,
            random_state=42,
            passes=10,
            workers=4
        )
        
        # Evaluate coherence
        coherence_model = CoherenceModel(
            model=lda_model,
            texts=processed_texts,
            dictionary=dictionary,
            coherence='c_v'
        )
        coherence_score = coherence_model.get_coherence()
        
        print(f"Coherence Score: {coherence_score}")
        
        return lda_model, dictionary
    
    def get_bill_topics(self, lda_model, dictionary, bill_text):
        """Get topic distribution for a bill"""
        processed = self.preprocess([bill_text])[0]
        bow = dictionary.doc2bow(processed)
        topics = lda_model.get_document_topics(bow)
        return sorted(topics, key=lambda x: x[1], reverse=True)
```

### 5.2 BERTopic for Modern Topic Modeling

```python
from bertopic import BERTopic
from sentence_transformers import SentenceTransformer

class ModernTopicModeler:
    def __init__(self):
        # Use sentence transformer for embeddings
        embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        self.topic_model = BERTopic(
            embedding_model=embedding_model,
            nr_topics=20,
            min_topic_size=10
        )
    
    def fit_bills(self, bills):
        """Fit topic model on bills"""
        texts = [bill['summary'] for bill in bills]
        topics, probs = self.topic_model.fit_transform(texts)
        
        return topics, probs
    
    def get_topic_info(self):
        """Get information about discovered topics"""
        return self.topic_model.get_topic_info()
    
    def visualize_topics(self):
        """Create interactive topic visualization"""
        return self.topic_model.visualize_topics()
```

## 6. Sentiment Analysis for Political Text

### 6.1 VADER for Political Sentiment

```python
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

class PoliticalSentimentAnalyzer:
    def __init__(self):
        self.vader = SentimentIntensityAnalyzer()
        # Add political lexicon
        self.add_political_words()
    
    def add_political_words(self):
        """Add political-specific sentiment words"""
        political_words = {
            'gridlock': -2.0,
            'bipartisan': 2.0,
            'partisan': -1.5,
            'compromise': 1.5,
            'obstruction': -2.5,
            'reform': 1.0,
            'crisis': -2.0,
            'scandal': -3.0
        }
        self.vader.lexicon.update(political_words)
    
    def analyze_bill(self, bill_text):
        """Analyze sentiment of bill text"""
        scores = self.vader.polarity_scores(bill_text)
        
        return {
            'positive': scores['pos'],
            'negative': scores['neg'],
            'neutral': scores['neu'],
            'compound': scores['compound'],
            'sentiment': self._classify_sentiment(scores['compound'])
        }
    
    def _classify_sentiment(self, compound_score):
        """Classify overall sentiment"""
        if compound_score >= 0.05:
            return 'positive'
        elif compound_score <= -0.05:
            return 'negative'
        else:
            return 'neutral'
    
    def analyze_speech(self, speech_text):
        """Analyze political speech sentiment"""
        # Split into sentences
        sentences = nltk.sent_tokenize(speech_text)
        
        sentiments = []
        for sentence in sentences:
            sentiment = self.analyze_bill(sentence)
            sentiments.append(sentiment)
        
        # Aggregate
        avg_compound = np.mean([s['compound'] for s in sentiments])
        
        return {
            'sentence_sentiments': sentiments,
            'overall_compound': avg_compound,
            'overall_sentiment': self._classify_sentiment(avg_compound)
        }
```

### 6.2 Transformer-based Sentiment

```python
from transformers import pipeline

class AdvancedSentimentAnalyzer:
    def __init__(self):
        self.sentiment_pipeline = pipeline(
            "sentiment-analysis",
            model="distilbert-base-uncased-finetuned-sst-2-english"
        )
    
    def analyze(self, text):
        """Deep learning sentiment analysis"""
        # Split long texts
        max_length = 512
        chunks = [text[i:i+max_length] for i in range(0, len(text), max_length)]
        
        results = []
        for chunk in chunks:
            result = self.sentiment_pipeline(chunk)[0]
            results.append(result)
        
        # Aggregate
        avg_score = np.mean([r['score'] for r in results])
        majority_label = max(set([r['label'] for r in results]), 
                            key=[r['label'] for r in results].count)
        
        return {
            'label': majority_label,
            'score': avg_score,
            'chunk_results': results
        }
```

## 7. Text Complexity and Readability

### 7.1 Readability Metrics

```python
import textstat

class BillReadabilityAnalyzer:
    def analyze(self, bill_text):
        """Calculate readability metrics for a bill"""
        return {
            'flesch_reading_ease': textstat.flesch_reading_ease(bill_text),
            'flesch_kincaid_grade': textstat.flesch_kincaid_grade(bill_text),
            'smog_index': textstat.smog_index(bill_text),
            'coleman_liau_index': textstat.coleman_liau_index(bill_text),
            'automated_readability_index': textstat.automated_readability_index(bill_text),
            'dale_chall_readability_score': textstat.dale_chall_readability_score(bill_text),
            'difficult_words': textstat.difficult_words(bill_text),
            'linsear_write_formula': textstat.linsear_write_formula(bill_text),
            'gunning_fog': textstat.gunning_fog(bill_text),
            'text_standard': textstat.text_standard(bill_text)
        }
    
    def interpret_scores(self, metrics):
        """Interpret readability scores"""
        fre = metrics['flesch_reading_ease']
        
        if fre >= 90:
            level = "Very Easy (5th grade)"
        elif fre >= 80:
            level = "Easy (6th grade)"
        elif fre >= 70:
            level = "Fairly Easy (7th grade)"
        elif fre >= 60:
            level = "Standard (8th-9th grade)"
        elif fre >= 50:
            level = "Fairly Difficult (10th-12th grade)"
        elif fre >= 30:
            level = "Difficult (College)"
        else:
            level = "Very Difficult (College graduate)"
        
        return {
            'reading_level': level,
            'recommended_age': metrics['flesch_kincaid_grade'] + 5
        }
```

## 8. Key Phrase Extraction

### 8.1 Using spaCy

```python
from spacy.lang.en import English
import pytextrank

class KeyPhraseExtractor:
    def __init__(self):
        self.nlp = spacy.load("en_core_web_lg")
        # Add PyTextRank
        self.nlp.add_pipe("textrank")
    
    def extract_phrases(self, text, limit=10):
        """Extract key phrases from political text"""
        doc = self.nlp(text)
        
        phrases = []
        for phrase in doc._.phrases[:limit]:
            phrases.append({
                'text': phrase.text,
                'rank': phrase.rank,
                'count': phrase.count
            })
        
        return phrases
```

### 8.2 Using YAKE

```python
import yake

class YAKEPhraseExtractor:
    def __init__(self):
        self.kw_extractor = yake.KeywordExtractor(
            lan="en",
            n=3,  # Max n-gram size
            dedupLim=0.9,
            top=20,
            features=None
        )
    
    def extract(self, text):
        """Extract keywords using YAKE"""
        keywords = self.kw_extractor.extract_keywords(text)
        
        return [
            {'phrase': kw, 'score': score}
            for kw, score in keywords
        ]
```

## 9. Real-World Applications

### 9.1 Bill Similarity Pipeline

```python
class BillSimilarityPipeline:
    def __init__(self):
        self.embedder = SentenceTransformer('all-mpnet-base-v2')
        self.nlp = spacy.load("en_core_web_lg")
    
    def process_and_compare(self, bill1, bill2):
        """Complete comparison of two bills"""
        
        # 1. Embedding similarity
        emb1 = self.embedder.encode(bill1['text'])
        emb2 = self.embedder.encode(bill2['text'])
        semantic_sim = util.cos_sim(emb1, emb2).item()
        
        # 2. Entity overlap
        doc1 = self.nlp(bill1['text'])
        doc2 = self.nlp(bill2['text'])
        
        entities1 = set([ent.text for ent in doc1.ents])
        entities2 = set([ent.text for ent in doc2.ents])
        
        entity_overlap = len(entities1 & entities2) / len(entities1 | entities2)
        
        # 3. Topic similarity (simplified)
        # Would use topic model in practice
        
        return {
            'semantic_similarity': semantic_sim,
            'entity_overlap': entity_overlap,
            'overall_similarity': (semantic_sim + entity_overlap) / 2
        }
```

### 9.2 Politician Text Analysis

```python
class PoliticianTextAnalysis:
    def __init__(self):
        self.sentiment_analyzer = PoliticalSentimentAnalyzer()
        self.readability = BillReadabilityAnalyzer()
        self.ner = PoliticalNER()
    
    def analyze_politician_output(self, politician_id, time_period='1year'):
        """Comprehensive analysis of politician's written output"""
        
        # Fetch all texts (bills, speeches, tweets)
        texts = fetch_politician_texts(politician_id, time_period)
        
        results = {
            'total_documents': len(texts),
            'avg_sentiment': 0,
            'avg_readability': 0,
            'common_topics': [],
            'mentioned_entities': {}
        }
        
        sentiments = []
        readability_scores = []
        all_entities = []
        
        for text in texts:
            # Sentiment
            sentiment = self.sentiment_analyzer.analyze_bill(text)
            sentiments.append(sentiment['compound'])
            
            # Readability
            readability = self.readability.analyze(text)
            readability_scores.append(readability['flesch_reading_ease'])
            
            # Entities
            entities = self.ner.extract_entities(text)
            all_entities.extend(entities)
        
        results['avg_sentiment'] = np.mean(sentiments)
        results['avg_readability'] = np.mean(readability_scores)
        results['mentioned_entities'] = self._count_entities(all_entities)
        
        return results
    
    def _count_entities(self, entities):
        """Count and rank entities"""
        from collections import Counter
        entity_texts = [e['text'] for e in entities]
        return dict(Counter(entity_texts).most_common(20))
```

## 10. References

### Libraries
- **spaCy**: https://spacy.io/
- **sentence-transformers**: https://www.sbert.net/
- **Hugging Face Transformers**: https://huggingface.co/transformers/
- **Gensim**: https://radimrehurek.com/gensim/
- **BERTopic**: https://maartengr.github.io/BERTopic/
- **YAKE**: https://github.com/LIAAD/yake

### Academic Papers
1. **"BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding"** - Devlin et al., 2019
2. **"Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks"** - Reimers & Gurevych, 2019
3. **"Political Ideology Detection Using Recursive Neural Networks"** - Iyyer et al., 2014
4. **"Detecting Framing Bias in Online News"** - Card et al., 2015

### Datasets
- **Congressional Bills**: https://www.congress.gov/
- **Political Manifestos**: https://manifesto-project.wzb.eu/
- **Political Speeches**: https://www.presidency.ucsb.edu/
- **Legislative Texts**: https://www.govinfo.gov/

---

**Last Updated**: 2025-10-23
**Next**: [03-political-metrics.md](03-political-metrics.md)
