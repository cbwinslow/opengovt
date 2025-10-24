# Development Guide

Welcome to the OpenGovt development guide! This document will help you set up your development environment and contribute to the project.

## Table of Contents

- [Development Environment Setup](#development-environment-setup)
- [Project Architecture](#project-architecture)
- [Code Style and Conventions](#code-style-and-conventions)
- [Testing](#testing)
- [Contributing](#contributing)
- [Common Development Tasks](#common-development-tasks)

## Development Environment Setup

### Option 1: DevContainer (Recommended)

Using VS Code DevContainers provides a consistent, isolated development environment.

1. **Prerequisites:**
   - VS Code with "Remote - Containers" extension
   - Docker Desktop

2. **Open in DevContainer:**
   ```bash
   # Clone the repository
   git clone https://github.com/cbwinslow/opengovt.git
   cd opengovt
   
   # Open in VS Code
   code .
   
   # VS Code will prompt to "Reopen in Container" - click Yes
   # Or use Command Palette: "Remote-Containers: Reopen in Container"
   ```

3. **Automatic Setup:**
   The DevContainer will automatically:
   - Install Python 3.12 and Node.js 20
   - Install all Python dependencies
   - Install frontend dependencies
   - Configure VS Code extensions
   - Set up database connection

### Option 2: Local Setup

1. **Install Prerequisites:**
   ```bash
   # Ubuntu/Debian
   sudo apt update
   sudo apt install python3.12 python3.12-venv postgresql-15 nodejs npm
   
   # macOS (using Homebrew)
   brew install python@3.12 postgresql@15 node
   
   # Start PostgreSQL
   sudo systemctl start postgresql  # Linux
   brew services start postgresql@15  # macOS
   ```

2. **Set up Python Environment:**
   ```bash
   # Create virtual environment
   python3.12 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   
   # Install dependencies
   pip install --upgrade pip
   pip install -r requirements.txt
   pip install -r requirements-analysis.txt
   
   # Install development tools
   pip install -e .
   ```

3. **Set up Database:**
   ```bash
   # Create database and user
   sudo -u postgres psql
   CREATE DATABASE opengovt_dev;
   CREATE USER dev_user WITH PASSWORD 'dev_password';
   GRANT ALL PRIVILEGES ON DATABASE opengovt_dev TO dev_user;
   \q
   
   # Run migrations
   psql -U dev_user -d opengovt_dev -f app/db/migrations/001_init.sql
   psql -U dev_user -d opengovt_dev -f app/db/migrations/002_analysis_tables.sql
   psql -U dev_user -d opengovt_dev -f app/db/migrations/003_social_media_tables.sql
   ```

4. **Set up Frontend:**
   ```bash
   cd frontend-v2
   npm install
   npm run dev
   ```

5. **Configure Environment:**
   ```bash
   # Copy and edit environment file
   cp .env.example .env
   nano .env  # or use your preferred editor
   ```

### Option 3: Docker Development

```bash
# Start development environment
docker-compose -f docker-compose.dev.yml up

# Access running container
docker-compose exec api bash

# Run commands inside container
python scripts/twitter_ingestion.py --help
```

## Project Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (Next.js)                    │
│  - User interface                                        │
│  - Data visualization                                    │
│  - Interactive components                                │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP/REST
┌──────────────────────▼──────────────────────────────────┐
│                  API Server (Flask/FastAPI)              │
│  - RESTful endpoints                                     │
│  - Authentication                                        │
│  - Request validation                                    │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│               Business Logic Layer                       │
│  - Data models (models/)                                 │
│  - Analysis modules (analysis/)                          │
│  - Pipeline orchestration (app/pipeline.py)             │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│                   Data Layer                            │
│  - Database access (app/db.py)                          │
│  - External APIs (scripts/)                              │
│  - Caching layer                                         │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│                 Data Storage                             │
│  - PostgreSQL (primary data)                            │
│  - Redis (cache)                                         │
│  - File storage (bulk data)                              │
└─────────────────────────────────────────────────────────┘
```

### Module Structure

```
opengovt/
├── models/              # Data models (dataclasses)
│   ├── bill.py         # Bill-related models
│   ├── person.py       # Legislator/person models
│   ├── vote.py         # Voting models
│   └── social_media.py # Social media models
│
├── analysis/            # NLP and ML analysis
│   ├── sentiment.py    # Sentiment analysis
│   ├── bias_detector.py # Bias detection
│   ├── embeddings.py   # Text embeddings
│   └── nlp_processor.py # General NLP
│
├── app/                 # Application logic
│   ├── db/             # Database utilities
│   │   └── migrations/ # SQL migrations
│   ├── pipeline.py     # Data pipeline
│   ├── db.py          # Database access
│   └── run.py         # App runner
│
├── scripts/             # Utility scripts
│   ├── twitter_ingestion.py
│   ├── analyze_tweets.py
│   └── extract_statements.py
│
└── frontend-v2/         # Next.js frontend
    ├── app/            # App router pages
    ├── components/     # React components
    └── lib/           # Utilities
```

## Code Style and Conventions

### Python Code Style

We follow PEP 8 with some modifications:

```python
# Use type hints
def analyze_sentiment(text: str) -> Dict[str, float]:
    """Analyze sentiment of text.
    
    Args:
        text: Input text to analyze
    
    Returns:
        Dictionary with sentiment scores
    """
    pass

# Use dataclasses for models
from dataclasses import dataclass
from typing import Optional

@dataclass
class Tweet:
    id: Optional[int] = None
    text: Optional[str] = None
    created_at: Optional[datetime] = None

# Use f-strings for formatting
logger.info(f"Processing tweet {tweet_id} from {username}")

# Use context managers
with psycopg2.connect(DATABASE_URL) as conn:
    with conn.cursor() as cursor:
        cursor.execute(query)
```

### Formatting Tools

```bash
# Format code with black
black .

# Sort imports with isort
isort .

# Check code style with flake8
flake8 .

# Type checking with mypy
mypy .

# Run all checks
black . && isort . && flake8 . && mypy .
```

### JavaScript/TypeScript Style

```typescript
// Use TypeScript for type safety
interface TweetData {
  id: number;
  text: string;
  createdAt: Date;
}

// Use async/await
async function fetchTweets(): Promise<TweetData[]> {
  const response = await fetch('/api/tweets');
  return response.json();
}

// Use modern React patterns
const TweetList: React.FC = () => {
  const [tweets, setTweets] = useState<TweetData[]>([]);
  
  useEffect(() => {
    fetchTweets().then(setTweets);
  }, []);
  
  return <div>{/* component */}</div>;
};
```

### Naming Conventions

- **Python:**
  - Classes: `PascalCase` (e.g., `TweetAnalyzer`)
  - Functions/methods: `snake_case` (e.g., `analyze_sentiment`)
  - Constants: `UPPER_SNAKE_CASE` (e.g., `MAX_BATCH_SIZE`)
  - Private: prefix with `_` (e.g., `_internal_method`)

- **JavaScript/TypeScript:**
  - Components: `PascalCase` (e.g., `TweetCard`)
  - Functions: `camelCase` (e.g., `fetchTweets`)
  - Constants: `UPPER_SNAKE_CASE` (e.g., `API_BASE_URL`)

### Documentation

- All public functions must have docstrings
- Use Google-style docstrings for Python
- Use JSDoc for JavaScript/TypeScript
- Keep README and docs up to date

Example Python docstring:

```python
def extract_statements(text: str, person_name: str) -> List[Dict[str, Any]]:
    """Extract political statements from text.
    
    Extracts statements at multiple granularity levels (short, medium, full)
    and identifies action type, subject, and stance.
    
    Args:
        text: Text to extract statements from
        person_name: Name of the person making the statement
    
    Returns:
        List of dictionaries containing extracted statements with metadata
    
    Raises:
        ValueError: If text or person_name is empty
    
    Example:
        >>> text = "Senator X voted to increase taxes 5% in VA"
        >>> statements = extract_statements(text, "Senator X")
        >>> print(statements[0]['statement_short'])
        'Senator X voted to increase taxes'
    """
    pass
```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_sentiment.py

# Run specific test
pytest tests/test_sentiment.py::test_vader_sentiment

# Run with verbose output
pytest -v

# Run only fast tests (skip slow/integration tests)
pytest -m "not slow"
```

### Writing Tests

Place tests in the `tests/` directory:

```python
# tests/test_sentiment.py
import pytest
from analysis.sentiment import SentimentAnalyzer

@pytest.fixture
def analyzer():
    """Create sentiment analyzer instance."""
    return SentimentAnalyzer()

def test_positive_sentiment(analyzer):
    """Test detection of positive sentiment."""
    text = "This is a great and wonderful day!"
    result = analyzer.analyze_text(text)
    
    assert result['sentiment_label'] == 'positive'
    assert result['compound_score'] > 0.5

def test_negative_sentiment(analyzer):
    """Test detection of negative sentiment."""
    text = "This is terrible and awful!"
    result = analyzer.analyze_text(text)
    
    assert result['sentiment_label'] == 'negative'
    assert result['compound_score'] < -0.5

@pytest.mark.slow
def test_large_batch_processing(analyzer):
    """Test processing large batch of texts."""
    texts = ["Sample text"] * 1000
    results = [analyzer.analyze_text(t) for t in texts]
    assert len(results) == 1000
```

### Test Markers

Use markers to categorize tests:

```python
@pytest.mark.unit  # Unit test
@pytest.mark.integration  # Integration test
@pytest.mark.slow  # Slow-running test
@pytest.mark.requires_api  # Requires API access
```

### Test Database

Use a separate test database:

```python
# conftest.py
import pytest
import psycopg2

@pytest.fixture(scope='session')
def test_db():
    """Create test database."""
    conn = psycopg2.connect(
        "postgresql://postgres:postgres@localhost/opengovt_test"
    )
    yield conn
    conn.close()
```

## Contributing

### Git Workflow

1. **Create a feature branch:**
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/bug-description
   ```

2. **Make changes and commit:**
   ```bash
   # Stage changes
   git add .
   
   # Commit with descriptive message
   git commit -m "Add sentiment analysis for tweet replies"
   ```

3. **Push to your fork:**
   ```bash
   git push origin feature/your-feature-name
   ```

4. **Create Pull Request:**
   - Go to GitHub
   - Click "New Pull Request"
   - Provide detailed description
   - Link related issues

### Commit Message Guidelines

Follow conventional commits:

```
type(scope): subject

body (optional)

footer (optional)
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**
```
feat(twitter): Add reply toxicity analysis

Implements toxicity detection for tweet replies using Detoxify model.
Includes hate speech classification and toxicity level categorization.

Closes #123

---

fix(db): Correct social_media_profiles unique constraint

The constraint should be on (person_id, platform, username) not just
(platform, username) to allow same username across different people.

---

docs(api): Update API endpoint documentation

Add examples for new social media endpoints
```

### Code Review Process

1. All changes require code review
2. Address reviewer feedback
3. Ensure CI passes (tests, linting)
4. Squash commits if requested
5. Merge when approved

## Common Development Tasks

### Adding a New Migration

```bash
# Create migration file
touch app/db/migrations/004_new_feature.sql

# Write migration
cat > app/db/migrations/004_new_feature.sql << 'EOF'
-- Name: DB migration 004 - new feature
-- Date: 2025-10-23
-- Description: Add new tables for feature X

BEGIN;

CREATE TABLE IF NOT EXISTS new_table (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL
);

COMMIT;
EOF

# Test migration
psql -d opengovt_dev -f app/db/migrations/004_new_feature.sql

# Update app/db.py to include new migration
```

### Adding a New Analysis Module

```python
# analysis/new_analyzer.py
"""
New analysis module description.
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class NewAnalyzer:
    """Description of new analyzer."""
    
    def __init__(self):
        """Initialize analyzer."""
        logger.info("Initializing NewAnalyzer")
        # Initialize models, etc.
    
    def analyze(self, text: str) -> Dict[str, Any]:
        """Analyze text.
        
        Args:
            text: Input text
        
        Returns:
            Analysis results
        """
        # Implement analysis
        return {}


# Add tests in tests/test_new_analyzer.py
# Add documentation in docs/
# Update README if necessary
```

### Adding a New Data Model

```python
# models/new_model.py
"""
Description of new model.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime


@dataclass
class NewModel:
    """Description of what this model represents."""
    
    id: Optional[int] = None
    name: Optional[str] = None
    created_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'metadata': self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NewModel':
        """Create from dictionary."""
        model = cls()
        model.id = data.get('id')
        model.name = data.get('name')
        # ... set other fields
        return model


# Update models/__init__.py to export the new model
```

### Debugging Tips

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Run with Python debugger
python -m pdb scripts/twitter_ingestion.py

# Use ipdb for better debugging
pip install ipdb
# Add in code: import ipdb; ipdb.set_trace()

# Check database state
psql -d opengovt_dev
\dt  # List tables
SELECT * FROM table_name LIMIT 10;

# Monitor logs in real-time
tail -f logs/app.log

# Check running processes
ps aux | grep python
```

### Performance Profiling

```python
# Profile code execution
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

# Your code here

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(20)  # Top 20 functions

# Or use line_profiler for line-by-line profiling
pip install line_profiler
# Add @profile decorator to functions
kernprof -l -v script.py
```

### Database Queries Optimization

```sql
-- Check slow queries
SELECT query, calls, total_time, mean_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;

-- Analyze query performance
EXPLAIN ANALYZE
SELECT * FROM politician_tweets WHERE person_id = 123;

-- Check index usage
SELECT schemaname, tablename, indexname, idx_scan
FROM pg_stat_user_indexes
WHERE idx_scan = 0;
```

## Development Resources

### Useful Commands

```bash
# Start development server
npm run dev  # Frontend
python cbw_http.py --serve  # API

# Database console
psql -d opengovt_dev

# Python REPL with project context
python -i -c "from models import *; from analysis import *"

# Check dependencies for updates
pip list --outdated
npm outdated

# Update dependencies
pip install -U -r requirements.txt
npm update
```

### IDE Setup

**VS Code Extensions:**
- Python (ms-python.python)
- Pylance (ms-python.vscode-pylance)
- Black Formatter (ms-python.black-formatter)
- ESLint (dbaeumer.vscode-eslint)
- Prettier (esbenp.prettier-vscode)
- GitLens (eamodio.gitlens)
- Docker (ms-azuretools.vscode-docker)

**PyCharm Configuration:**
- Set Python interpreter to `.venv/bin/python`
- Enable pytest as test runner
- Configure Black as formatter
- Set up PostgreSQL database connection

### External Resources

- [Python Style Guide (PEP 8)](https://pep8.org/)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [Next.js Documentation](https://nextjs.org/docs)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Twitter API v2](https://developer.twitter.com/en/docs/twitter-api)

## Getting Help

- **Documentation**: Check `docs/` directory first
- **Issues**: Search [GitHub Issues](https://github.com/cbwinslow/opengovt/issues)
- **Discussions**: Join [GitHub Discussions](https://github.com/cbwinslow/opengovt/discussions)
- **Code**: Review existing code for examples

## License

By contributing to OpenGovt, you agree that your contributions will be licensed under the MIT License.
