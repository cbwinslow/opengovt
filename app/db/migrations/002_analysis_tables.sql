-- Name: DB migration 002 - analysis tables
-- Date: 2025-10-14
-- Description: Create tables for NLP analysis, embeddings, sentiment, bias detection, and consistency tracking

BEGIN;

-- ==============================================================================
-- Bill Embeddings Table
-- ==============================================================================
CREATE TABLE IF NOT EXISTS bill_embeddings (
  id SERIAL PRIMARY KEY,
  bill_id INTEGER NOT NULL REFERENCES bills(id) ON DELETE CASCADE,
  model_name TEXT NOT NULL,
  embedding_vector FLOAT8[] NOT NULL,  -- Array of floats for the vector
  embedding_dim INTEGER NOT NULL,  -- Dimension of the embedding
  text_hash TEXT,  -- Hash of the text that was embedded
  created_at TIMESTAMP DEFAULT now(),
  metadata JSONB,
  UNIQUE(bill_id, model_name)
);

CREATE INDEX idx_bill_embeddings_bill_id ON bill_embeddings(bill_id);
CREATE INDEX idx_bill_embeddings_model ON bill_embeddings(model_name);

-- ==============================================================================
-- Speech/Statement Embeddings Table
-- ==============================================================================
CREATE TABLE IF NOT EXISTS speech_embeddings (
  id SERIAL PRIMARY KEY,
  person_id INTEGER REFERENCES legislators(id) ON DELETE CASCADE,
  speech_id TEXT,  -- External reference to speech/statement
  speech_date TIMESTAMP,
  model_name TEXT NOT NULL,
  embedding_vector FLOAT8[] NOT NULL,
  embedding_dim INTEGER NOT NULL,
  text_hash TEXT,
  created_at TIMESTAMP DEFAULT now(),
  metadata JSONB
);

CREATE INDEX idx_speech_embeddings_person_id ON speech_embeddings(person_id);
CREATE INDEX idx_speech_embeddings_speech_id ON speech_embeddings(speech_id);

-- ==============================================================================
-- Sentiment Analysis Results
-- ==============================================================================
CREATE TABLE IF NOT EXISTS sentiment_analysis (
  id SERIAL PRIMARY KEY,
  text_id INTEGER,  -- Can reference bill_id, speech_id, etc.
  text_type TEXT,  -- 'bill', 'speech', 'statement', etc.
  model_name TEXT NOT NULL,
  compound_score FLOAT,  -- Overall sentiment (-1 to 1)
  positive_score FLOAT,
  negative_score FLOAT,
  neutral_score FLOAT,
  sentiment_label TEXT,  -- 'positive', 'negative', 'neutral'
  confidence FLOAT,
  analyzed_at TIMESTAMP DEFAULT now(),
  text_length INTEGER,
  metadata JSONB
);

CREATE INDEX idx_sentiment_text_id_type ON sentiment_analysis(text_id, text_type);
CREATE INDEX idx_sentiment_label ON sentiment_analysis(sentiment_label);

-- ==============================================================================
-- Named Entity Extraction Results
-- ==============================================================================
CREATE TABLE IF NOT EXISTS extracted_entities (
  id SERIAL PRIMARY KEY,
  text_id INTEGER,
  text_type TEXT,
  entity_text TEXT NOT NULL,
  entity_label TEXT NOT NULL,  -- 'PERSON', 'ORG', 'GPE', 'LAW', etc.
  start_char INTEGER,
  end_char INTEGER,
  confidence FLOAT,
  extracted_at TIMESTAMP DEFAULT now(),
  model_name TEXT
);

CREATE INDEX idx_entities_text_id_type ON extracted_entities(text_id, text_type);
CREATE INDEX idx_entities_label ON extracted_entities(entity_label);
CREATE INDEX idx_entities_text ON extracted_entities(entity_text);

-- ==============================================================================
-- Political Bias Detection Results
-- ==============================================================================
CREATE TABLE IF NOT EXISTS bias_analysis (
  id SERIAL PRIMARY KEY,
  text_id INTEGER,
  text_type TEXT,
  overall_bias TEXT,  -- 'left', 'center-left', 'center', 'center-right', 'right', 'neutral'
  bias_score FLOAT,  -- -1 (left) to 1 (right)
  confidence FLOAT,
  objectivity_score FLOAT,  -- 0 (subjective) to 1 (objective)
  loaded_language_count INTEGER,
  emotional_appeal_count INTEGER,
  analyzed_at TIMESTAMP DEFAULT now(),
  model_name TEXT,
  metadata JSONB
);

