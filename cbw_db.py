###############################################################################
# Name:        cbw_db.py
# Date:        2025-10-02
# Script Name: cbw_db.py
# Version:     1.0
# Log Summary: Database manager: run migrations and upsert parsed records.
# Description: Provides DBManager to run embedded migrations and upsert bills, votes,
#              and legislators. Uses psycopg2. The migration SQL is passed in at init.
# Change Summary:
#   - 1.0 initial DB manager split-out
# Inputs:
#   - DB connection string and migrations list
# Outputs:
#   - DB schema creation and upsert operations
###############################################################################

from typing import Dict, Any, Optional, List
from cbw_utils import labeled, configure_logger, adapter_for
import psycopg2

logger = configure_logger()
ad = adapter_for(logger, "db")

class DBManager:
    def __init__(self, conn_str: str, migrations: Optional[List[tuple]] = None):
        self.conn_str = conn_str
        self.conn = None
        self.migrations = migrations or []

    @labeled("db_connect")
    def connect(self):
        if psycopg2 is None:
            raise RuntimeError("psycopg2 not installed. pip install psycopg2-binary")
        self.conn = psycopg2.connect(self.conn_str)
        self.conn.autocommit = False
        ad.info("Connected to Postgres")

    @labeled("db_run_migrations")
    def run_migrations(self):
        if not self.conn:
            self.connect()
        cur = self.conn.cursor()
        try:
            for name, sql in self.migrations:
                ad.info("Applying migration %s", name)
                cur.execute(sql)
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            ad.exception("Migration error: %s", e)
            raise

    @labeled("db_upsert_bill")
    def upsert_bill(self, rec: Dict[str, Any], congress: Optional[int] = None, chamber: Optional[str] = None) -> Optional[int]:
        if not self.conn:
            self.connect()
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO bills (source_file, congress, chamber, bill_number, title, sponsor, introduced_date)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (congress,chamber,bill_number) DO UPDATE
                SET title = EXCLUDED.title, sponsor = EXCLUDED.sponsor, introduced_date = EXCLUDED.introduced_date
                RETURNING id
            """, (rec.get("source_file"), congress, chamber, rec.get("bill_number"), rec.get("title"), rec.get("sponsor"), rec.get("introduced_date")))
            row = cur.fetchone()
        self.conn.commit()
        return row[0] if row else None

    @labeled("db_upsert_vote")
    def upsert_vote(self, rec: Dict[str, Any], congress: Optional[int] = None, chamber: Optional[str] = None) -> Optional[int]:
        if not self.conn:
            self.connect()
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO votes (source_file, congress, chamber, vote_id, vote_date, result)
                VALUES (%s,%s,%s,%s,%s,%s)
                ON CONFLICT (congress,chamber,vote_id) DO UPDATE
                SET result = EXCLUDED.result, vote_date = EXCLUDED.vote_date
                RETURNING id
            """, (rec.get("source_file"), congress, chamber, rec.get("vote_id"), rec.get("date"), rec.get("result")))
            row = cur.fetchone()
        self.conn.commit()
        return row[0] if row else None

    @labeled("db_upsert_legislator")
    def upsert_legislator(self, rec: Dict[str, Any]) -> Optional[int]:
        if not self.conn:
            self.connect()
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO legislators (name, bioguide, current_party, state)
                VALUES (%s,%s,%s,%s)
                ON CONFLICT (bioguide) DO UPDATE
                SET name = EXCLUDED.name, current_party = EXCLUDED.current_party, state = EXCLUDED.state
                RETURNING id
            """, (rec.get("name"), rec.get("bioguide"), rec.get("current_party"), rec.get("state")))
            row = cur.fetchone()
        self.conn.commit()
        return row[0] if row else None

    @labeled("db_close")
    def close(self):
        if self.conn:
            self.conn.close()
            ad.info("DB connection closed")