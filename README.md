```markdown
# cbw Congress Bulk Ingest - Multi-file Package

## 📚 Documentation

- **[SCRIPT_EVALUATION.md](SCRIPT_EVALUATION.md)** - Comprehensive analysis of all 46 scripts, functions, and interactions (1,178 lines)
- **[SCRIPT_INDEX.md](SCRIPT_INDEX.md)** - Quick reference guide with script catalog and common workflows (170 lines)
- **[PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)** - Project organization and data models
- **[docs/](docs/)** - Detailed documentation on analysis modules, APIs, and queries

Overview
- Purpose: End-to-end OOP pipeline to discover, download, extract, parse, normalize,
  and ingest U.S. legislative bulk data (govinfo / congress.gov, GovTrack, OpenStates,
  theunitedstates, etc.) into PostgreSQL. Includes retry reporting, HTTP control API,
  detailed labeled logging and decorators, and a basic TUI (separate build).
- Files: All Python modules are prefixed `cbw_` to show they belong together:
  - cbw_utils.py        - logging, decorators, JSON helpers
  - cbw_config.py      - configuration object & defaults
  - cbw_discovery.py   - discovery of candidate URLs
  - cbw_validator.py   - HEAD/GET validation
  - cbw_downloader.py  - async downloader with resume/retry
  - cbw_extractor.py   - archive extraction
  - cbw_parser.py      - conservative parsers for XML/JSON
  - cbw_db.py          - Postgres migration & upsert helper
  - cbw_retry.py       - retry report manager
  - cbw_http.py        - HTTP control server for TUI/automation
  - cbw_main.py        - CLI entrypoint to run the end-to-end pipeline
- Docker: Dockerfile and docker-compose.yml included for full stack (Postgres + pipeline)
- Requirements: requests, aiohttp, tqdm, psycopg2-binary, lxml, prometheus-client

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
1. docker-compose up --build
2. Pipeline will attempt to run downloads as configured and expose Prometheus metrics on :8000 and control API on :8080.

Notes
- Parsers are conservative starters: provide sample XML from govinfo/congress.gov for me to add exact lxml XPaths to map sponsors, cosponsors, actions, texts, and rollcall breakdowns.
- Logs are in ./logs (rotating files), and each function is decorated with labeled entry/exit/exception logs to aid debugging.
- The retry report is stored in retry_report.json; the downloader records failed URLs automatically.
- I can now:
  - Add robust govinfo XPaths to parse sponsors/actions/rollcalls given sample files.
  - Expand the Go TUI to call the HTTP control API and display live progress.
  - Add Prometheus metric counters in the Python code (currently placeholders).
  - Provide unit tests and CI workflow.
