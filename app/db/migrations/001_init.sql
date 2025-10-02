-- Name: DB migration 001 - initial schema
-- Date: 2025-10-02
-- Description: Create base tables for bills, votes, legislators, sponsors, actions, texts, rollcall breakdown
BEGIN;

CREATE TABLE IF NOT EXISTS bills (
  id SERIAL PRIMARY KEY,
  source_file TEXT,
  congress INTEGER,
  chamber TEXT,
  bill_number TEXT,
  title TEXT,
  sponsor TEXT,
  introduced_date TIMESTAMP,
  inserted_at TIMESTAMP DEFAULT now(),
  UNIQUE (congress, chamber, bill_number)
);

CREATE TABLE IF NOT EXISTS votes (
  id SERIAL PRIMARY KEY,
  source_file TEXT,
  congress INTEGER,
  chamber TEXT,
  vote_id TEXT,
  vote_date TIMESTAMP,
  result TEXT,
  inserted_at TIMESTAMP DEFAULT now(),
  UNIQUE (congress, chamber, vote_id)
);

CREATE TABLE IF NOT EXISTS legislators (
  id SERIAL PRIMARY KEY,
  name TEXT,
  bioguide TEXT,
  current_party TEXT,
  state TEXT,
  inserted_at TIMESTAMP DEFAULT now(),
  UNIQUE (bioguide)
);

-- Sponsors (many-to-one)
CREATE TABLE IF NOT EXISTS sponsors (
  id SERIAL PRIMARY KEY,
  bill_id INTEGER REFERENCES bills(id) ON DELETE CASCADE,
  name TEXT,
  role TEXT
);

-- Actions (history of a bill)
CREATE TABLE IF NOT EXISTS bill_actions (
  id SERIAL PRIMARY KEY,
  bill_id INTEGER REFERENCES bills(id) ON DELETE CASCADE,
  action_date TIMESTAMP,
  description TEXT
);

-- Full texts
CREATE TABLE IF NOT EXISTS bill_texts (
  id SERIAL PRIMARY KEY,
  bill_id INTEGER REFERENCES bills(id) ON DELETE CASCADE,
  text_type TEXT,
  text_url TEXT,
  inserted_at TIMESTAMP DEFAULT now()
);

-- Rollcall vote breakdown (member-level)
CREATE TABLE IF NOT EXISTS rollcall_votes (
  id SERIAL PRIMARY KEY,
  vote_id INTEGER REFERENCES votes(id) ON DELETE CASCADE,
  member_bioguide TEXT,
  vote_choice TEXT
);

COMMIT;