CREATE INDEX idx_bias_text_id_type ON bias_analysis(text_id, text_type);
CREATE INDEX idx_bias_overall ON bias_analysis(overall_bias);

-- ==============================================================================
-- Voting Consistency Analysis
-- ==============================================================================
CREATE TABLE IF NOT EXISTS consistency_analysis (
  id SERIAL PRIMARY KEY,
  person_id INTEGER NOT NULL REFERENCES legislators(id) ON DELETE CASCADE,
  analysis_period_start TIMESTAMP,
  analysis_period_end TIMESTAMP,
  overall_consistency FLOAT,  -- 0 to 1
  party_line_voting FLOAT,  -- % votes with party
  bipartisan_score FLOAT,  -- % bipartisan activity
  campaign_alignment FLOAT,  -- Alignment with campaign positions
  total_votes_analyzed INTEGER,
  position_changes_count INTEGER,
  flip_flops_count INTEGER,
  analyzed_at TIMESTAMP DEFAULT now(),
  metadata JSONB
);

CREATE INDEX idx_consistency_person_id ON consistency_analysis(person_id);
CREATE INDEX idx_consistency_period ON consistency_analysis(analysis_period_start, analysis_period_end);

-- ==============================================================================
-- Issue Consistency by Topic
-- ==============================================================================
CREATE TABLE IF NOT EXISTS issue_consistency (
  id SERIAL PRIMARY KEY,
  person_id INTEGER NOT NULL REFERENCES legislators(id) ON DELETE CASCADE,
  issue_topic TEXT NOT NULL,
  consistency_score FLOAT,  -- 0 to 1
  vote_count INTEGER,
  analyzed_at TIMESTAMP DEFAULT now()
);

CREATE INDEX idx_issue_consistency_person ON issue_consistency(person_id);
CREATE INDEX idx_issue_consistency_topic ON issue_consistency(issue_topic);

-- ==============================================================================
-- Position Changes Tracking
-- ==============================================================================
CREATE TABLE IF NOT EXISTS position_changes (
  id SERIAL PRIMARY KEY,
  person_id INTEGER NOT NULL REFERENCES legislators(id) ON DELETE CASCADE,
  subject TEXT,
  from_position TEXT,
  to_position TEXT,
  change_date TIMESTAMP,
  bill_id INTEGER REFERENCES bills(id),
  is_flip_flop BOOLEAN DEFAULT FALSE,
  recorded_at TIMESTAMP DEFAULT now()
);

CREATE INDEX idx_position_changes_person ON position_changes(person_id);
CREATE INDEX idx_position_changes_subject ON position_changes(subject);
CREATE INDEX idx_position_changes_flip_flop ON position_changes(is_flip_flop) WHERE is_flip_flop = TRUE;

-- ==============================================================================
-- Bill Similarity Matrix (for finding similar bills)
-- ==============================================================================
CREATE TABLE IF NOT EXISTS bill_similarities (
  id SERIAL PRIMARY KEY,
  bill_id_1 INTEGER NOT NULL REFERENCES bills(id) ON DELETE CASCADE,
  bill_id_2 INTEGER NOT NULL REFERENCES bills(id) ON DELETE CASCADE,
  similarity_score FLOAT NOT NULL,  -- 0 to 1
  model_name TEXT,
  calculated_at TIMESTAMP DEFAULT now(),
  CHECK (bill_id_1 < bill_id_2),  -- Ensure we don't duplicate pairs
  UNIQUE(bill_id_1, bill_id_2, model_name)
);

CREATE INDEX idx_bill_similarities_score ON bill_similarities(similarity_score DESC);
CREATE INDEX idx_bill_similarities_bill1 ON bill_similarities(bill_id_1);
CREATE INDEX idx_bill_similarities_bill2 ON bill_similarities(bill_id_2);

-- ==============================================================================
-- Text Complexity Analysis
-- ==============================================================================
CREATE TABLE IF NOT EXISTS text_complexity (
  id SERIAL PRIMARY KEY,
  text_id INTEGER,
  text_type TEXT,
  sentence_count INTEGER,
  word_count INTEGER,
  avg_sentence_length FLOAT,
  complex_word_count INTEGER,
  lexical_diversity FLOAT,
  readability_score FLOAT,  -- Various readability metrics
  analyzed_at TIMESTAMP DEFAULT now(),
  model_name TEXT
);

CREATE INDEX idx_text_complexity_text_id_type ON text_complexity(text_id, text_type);

