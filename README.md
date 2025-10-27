# OpenGovt - Government Transparency & Legislative Analysis Platform

A comprehensive platform for ingesting, analyzing, and providing transparency for U.S. legislative data, voting records, and social media discourse. Part of the **[OpenDiscourse.net](https://opendiscourse.net)** project.

## 🎯 Overview

## 🤖 Automated Workflows

This repository uses comprehensive GitHub Actions workflows for code quality, security, and automation:

- **12 Custom Workflows** - Code quality, security, documentation, AI analysis, and more
- **20+ Marketplace Actions** - Integration with best-in-class tools
- **9 AI Agents** - CrewAI-powered code analysis and improvements
- **Automated Updates** - Dependabot for dependencies, auto-formatting, file headers

📖 **[Quick Start Guide](.github/WORKFLOWS_QUICKSTART.md)** | 📚 **[Full Workflows Guide](.github/WORKFLOWS_GUIDE.md)**

## 📚 Documentation

## ✨ Key Features

### Data Ingestion
- 📊 **Legislative Data**: Bills, votes, committee activities, member information
- 🐦 **Social Media**: Twitter/X tweets, replies, engagement metrics, and media
- 🔄 **Automated Collection**: Scheduled ingestion with retry logic and rate limiting
- 📁 **Bulk Processing**: Handle large datasets efficiently with async processing

### Analysis Capabilities
- 💬 **Sentiment Analysis**: Multi-model analysis (VADER + Transformers) for tweets and bills
- ⚠️ **Toxicity Detection**: Hate speech and toxic language identification in responses
- 🎯 **Political Statement Extraction**: Multi-granularity bins of actions and declarations
- 📈 **Voting Consistency**: Track position changes and flip-flops over time
- 🤝 **Bipartisan Analysis**: Measure cross-party collaboration and agreement
- 🎭 **Bias Detection**: Identify political bias and loaded language

### Social Media Features
- 👥 **Constituent Analysis**: Profile and analyze people responding to politicians
- 📊 **Engagement Metrics**: Track likes, retweets, replies, and quote tweets
- 🔍 **Response Correlation**: Analyze how constituent responses correlate with content
- 🤖 **Bot Detection**: Identify likely automated accounts in responses
- 📍 **Geographic Analysis**: Map follower and response locations

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- PostgreSQL 15+
- Node.js 20+ (for frontend)
- Docker & Docker Compose (recommended)

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/cbwinslow/opengovt.git
cd opengovt
```

2. **Set up environment**
```bash
# Copy environment template
cp .env.example .env

# Edit .env with your API keys and settings
nano .env
```

3. **Using Docker (Recommended)**
```bash
# Build and start all services
docker-compose up --build

# Database migrations are run automatically
```

4. **Or Manual Installation**
```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-analysis.txt

# Install Node dependencies for frontend
cd frontend-v2
npm install
cd ..

# Set up database
psql -d postgres -c "CREATE DATABASE opengovt;"
psql -d opengovt -f app/db/migrations/001_init.sql
psql -d opengovt -f app/db/migrations/002_analysis_tables.sql
psql -d opengovt -f app/db/migrations/003_social_media_tables.sql
```

### Basic Usage

**Legislative Data Ingestion:**
```bash
# Run discovery (dry-run)
python cbw_main.py --start-congress 118 --end-congress 118 --dry-run

# Full ingestion
export DATABASE_URL="postgresql://user:pass@localhost:5432/opengovt"
python cbw_main.py --download --extract --postprocess --db "$DATABASE_URL"
```

**Social Media Data Collection:**
```bash
# Collect tweets from a politician
python scripts/twitter_ingestion.py \
  --person-id 123 \
  --username SenatorSmith \
  --days 30 \
  --include-replies
```

**Analysis:**
```bash
# Analyze sentiment and toxicity
python scripts/analyze_tweets.py --analyze-all

# Extract political statements
python scripts/extract_statements.py --source all
```

## 📖 Documentation

Comprehensive documentation is available in the `docs/` directory:

- **[Quick Start Guide](docs/QUICK_START.md)** - Get up and running quickly
- **[Deployment Guide](docs/DEPLOYMENT.md)** - Production deployment instructions
- **[Development Guide](docs/DEVELOPMENT.md)** - Contributing and development setup
- **[Social Media Analysis](docs/SOCIAL_MEDIA.md)** - Twitter/X integration and analysis
- **[API Endpoints](docs/API_ENDPOINTS.md)** - Government data API references
- **[SQL Queries](docs/SQL_QUERIES.md)** - Common database queries
- **[Analysis Modules](docs/ANALYSIS_MODULES.md)** - NLP and ML analysis details

## 🏗️ Project Structure

```
opengovt/
├── app/                    # Application code
│   ├── db/                # Database utilities and migrations
│   ├── pipeline.py        # Data processing pipeline
│   └── run.py            # Application runner
├── analysis/              # NLP and ML analysis modules
│   ├── sentiment.py       # Sentiment analysis
│   ├── bias_detector.py   # Political bias detection
│   ├── embeddings.py      # Text embeddings
│   └── nlp_processor.py   # General NLP processing
├── models/                # Data models
│   ├── bill.py           # Bill models
│   ├── person.py         # Person/Member models
│   ├── vote.py           # Vote models
│   └── social_media.py   # Social media models
├── scripts/               # Utility scripts
│   ├── twitter_ingestion.py      # Twitter data collection
│   ├── analyze_tweets.py         # Tweet analysis
│   └── extract_statements.py    # Statement extraction
├── frontend-v2/           # Next.js frontend application
├── docs/                  # Documentation
├── .devcontainer/         # VS Code dev container config
└── docker-compose.yml    # Docker services configuration
```

## 🔧 Configuration

### Environment Variables

Key configuration options in `.env`:

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/opengovt

# API Keys
TWITTER_BEARER_TOKEN=your_token
CONGRESS_API_KEY=your_key
OPENSTATES_API_KEY=your_key

# Feature Flags
ENABLE_TWITTER_INGESTION=true
ENABLE_SENTIMENT_ANALYSIS=true
ENABLE_TOXICITY_DETECTION=true
ENABLE_STATEMENT_EXTRACTION=true

# Analysis Settings
SENTIMENT_MODEL=vader
TOXICITY_MODEL=detoxify
```

See `.env.example` for all available options.

## 🧪 Testing

```bash
# Run all tests
pytest

# Run specific test suite
pytest tests/test_sentiment.py

# Run with coverage
pytest --cov=. --cov-report=html
```

## 📊 Data Models

### Political Statement Extraction (Multi-Granularity)

Statements are extracted at three levels:

1. **Short**: "Senator X voted to increase taxes"
2. **Medium**: "Senator X voted to increase taxes 5 percent"
3. **Full**: "Senator X voted to increase taxes 5 percent in VA last year"

This allows for analysis at different detail levels while maintaining traceability.

### Database Schema

The database includes tables for:
- **Legislative Data**: bills, votes, legislators, committees
- **Social Media**: tweets, replies, profiles, engagement
- **Analysis**: sentiment, toxicity, bias, consistency
- **Extracted Data**: political statements, entities, topics

See [SQL Queries documentation](docs/SQL_QUERIES.md) for examples.

## 🔐 Security

- Environment variables for sensitive data
- SQL injection prevention with prepared statements
- Rate limiting on API endpoints
- HTTPS enforced in production
- Regular dependency updates
- CodeQL security scanning

## 🤝 Contributing

We welcome contributions! Please see our [Development Guide](docs/DEVELOPMENT.md) for details on:
- Setting up your development environment
- Code style and conventions
- Submitting pull requests
- Running tests

## 📈 Roadmap

See **[OPENDISCOURSE_PROJECT.md](OPENDISCOURSE_PROJECT.md)** for the full roadmap.

**Short-term:**
- ✅ Social media integration (Twitter/X)
- ✅ Sentiment and toxicity analysis
- ✅ Political statement extraction
- 🔄 Real-time tweet monitoring
- 🔄 Fact-checking integration

**Medium-term:**
- Topic modeling (LDA, BERTopic)
- Specialized legal text embeddings
- Interactive visualization dashboards
- Alert system for position changes

**Long-term:**
- Multi-platform social media (Facebook, YouTube)
- Predictive voting analysis
- Automated policy briefs
- Public API access

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Congress.gov API
- OpenStates API
- ProPublica Congress API
- Twitter API v2
- spaCy, transformers, and other open-source NLP tools

## 📧 Contact

- **Project**: [OpenDiscourse.net](https://opendiscourse.net)
- **GitHub**: [cbwinslow/opengovt](https://github.com/cbwinslow/opengovt)
- **Issues**: [GitHub Issues](https://github.com/cbwinslow/opengovt/issues)

## 🌟 Star History

If you find this project useful, please consider giving it a star! ⭐

---

**Note**: This is an active development project. Features and APIs may change. Always refer to the latest documentation.
  - Provide unit tests and CI workflow.

## 🎯 OpenDiscourse Project

This repository is part of the **OpenDiscourse.net** project, which provides comprehensive analysis and transparency for government legislative data. 

### Project Status & Roadmap

See **[OPENDISCOURSE_PROJECT.md](OPENDISCOURSE_PROJECT.md)** for:
- Development roadmap and timeline
- Project items categorized by priority (Short/Medium/Long term)
- Detailed tasks and success criteria for each feature
- Current implementation status

### Key Features (Planned & In Development)

**Analysis Capabilities:**
- 🔍 Embeddings & similarity search for legislative text
- 📊 Sentiment analysis of bills and speeches
- 🏷️ Entity extraction and NLP processing
- ⚖️ Political bias detection
- 📈 Voting consistency tracking

**Upcoming Features:**
- Legal text-specific embedding models
- Topic modeling (LDA, BERTopic)
- Fact-checking integration
- Interactive visualization dashboards
- Real-time analysis API
- Alert system for position changes

### Contributing to OpenDiscourse

Check the [project issues](.github/project-issues/) for detailed specifications of planned features:
- [01-legal-embeddings.md](.github/project-issues/01-legal-embeddings.md) - Specialized embedding models
- [02-topic-modeling.md](.github/project-issues/02-topic-modeling.md) - Topic categorization
- [03-fact-checking.md](.github/project-issues/03-fact-checking.md) - Claim verification
- [04-visualization-dashboards.md](.github/project-issues/04-visualization-dashboards.md) - Interactive dashboards
- And more...

### Related Resources

- **Analysis Modules**: See [docs/ANALYSIS_MODULES.md](docs/ANALYSIS_MODULES.md)
- **Data Sources**: See [docs/GOVERNMENT_DATA_RESOURCES.md](docs/GOVERNMENT_DATA_RESOURCES.md)
- **Implementation Summary**: See [docs/IMPLEMENTATION_SUMMARY.md](docs/IMPLEMENTATION_SUMMARY.md)
