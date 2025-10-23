# [OpenDiscourse] Integration with External Fact-Checking Services

**Project Item Category**: Long Term

**Priority**: Low

**Estimated Effort**: Medium (1-2 weeks)

## Description

Expand fact-checking capabilities with multiple external services and APIs to provide comprehensive verification of claims made in legislative discourse. This builds upon the initial fact-checking integration to create a robust, multi-source verification system.

## Tasks

- [ ] Integrate PolitiFact API or scraper
- [ ] Add FactCheck.org data access
- [ ] Implement Snopes API integration (if available)
- [ ] Add Washington Post Fact Checker integration
- [ ] Create unified fact-check aggregation system
- [ ] Build confidence scoring based on multiple sources
- [ ] Implement claim matching across sources
- [ ] Add fact-check history tracking
- [ ] Create controversy detection (conflicting fact-checks)
- [ ] Build fact-check reputation system
- [ ] Add citation and source linking
- [ ] Implement caching to respect rate limits
- [ ] Create fact-check dashboard
- [ ] Write comprehensive documentation

## Dependencies

- APIs or scrapers for fact-checking services:
  - PolitiFact
  - FactCheck.org
  - Snopes
  - Washington Post Fact Checker
  - AP Fact Check
- `requests` or `scrapy` for web scraping
- Database tables: `fact_check_sources`, `fact_check_ratings`, `source_reputation`
- Caching system (Redis) for rate limiting

## Success Criteria

- System aggregates fact-checks from 3+ sources
- Claim matching works across different phrasings
- Confidence scores are accurate and useful
- Conflicting fact-checks are identified
- System respects rate limits and ToS
- Database efficiently stores multi-source data
- API provides unified fact-check results
- Documentation includes ethical guidelines

## Related Documentation

- [OPENDISCOURSE_PROJECT.md](../../OPENDISCOURSE_PROJECT.md#12-integration-with-external-fact-checking-services)
- [.github/project-issues/03-fact-checking.md](03-fact-checking.md) (builds on this)

## Additional Context

Fact-checking sources:

1. **PolitiFact** (Poynter Institute)
   - Ratings: True, Mostly True, Half True, Mostly False, False, Pants on Fire
   - Covers politicians, speeches, ads

2. **FactCheck.org** (Annenberg Public Policy Center)
   - Non-partisan, academic approach
   - Detailed analysis articles

3. **Washington Post Fact Checker**
   - Pinocchio rating system (1-4 Pinocchios)
   - Database of false claims

4. **Snopes**
   - Broad coverage including political claims
   - True/False/Mixture ratings

5. **AP Fact Check**
   - Associated Press credibility
   - Covers major political statements

Aggregation strategy:
```python
claim = "Tax cuts increased revenue"

Sources:
- PolitiFact: "Mostly False" (confidence: 0.8)
- FactCheck.org: "Misleading" (confidence: 0.9)  
- WaPo: "3 Pinocchios" (confidence: 0.85)

Aggregated Result:
- Overall: "False"
- Confidence: 0.85 (weighted average)
- Consensus: 3/3 sources agree claim is false
```

Challenges:
- Different rating scales across sources
- Claims phrased differently
- Time-sensitive context
- Rate limiting and API costs
- Website scraping reliability
- Copyright and fair use

Ethical guidelines:
- Present all source ratings, not just aggregate
- Link to original fact-check articles
- Indicate when sources disagree
- Update ratings as new fact-checks emerge
- Clearly state limitations
- Respect source attribution

Database schema:
```sql
fact_check_sources (
  id, name, url, reputation_score
)

fact_check_ratings (
  id, claim_id, source_id, rating, 
  confidence, url, checked_date
)

claim_matches (
  claim_id, text, canonical_text,
  source_claim_id
)
```
