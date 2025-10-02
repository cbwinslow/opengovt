###############################################################################
# Name:        Database helpers and migrations
# Date:        2025-10-02
# Script Name: db.py
# Version:     1.0
# Log Summary: Database connection helper, migration runner, and DB ingestor.
# Description: Provides a migration runner for SQL files and a DBIngestor class
#              that executes schema migrations and provides upsert methods for
#              bills, votes, and legislators using psycopg2.
# Change Summary:
#   - 1.0 initial DB helpers and migration execution
# Inputs: connection string, path to migrations
# Outputs: Applies migrations to Postgres, provides upsert APIs
###############################################################################

import os
import glob
import psycopg2
import psycopg2.extras
from typing import Optional, Dict, Any
from app.utils import labeled, configure_logger

logger = configure_logger("db", level=20)

@labeled("db_migrations")
def run_migrations(conn_str: str, migrations_dir: str):
    """
    Applies SQL migration files in lexicographic order. Each file applied in a transaction.
    """
    logger.info("Running migrations from %s", migrations_dir)
    files = sorted(glob.glob(os.path.join(migrations_dir, "*.sql")))
    conn = psycopg2.connect(conn_str)
    try:
        for f in files:
            with open(f, "r", encoding="utf-8") as fh:
                sql = fh.read()
            logger.info("Applying migration %s", f)
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()
    finally:
        conn.close()

class DBIngestor:
    def __init__(self, conn_str: str):
        self.conn_str = conn_str
        self.conn = None

    @labeled("db_connect")
    def connect(self):
        self.conn = psycopg2.connect(self.conn_str)
        self.conn.autocommit = False

    @labeled("db_ensure_schema")
    def ensure_schema(self, migrations_dir: str):
        run_migrations(self.conn_str, migrations_dir)

    @labeled("db_upsert_bill")
    def upsert_bill(self, record: Dict[str, Any]):
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO bills (source_file, congress, chamber, bill_number, title, sponsor, introduced_date)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (congress,chamber,bill_number) DO UPDATE
                SET title = EXCLUDED.title, sponsor = EXCLUDED.sponsor, introduced_date = EXCLUDED.introduced_date
                RETURNING id
            """, (record.get("source_file"), record.get("congress"), record.get("chamber"), record.get("bill_number"), record.get("title"), record.get("sponsor"), record.get("introduced_date")))
            res = cur.fetchone()
        self.conn.commit()
        return res[0] if res else None

    @labeled("db_upsert_vote")
    def upsert_vote(self, record: Dict[str, Any]):
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO votes (source_file, congress, chamber, vote_id, vote_date, result)
                VALUES (%s,%s,%s,%s,%s,%s)
                ON CONFLICT (congress,chamber,vote_id) DO UPDATE
                SET result = EXCLUDED.result, vote_date = EXCLUDED.vote_date
                RETURNING id
            """, (record.get("source_file"), record.get("congress"), record.get("chamber"), record.get("vote_id"), record.get("vote_date"), record.get("result")))
            res = cur.fetchone()
        self.conn.commit()
        return res[0] if res else None

    @labeled("db_upsert_legislator")
    def upsert_legislator(self, record: Dict[str, Any]):
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO legislators (name, bioguide, current_party, state)
                VALUES (%s,%s,%s,%s)
                ON CONFLICT (bioguide) DO UPDATE
                SET name = EXCLUDED.name, current_party = EXCLUDED.current_party, state = EXCLUDED.state
                RETURNING id
            """, (record.get("name"), record.get("bioguide"), record.get("current_party"), record.get("state")))
            res = cur.fetchone()
        self.conn.commit()
        return res[0] if res else None

    @labeled("db_close")
    def close(self):
        if self.conn:
            self.conn.close()