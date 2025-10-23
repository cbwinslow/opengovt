# OpenDiscourse Project - Development Roadmap

This repository is part of the **OpenDiscourse.net** project, which aims to provide comprehensive analysis and transparency tools for government legislative data.

## Project Overview

OpenDiscourse.net is a platform for analyzing legislative discourse, voting patterns, and political consistency across federal and state governments. This repository (opengovt) serves as the data ingestion and analysis backend.

## Repository Association

**Primary Project**: OpenDiscourse.net
**Repository**: cbwinslow/opengovt
**Role**: Data ingestion, analysis pipeline, and NLP processing backend

## Project Items & Status

### Short Term Goals

#### 1. Add Specialized Embedding Models for Legal Text
**Status**: Open  
**Priority**: High  
**Description**: Implement specialized embedding models trained on legal and legislative text to improve similarity search and clustering accuracy.
**Tasks**:
- Research available legal text embedding models
- Evaluate legal-BERT, LegalBERT, and similar models
- Implement model switching in embeddings.py
- Benchmark against current models
- Update documentation

#### 2. Implement Topic Modeling (LDA, BERTopic)
**Status**: Open  
**Priority**: High  
**Description**: Add topic modeling capabilities to automatically categorize and cluster bills by subject matter.
**Tasks**:
- Implement LDA using gensim
- Add BERTopic integration
- Create topic visualization tools
- Add topic assignment to bills table
- Create example scripts

#### 3. Add Fact-Checking Integration
**Status**: Open  
**Priority**: Medium  
**Description**: Integrate external fact-checking services to verify claims made in legislative text and speeches.
**Tasks**:
- Research available fact-checking APIs
- Implement ClaimBuster or similar API integration
- Create fact_checking.py module
- Add database tables for fact-check results
- Build verification workflow

#### 4. Create Visualization Dashboards
**Status**: Open  
**Priority**: High  
**Description**: Build interactive dashboards to visualize analysis results, trends, and patterns.
**Tasks**:
- Choose visualization framework (Plotly Dash, Streamlit, or React)
- Create bill similarity network visualization
- Build voting pattern heatmaps
- Add sentiment trend charts
- Implement legislator comparison tools

### Medium Term Goals

#### 5. Fine-tune BERT Models on Political Text
**Status**: Open  
**Priority**: Medium  
**Description**: Train custom BERT models specifically on political and legislative text for better accuracy.
**Tasks**:
- Collect and curate political text corpus
- Set up training infrastructure
- Fine-tune BERT base model
- Evaluate model performance
- Deploy fine-tuned models

#### 6. Add Argument Mining Capabilities
**Status**: Open  
**Priority**: Medium  
**Description**: Implement argument mining to extract claims, premises, and reasoning from legislative texts.
**Tasks**:
- Research argument mining frameworks
- Implement claim detection
- Build premise-conclusion linking
- Add argumentation structure visualization
- Create analysis tables for arguments

#### 7. Implement Real-time Analysis API
**Status**: Open  
**Priority**: High  
**Description**: Create a REST API for real-time analysis of legislative text and voting data.
**Tasks**:
- Design API endpoints and schemas
- Implement FastAPI or Flask application
- Add authentication and rate limiting
- Create API documentation (OpenAPI/Swagger)
- Deploy API service

#### 8. Create Alert System for Position Changes
**Status**: Open  
**Priority**: Medium  
**Description**: Build notification system to alert users when politicians change positions on issues.
**Tasks**:
- Design alert subscription system
- Implement change detection algorithms
- Add email/webhook notification support
- Create user preference management
- Build alert dashboard

### Long Term Goals

#### 9. Multi-lingual Support
**Status**: Open  
**Priority**: Low  
**Description**: Extend analysis capabilities to support multiple languages for international legislative bodies.
**Tasks**:
- Add multi-lingual NLP models
- Implement translation services
- Update database schema for language support
- Add language-specific analysis modules
- Create documentation for supported languages

#### 10. Advanced Network Analysis
**Status**: Open  
**Priority**: Medium  
**Description**: Implement sophisticated network analysis for legislator relationships and bill co-sponsorship patterns.
**Tasks**:
- Add NetworkX integration
- Build co-sponsorship network analysis
- Implement community detection algorithms
- Create network visualization tools
- Add centrality and influence metrics

#### 11. Predictive Modeling for Bill Passage
**Status**: Open  
**Priority**: Medium  
**Description**: Build machine learning models to predict likelihood of bill passage based on historical data.
**Tasks**:
- Collect historical bill outcome data
- Engineer relevant features
- Train classification models
- Evaluate prediction accuracy
- Deploy prediction service

#### 12. Integration with External Fact-Checking Services
**Status**: Open  
**Priority**: Low  
**Description**: Expand fact-checking capabilities with multiple external services and APIs.
**Tasks**:
- Integrate PolitiFact API
- Add FactCheck.org data
- Implement Snopes API if available
- Create unified fact-check aggregation
- Build confidence scoring system

## Dependencies & Technical Requirements

### Current Stack
- Python 3.8+
- PostgreSQL 12+
- spaCy, sentence-transformers, transformers
- Docker & Docker Compose

### Planned Additions
- FastAPI or Flask (for API)
- Plotly Dash or Streamlit (for dashboards)
- gensim (for topic modeling)
- NetworkX (for network analysis)
- Additional ML frameworks as needed

## Contributing

Contributors should:
1. Check this document for open project items
2. Review linked GitHub issues for detailed requirements
3. Follow the development workflow in TESTING.md
4. Update this document when completing items

## Related Documentation

- [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) - Current project architecture
- [IMPLEMENTATION_SUMMARY.md](docs/IMPLEMENTATION_SUMMARY.md) - Completed features
- [TESTING.md](TESTING.md) - Testing and development workflow
- [README.md](README.md) - Project overview and quick start

## Timeline

- **Q4 2024**: Complete short-term goals (items 1-4)
- **Q1-Q2 2025**: Complete medium-term goals (items 5-8)
- **Q3-Q4 2025**: Begin long-term goals (items 9-12)

## Contact & Support

For questions about the OpenDiscourse project or this repository:
- Repository Owner: cbwinslow
- Project Website: OpenDiscourse.net
- GitHub Issues: Use issue templates for bug reports and feature requests

---

*Last Updated: 2025-10-22*  
*Part of the OpenDiscourse.net project*
