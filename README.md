```markdown
# cbw Congress Bulk Ingest - Multi-file Package

Overview
- Purpose: End-to-end OOP pipeline to discover, download, extract, parse, normalize,
  and ingest U.S. legislative bulk data (govinfo / congress.gov, GovTrack, OpenStates,
  theunitedstates, etc.) into multiple database systems. Includes retry reporting, 
  HTTP control API, detailed labeled logging and decorators, and a basic TUI (separate build).
- **Multi-Database Support**: PostgreSQL, MySQL, SQLite, ClickHouse, InfluxDB, VictoriaMetrics
- **API Integrations**: Congress.gov API, GovInfo.gov, OpenStates API v3, NY OpenLegislation
- Files: All Python modules are prefixed `cbw_` to show they belong together:
  - cbw_utils.py        - logging, decorators, JSON helpers
  - cbw_config.py      - configuration object & defaults
  - cbw_discovery.py   - discovery of candidate URLs
  - cbw_validator.py   - HEAD/GET validation
  - cbw_downloader.py  - async downloader with resume/retry
  - cbw_extractor.py   - archive extraction
  - cbw_parser.py      - conservative parsers for XML/JSON
  - cbw_db.py          - Database migration & upsert helper
  - cbw_db_adapter.py  - Multi-database adapter for different DB engines
  - cbw_retry.py       - retry report manager
  - cbw_http.py        - HTTP control server for TUI/automation
  - cbw_main.py        - CLI entrypoint to run the end-to-end pipeline
- Docker: docker-compose.yml with PostgreSQL, MySQL, ClickHouse, InfluxDB, VictoriaMetrics
- Requirements: requests, aiohttp, tqdm, psycopg2-binary, lxml, prometheus-client, PyYAML, 
                pymysql, clickhouse-driver, influxdb-client, sqlalchemy

Quickstart (local)
1. Create venv and install:
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt

2. Run discovery dry-run (no downloads):
   python cbw_main.py --start-congress 118 --end-congress 118 --dry-run

3. Full run (careful: large downloads):
   export DATABASE_URL="postgresql://user:pass@localhost:5432/congress"
   python cbw_main.py --download --extract --postprocess --db "$DATABASE_URL"

4. Start HTTP control server:
   python cbw_main.py --serve --serve-port 8080

Docker (quick)
1. Start with PostgreSQL only:
   docker-compose up --build
   
2. Include additional databases (optional):
   docker-compose --profile mysql --profile clickhouse up --build
   
3. Pipeline will expose Prometheus metrics on :8000 and control API on :8080.

Database Configuration
1. Configuration file: config/database.yaml
2. Test database connections:
   python scripts/test_db_connection.py --all
3. See docs/DATABASE_CONFIGURATION.md for detailed setup guide

Supported Databases:
- PostgreSQL (primary) - Relational database for structured data
- MySQL/MariaDB - Alternative relational database
- SQLite - Lightweight local development database
- ClickHouse - Columnar database for analytics
- InfluxDB - Time series database for metrics
- VictoriaMetrics - Prometheus-compatible time series database

Notes
- Parsers are conservative starters: provide sample XML from govinfo/congress.gov for me to add exact lxml XPaths to map sponsors, cosponsors, actions, texts, and rollcall breakdowns.
- Logs are in ./logs (rotating files), and each function is decorated with labeled entry/exit/exception logs to aid debugging.
- The retry report is stored in retry_report.json; the downloader records failed URLs automatically.
- I can now:
  - Add robust govinfo XPaths to parse sponsors/actions/rollcalls given sample files.
  - Expand the Go TUI to call the HTTP control API and display live progress.
  - Add Prometheus metric counters in the Python code (currently placeholders).
  - Provide unit tests and CI workflow.
