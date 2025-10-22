# [OpenDiscourse] Implement Real-time Analysis API

**Project Item Category**: Medium Term

**Priority**: High

**Estimated Effort**: Large (> 2 weeks)

## Description

Create a REST API for real-time analysis of legislative text and voting data. This will enable external applications, journalists, and researchers to access OpenDiscourse analysis capabilities programmatically.

## Tasks

- [ ] Design API endpoints and schemas (REST/GraphQL)
- [ ] Implement FastAPI application structure
- [ ] Add authentication (JWT tokens, API keys)
- [ ] Implement rate limiting per user/key
- [ ] Create endpoints for all analysis modules:
  - [ ] `/api/embeddings/generate` - Generate embeddings
  - [ ] `/api/embeddings/similar` - Find similar bills
  - [ ] `/api/sentiment/analyze` - Analyze sentiment
  - [ ] `/api/entities/extract` - Extract entities
  - [ ] `/api/bias/detect` - Detect bias
  - [ ] `/api/consistency/analyze` - Analyze consistency
- [ ] Add real-time processing queue (Celery or similar)
- [ ] Implement caching layer (Redis)
- [ ] Create OpenAPI/Swagger documentation
- [ ] Add monitoring and logging
- [ ] Implement error handling and validation
- [ ] Write API tests (unit and integration)
- [ ] Deploy API service (Docker, Kubernetes)
- [ ] Set up CI/CD pipeline

## Dependencies

- `fastapi` - Modern Python web framework
- `uvicorn` - ASGI server
- `pydantic` - Data validation
- `python-jose` - JWT authentication
- `redis` - Caching layer
- `celery` - Async task queue
- `pytest` - Testing framework
- Docker & Kubernetes for deployment

## Success Criteria

- API is accessible and performant (< 200ms p95)
- Authentication and rate limiting work correctly
- All analysis endpoints return accurate results
- OpenAPI documentation is complete and accurate
- API handles errors gracefully
- Monitoring shows system health
- Test coverage > 80%
- API is deployed and accessible
- Usage documentation is clear

## Related Documentation

- [OPENDISCOURSE_PROJECT.md](../../OPENDISCOURSE_PROJECT.md#7-implement-real-time-analysis-api)
- [analysis/](../../analysis/) - All analysis modules
- [docs/API_ENDPOINTS.md](../../docs/API_ENDPOINTS.md)

## Additional Context

Example API usage:
```bash
# Analyze sentiment of bill text
curl -X POST https://api.opendiscourse.net/v1/sentiment/analyze \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "This bill will reform healthcare...",
    "text_id": "hr-1234-118",
    "text_type": "bill"
  }'

Response:
{
  "sentiment_label": "positive",
  "compound_score": 0.72,
  "positive_score": 0.65,
  "negative_score": 0.10,
  "neutral_score": 0.25
}
```

API design principles:
- RESTful conventions
- Versioned endpoints (/v1/, /v2/)
- Consistent error responses
- Rate limiting headers
- Pagination for list endpoints
- Webhook support for async operations