-- ==============================================================================
-- Hate Speech / Toxic Language Detection
-- ==============================================================================
CREATE TABLE IF NOT EXISTS toxicity_analysis (
  id SERIAL PRIMARY KEY,
  text_id INTEGER,
  text_type TEXT,
  toxicity_score FLOAT,  -- 0 to 1
  severe_toxicity_score FLOAT,
  identity_attack_score FLOAT,
  insult_score FLOAT,
  profanity_score FLOAT,
  threat_score FLOAT,
  is_toxic BOOLEAN,
  analyzed_at TIMESTAMP DEFAULT now(),
  model_name TEXT
);

CREATE INDEX idx_toxicity_text_id_type ON toxicity_analysis(text_id, text_type);
CREATE INDEX idx_toxicity_is_toxic ON toxicity_analysis(is_toxic) WHERE is_toxic = TRUE;

-- ==============================================================================
-- Politician Comparison Matrix
-- ==============================================================================
CREATE TABLE IF NOT EXISTS politician_comparisons (
  id SERIAL PRIMARY KEY,
  person_id_1 INTEGER NOT NULL REFERENCES legislators(id) ON DELETE CASCADE,
  person_id_2 INTEGER NOT NULL REFERENCES legislators(id) ON DELETE CASCADE,
  agreement_rate FLOAT,  -- % of votes where they agreed
  common_votes_count INTEGER,
  ideological_distance FLOAT,  -- Based on voting patterns
  compared_at TIMESTAMP DEFAULT now(),
  CHECK (person_id_1 < person_id_2),
  UNIQUE(person_id_1, person_id_2)
);

CREATE INDEX idx_politician_comparisons_agreement ON politician_comparisons(agreement_rate DESC);

-- ==============================================================================
-- Views for Common Queries
-- ==============================================================================

-- View: Latest sentiment by bill
CREATE OR REPLACE VIEW latest_bill_sentiment AS
SELECT DISTINCT ON (text_id)
  text_id AS bill_id,
  sentiment_label,
  compound_score,
  confidence,
  analyzed_at
FROM sentiment_analysis
WHERE text_type = 'bill'
ORDER BY text_id, analyzed_at DESC;

-- View: Latest bias analysis by bill
CREATE OR REPLACE VIEW latest_bill_bias AS
SELECT DISTINCT ON (text_id)
  text_id AS bill_id,
  overall_bias,
  bias_score,
  objectivity_score,
  analyzed_at
FROM bias_analysis
WHERE text_type = 'bill'
ORDER BY text_id, analyzed_at DESC;

-- View: Politician consistency summary
CREATE OR REPLACE VIEW politician_consistency_summary AS
SELECT
  l.id AS person_id,
  l.name,
  l.bioguide,
  l.current_party,
  l.state,
  c.overall_consistency,
  c.party_line_voting,
  c.bipartisan_score,
  c.position_changes_count,
  c.flip_flops_count,
  c.analyzed_at
FROM legislators l
LEFT JOIN LATERAL (
  SELECT *
  FROM consistency_analysis
  WHERE person_id = l.id
  ORDER BY analyzed_at DESC
  LIMIT 1
) c ON TRUE;

-- View: Most similar bills
CREATE OR REPLACE VIEW top_similar_bills AS
SELECT
  bs.bill_id_1,
  bs.bill_id_2,
  bs.similarity_score,
  b1.bill_number AS bill_1_number,
  b1.title AS bill_1_title,
  b2.bill_number AS bill_2_number,
  b2.title AS bill_2_title
FROM bill_similarities bs
JOIN bills b1 ON bs.bill_id_1 = b1.id
JOIN bills b2 ON bs.bill_id_2 = b2.id
WHERE bs.similarity_score > 0.7
ORDER BY bs.similarity_score DESC;

COMMIT;

-- ==============================================================================
-- Notes:
-- ==============================================================================
-- 1. PostgreSQL doesn't have native vector indexing. For production, consider:
--    - pgvector extension for efficient vector similarity search
--    - External vector databases like Pinecone, Milvus, or Weaviate
--
-- 2. The FLOAT8[] type is used for embeddings. For larger scale:
--    - Consider storing embeddings in a separate vector database
--    - Use pgvector extension with appropriate index types (ivfflat, hnsw)
--
-- 3. All analysis tables have metadata JSONB columns for extensibility
--
-- 4. Indexes are created on foreign keys and commonly queried columns
--
-- 5. Views provide convenient access to latest analysis results
