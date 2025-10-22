# [OpenDiscourse] Add Fact-Checking Integration

**Project Item Category**: Short Term

**Priority**: Medium

**Estimated Effort**: Medium (1-2 weeks)

## Description

Integrate external fact-checking services to verify claims made in legislative text and speeches. This will help identify verifiable statements and provide evidence-based analysis of legislative discourse.

## Tasks

- [ ] Research available fact-checking APIs (ClaimBuster, Google Fact Check, etc.)
- [ ] Implement ClaimBuster API integration for claim detection
- [ ] Create `analysis/fact_checking.py` module
- [ ] Add database tables for fact-check results and claims
- [ ] Implement claim extraction from legislative text
- [ ] Add verification workflow to link claims with fact-check sources
- [ ] Create visualization for fact-check confidence scores
- [ ] Add example script `examples/fact_checking_example.py`
- [ ] Update documentation with fact-checking capabilities

## Dependencies

- ClaimBuster API or similar service
- `requests` library (already installed)
- API keys for fact-checking services
- Database tables: `claims`, `fact_checks`, `claim_sources`

## Success Criteria

- System can identify checkable claims in legislative text
- Claims are successfully matched with fact-check databases
- Fact-check results are stored with confidence scores
- API integration is robust with error handling
- Documentation includes usage examples and API setup
- Privacy and rate limiting considerations are addressed

## Related Documentation

- [OPENDISCOURSE_PROJECT.md](../../OPENDISCOURSE_PROJECT.md#3-add-fact-checking-integration)
- [docs/ANALYSIS_MODULES.md](../../docs/ANALYSIS_MODULES.md)

## Additional Context

Potential fact-checking services:
- **ClaimBuster**: Claims detection API (http://idir.uta.edu/claimbuster/)
- **Google Fact Check Tools API**: Aggregates fact-checks from multiple sources
- **FactCheck.org**: May have API or structured data available

Ethical considerations:
- Clearly indicate confidence levels
- Cite original fact-checking sources
- Respect rate limits and terms of service
- Handle controversial claims carefully
