# SQL Query Templates and Views

This document provides common SQL queries and templates for accessing analysis data.

## Table of Contents
- [Sentiment Analysis Queries](#sentiment-analysis-queries)
- [Entity Extraction Queries](#entity-extraction-queries)
- [Bias Detection Queries](#bias-detection-queries)
- [Consistency Analysis Queries](#consistency-analysis-queries)
- [Similarity Search Queries](#similarity-search-queries)
- [Complex Analysis Queries](#complex-analysis-queries)
- [Performance Optimization](#performance-optimization)

---

## Sentiment Analysis Queries

### Get Bills by Sentiment

```sql
-- Positive bills
SELECT
    b.bill_number,
    b.title,
    s.compound_score,
    s.sentiment_label
FROM bills b
JOIN sentiment_analysis s ON b.id = s.text_id AND s.text_type = 'bill'
WHERE s.sentiment_label = 'positive'
ORDER BY s.compound_score DESC
LIMIT 20;

-- Negative bills
SELECT
    b.bill_number,
    b.title,
    s.compound_score,
    s.sentiment_label
FROM bills b
JOIN sentiment_analysis s ON b.id = s.text_id AND s.text_type = 'bill'
WHERE s.sentiment_label = 'negative'
ORDER BY s.compound_score ASC
LIMIT 20;

-- Most polarized bills (extreme sentiment)
SELECT
    b.bill_number,
    b.title,
    s.compound_score,
    s.sentiment_label,
    s.confidence
FROM bills b
JOIN sentiment_analysis s ON b.id = s.text_id AND s.text_type = 'bill'
WHERE ABS(s.compound_score) > 0.5
ORDER BY ABS(s.compound_score) DESC
LIMIT 20;
```

### Aggregate Sentiment by Congress/Chamber

```sql
-- Average sentiment by congress
SELECT
    b.congress,
    COUNT(*) as bill_count,
    AVG(s.compound_score) as avg_sentiment,
    SUM(CASE WHEN s.sentiment_label = 'positive' THEN 1 ELSE 0 END) as positive_count,
    SUM(CASE WHEN s.sentiment_label = 'negative' THEN 1 ELSE 0 END) as negative_count,
    SUM(CASE WHEN s.sentiment_label = 'neutral' THEN 1 ELSE 0 END) as neutral_count
FROM bills b
JOIN sentiment_analysis s ON b.id = s.text_id AND s.text_type = 'bill'
GROUP BY b.congress
ORDER BY b.congress DESC;

-- Average sentiment by chamber
SELECT
    b.chamber,
    COUNT(*) as bill_count,
    AVG(s.compound_score) as avg_sentiment,
    STDDEV(s.compound_score) as sentiment_stddev
FROM bills b
JOIN sentiment_analysis s ON b.id = s.text_id AND s.text_type = 'bill'
GROUP BY b.chamber;
```

---

## Entity Extraction Queries

### Find Bills Mentioning Specific People

```sql
-- Bills mentioning a specific person
SELECT DISTINCT
    b.bill_number,
    b.title,
    b.introduced_date,
    ee.entity_text
FROM bills b
JOIN extracted_entities ee ON b.id = ee.text_id AND ee.text_type = 'bill'
WHERE ee.entity_label = 'PERSON'
  AND ee.entity_text ILIKE '%Biden%'
ORDER BY b.introduced_date DESC;
```

### Most Frequently Mentioned Entities

```sql
-- Top people mentioned in bills
SELECT
    ee.entity_text,
    COUNT(*) as mention_count,
    COUNT(DISTINCT ee.text_id) as bill_count
FROM extracted_entities ee
WHERE ee.entity_label = 'PERSON'
  AND ee.text_type = 'bill'
GROUP BY ee.entity_text
HAVING COUNT(*) > 5
ORDER BY mention_count DESC
LIMIT 20;

-- Top organizations
SELECT
    ee.entity_text,
    COUNT(*) as mention_count,
    COUNT(DISTINCT ee.text_id) as bill_count
FROM extracted_entities ee
WHERE ee.entity_label IN ('ORG', 'NORP')
  AND ee.text_type = 'bill'
GROUP BY ee.entity_text
HAVING COUNT(*) > 5
ORDER BY mention_count DESC
LIMIT 20;

-- Top locations/GPEs
SELECT
    ee.entity_text,
    COUNT(*) as mention_count
FROM extracted_entities ee
WHERE ee.entity_label IN ('GPE', 'LOC')
  AND ee.text_type = 'bill'
GROUP BY ee.entity_text
ORDER BY mention_count DESC
LIMIT 20;
```

### Entity Co-occurrence

```sql
-- Find entities that frequently appear together in bills
WITH entity_pairs AS (
    SELECT
        e1.text_id,
        e1.entity_text as entity1,
        e2.entity_text as entity2
    FROM extracted_entities e1
    JOIN extracted_entities e2 ON e1.text_id = e2.text_id
    WHERE e1.entity_label = 'PERSON'
      AND e2.entity_label = 'ORG'
      AND e1.entity_text < e2.entity_text  -- Avoid duplicates
)
SELECT
    entity1,
    entity2,
    COUNT(*) as co_occurrence_count
FROM entity_pairs
GROUP BY entity1, entity2
HAVING COUNT(*) >= 3
ORDER BY co_occurrence_count DESC
LIMIT 20;
```

---

## Bias Detection Queries

### Find Politically Biased Bills

```sql
-- Left-leaning bills
SELECT
    b.bill_number,
    b.title,
    ba.overall_bias,
    ba.bias_score,
    ba.objectivity_score
FROM bills b
JOIN bias_analysis ba ON b.id = ba.text_id AND ba.text_type = 'bill'
WHERE ba.overall_bias IN ('left', 'center-left')
ORDER BY ba.bias_score ASC
LIMIT 20;

-- Right-leaning bills
SELECT
    b.bill_number,
    b.title,
    ba.overall_bias,
    ba.bias_score,
    ba.objectivity_score
FROM bills b
JOIN bias_analysis ba ON b.id = ba.text_id AND ba.text_type = 'bill'
WHERE ba.overall_bias IN ('right', 'center-right')
ORDER BY ba.bias_score DESC
LIMIT 20;

-- Most objective bills
SELECT
    b.bill_number,
    b.title,
    ba.overall_bias,
    ba.objectivity_score
FROM bills b
JOIN bias_analysis ba ON b.id = ba.text_id AND ba.text_type = 'bill'
WHERE ba.objectivity_score > 0.8
ORDER BY ba.objectivity_score DESC
LIMIT 20;
```

### Bias Distribution

```sql
-- Distribution of bias across bills
SELECT
    ba.overall_bias,
    COUNT(*) as count,
    AVG(ba.bias_score) as avg_score,
    AVG(ba.objectivity_score) as avg_objectivity
FROM bias_analysis ba
WHERE ba.text_type = 'bill'
GROUP BY ba.overall_bias
ORDER BY AVG(ba.bias_score);
```

---

## Consistency Analysis Queries

### Politician Voting Consistency

```sql
-- Top consistent voters
SELECT
    l.name,
    l.current_party,
    l.state,
    c.overall_consistency,
    c.party_line_voting,
    c.bipartisan_score,
    c.total_votes_analyzed
FROM legislators l
JOIN consistency_analysis c ON l.id = c.person_id
WHERE c.total_votes_analyzed >= 50
ORDER BY c.overall_consistency DESC
LIMIT 20;

-- Politicians with most position changes
SELECT
    l.name,
    l.current_party,
    l.state,
    c.position_changes_count,
    c.flip_flops_count,
    c.overall_consistency
FROM legislators l
JOIN consistency_analysis c ON l.id = c.person_id
WHERE c.total_votes_analyzed >= 50
ORDER BY c.position_changes_count DESC
LIMIT 20;

-- Most bipartisan politicians
SELECT
    l.name,
    l.current_party,
    l.state,
    c.bipartisan_score,
    c.party_line_voting
FROM legislators l
JOIN consistency_analysis c ON l.id = c.person_id
WHERE c.total_votes_analyzed >= 50
ORDER BY c.bipartisan_score DESC
LIMIT 20;
```

### Issue-Specific Consistency

```sql
-- Consistency by issue/topic
SELECT
    l.name,
    l.current_party,
    ic.issue_topic,
    ic.consistency_score,
    ic.vote_count
FROM legislators l
JOIN issue_consistency ic ON l.id = ic.person_id
WHERE ic.vote_count >= 10
ORDER BY l.name, ic.consistency_score DESC;

-- Politicians inconsistent on specific issue
SELECT
    l.name,
    l.current_party,
    ic.issue_topic,
    ic.consistency_score,
    ic.vote_count
FROM legislators l
JOIN issue_consistency ic ON l.id = ic.person_id
WHERE ic.issue_topic = 'healthcare'
  AND ic.consistency_score < 0.7
  AND ic.vote_count >= 5
ORDER BY ic.consistency_score ASC;
```

### Position Changes Over Time

```sql
-- Recent position changes
SELECT
    l.name,
    l.current_party,
    pc.subject,
    pc.from_position,
    pc.to_position,
    pc.change_date,
    pc.is_flip_flop
FROM legislators l
JOIN position_changes pc ON l.id = pc.person_id
WHERE pc.change_date >= CURRENT_DATE - INTERVAL '1 year'
ORDER BY pc.change_date DESC;

-- Flip-flops only
SELECT
    l.name,
    l.current_party,
    pc.subject,
    pc.from_position,
    pc.to_position,
    pc.change_date
FROM legislators l
JOIN position_changes pc ON l.id = pc.person_id
WHERE pc.is_flip_flop = TRUE
ORDER BY pc.change_date DESC;
```

---

## Similarity Search Queries

### Find Similar Bills

```sql
-- Most similar bill pairs
SELECT
    b1.bill_number as bill1,
    b1.title as title1,
    b2.bill_number as bill2,
    b2.title as title2,
    bs.similarity_score
FROM bill_similarities bs
JOIN bills b1 ON bs.bill_id_1 = b1.id
JOIN bills b2 ON bs.bill_id_2 = b2.id
WHERE bs.similarity_score > 0.8
ORDER BY bs.similarity_score DESC
LIMIT 20;

-- Bills similar to a specific bill
SELECT
    b2.bill_number,
    b2.title,
    bs.similarity_score
FROM bill_similarities bs
JOIN bills b1 ON (bs.bill_id_1 = b1.id OR bs.bill_id_2 = b1.id)
JOIN bills b2 ON (CASE
    WHEN bs.bill_id_1 = b1.id THEN bs.bill_id_2 = b2.id
    ELSE bs.bill_id_1 = b2.id
END)
WHERE b1.bill_number = 'HR1234'
ORDER BY bs.similarity_score DESC
LIMIT 10;
```

### Cluster Similar Bills

```sql
-- Find bills with high similarity to any in a set (topic clustering)
WITH topic_bills AS (
    SELECT id FROM bills WHERE bill_number IN ('HR1234', 'S456', 'HR789')
)
SELECT DISTINCT
    b.bill_number,
    b.title,
    MAX(bs.similarity_score) as max_similarity
FROM bills b
JOIN bill_similarities bs ON (b.id = bs.bill_id_1 OR b.id = bs.bill_id_2)
JOIN topic_bills tb ON (tb.id = bs.bill_id_1 OR tb.id = bs.bill_id_2)
WHERE b.id NOT IN (SELECT id FROM topic_bills)
  AND bs.similarity_score > 0.7
GROUP BY b.id, b.bill_number, b.title
ORDER BY max_similarity DESC;
```

---

## Complex Analysis Queries

### Comprehensive Bill Analysis

```sql
-- Complete analysis summary for a bill
SELECT
    b.bill_number,
    b.title,
    b.introduced_date,
    b.status,
    -- Sentiment
    s.sentiment_label,
    s.compound_score,
    -- Bias
    ba.overall_bias,
    ba.objectivity_score,
    -- Entities
    (SELECT COUNT(*) FROM extracted_entities ee 
     WHERE ee.text_id = b.id AND ee.text_type = 'bill') as entity_count,
    -- Similar bills
    (SELECT COUNT(*) FROM bill_similarities bs 
     WHERE (bs.bill_id_1 = b.id OR bs.bill_id_2 = b.id) 
     AND bs.similarity_score > 0.7) as similar_bill_count
FROM bills b
LEFT JOIN latest_bill_sentiment s ON b.id = s.bill_id
LEFT JOIN latest_bill_bias ba ON b.id = ba.bill_id
WHERE b.bill_number = 'HR1234';
```

### Politicians with Unusual Voting Patterns

```sql
-- Find politicians voting against their party
SELECT
    l.name,
    l.current_party,
    c.party_line_voting,
    c.total_votes_analyzed,
    c.overall_consistency
FROM legislators l
JOIN consistency_analysis c ON l.id = c.person_id
WHERE c.party_line_voting < 0.7
  AND c.total_votes_analyzed >= 50
ORDER BY c.party_line_voting ASC;
```

### Correlation Between Sentiment and Passage

```sql
-- Do positive bills pass more often?
SELECT
    s.sentiment_label,
    COUNT(*) as bill_count,
    SUM(CASE WHEN b.status IN ('enacted', 'passed') THEN 1 ELSE 0 END) as passed_count,
    ROUND(
        100.0 * SUM(CASE WHEN b.status IN ('enacted', 'passed') THEN 1 ELSE 0 END) / COUNT(*),
        2
    ) as passage_rate
FROM bills b
JOIN sentiment_analysis s ON b.id = s.text_id AND s.text_type = 'bill'
GROUP BY s.sentiment_label;
```

### Entity Network Analysis

```sql
-- Create a co-occurrence network of people and organizations
WITH entity_network AS (
    SELECT
        e1.entity_text as node1,
        e1.entity_label as node1_type,
        e2.entity_text as node2,
        e2.entity_label as node2_type,
        COUNT(DISTINCT e1.text_id) as connection_strength
    FROM extracted_entities e1
    JOIN extracted_entities e2 ON e1.text_id = e2.text_id
    WHERE e1.entity_label IN ('PERSON', 'ORG')
      AND e2.entity_label IN ('PERSON', 'ORG')
      AND e1.entity_text < e2.entity_text
    GROUP BY e1.entity_text, e1.entity_label, e2.entity_text, e2.entity_label
    HAVING COUNT(DISTINCT e1.text_id) >= 5
)
SELECT * FROM entity_network
ORDER BY connection_strength DESC
LIMIT 50;
```

---

## Performance Optimization

### Create Useful Indexes

```sql
-- Indexes for sentiment queries
CREATE INDEX IF NOT EXISTS idx_sentiment_label_score 
ON sentiment_analysis(sentiment_label, compound_score DESC);

-- Indexes for entity queries
CREATE INDEX IF NOT EXISTS idx_entities_text_lower 
ON extracted_entities(LOWER(entity_text));

CREATE INDEX IF NOT EXISTS idx_entities_label_text 
ON extracted_entities(entity_label, entity_text);

-- Indexes for similarity queries
CREATE INDEX IF NOT EXISTS idx_similarities_score_high 
ON bill_similarities(similarity_score DESC) WHERE similarity_score > 0.7;

-- Composite indexes for common joins
CREATE INDEX IF NOT EXISTS idx_bills_congress_chamber 
ON bills(congress, chamber);
```

### Materialized Views for Common Queries

```sql
-- Materialized view for bill analysis summary
CREATE MATERIALIZED VIEW IF NOT EXISTS bill_analysis_summary AS
SELECT
    b.id,
    b.bill_number,
    b.title,
    b.congress,
    b.chamber,
    s.sentiment_label,
    s.compound_score,
    ba.overall_bias,
    ba.objectivity_score,
    (SELECT COUNT(*) FROM extracted_entities ee 
     WHERE ee.text_id = b.id AND ee.text_type = 'bill') as entity_count
FROM bills b
LEFT JOIN latest_bill_sentiment s ON b.id = s.bill_id
LEFT JOIN latest_bill_bias ba ON b.id = ba.bill_id;

-- Refresh the view
REFRESH MATERIALIZED VIEW bill_analysis_summary;

-- Create index on the view
CREATE INDEX idx_bill_analysis_congress 
ON bill_analysis_summary(congress);
```

### Query Optimization Tips

```sql
-- Use EXPLAIN ANALYZE to check query performance
EXPLAIN ANALYZE
SELECT ...;

-- Limit results for large datasets
SELECT ... LIMIT 1000;

-- Use EXISTS instead of IN for better performance
SELECT b.* FROM bills b
WHERE EXISTS (
    SELECT 1 FROM sentiment_analysis s 
    WHERE s.text_id = b.id AND s.sentiment_label = 'positive'
);

-- Avoid SELECT * when you only need specific columns
SELECT b.id, b.bill_number, b.title
FROM bills b
...;
```

---

## Exporting Data

### Export to CSV

```bash
# Export bill sentiment data
psql $DATABASE_URL -c "COPY (
    SELECT
        b.bill_number,
        b.title,
        s.sentiment_label,
        s.compound_score
    FROM bills b
    JOIN sentiment_analysis s ON b.id = s.text_id
) TO STDOUT WITH CSV HEADER" > bill_sentiment.csv

# Export entity data
psql $DATABASE_URL -c "COPY (
    SELECT
        b.bill_number,
        ee.entity_text,
        ee.entity_label
    FROM bills b
    JOIN extracted_entities ee ON b.id = ee.text_id
) TO STDOUT WITH CSV HEADER" > entities.csv
```

### Export to JSON

```sql
-- Export as JSON
SELECT json_agg(row_to_json(t)) FROM (
    SELECT
        b.bill_number,
        b.title,
        s.sentiment_label,
        s.compound_score
    FROM bills b
    JOIN sentiment_analysis s ON b.id = s.text_id
    LIMIT 100
) t;
```

---

*Last Updated: 2025-10-14*
*Part of the OpenDiscourse.net project*
