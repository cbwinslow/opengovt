# [OpenDiscourse] Add Specialized Embedding Models for Legal Text

**Project Item Category**: Short Term

**Priority**: High

**Estimated Effort**: Medium (1-2 weeks)

## Description

Implement specialized embedding models trained on legal and legislative text to improve similarity search and clustering accuracy. Current models use general-purpose sentence transformers, but legal text has unique vocabulary and structure that specialized models can better capture.

## Tasks

- [ ] Research available legal text embedding models (Legal-BERT, Case-Law-BERT, etc.)
- [ ] Evaluate performance of legal-BERT and similar models on sample legislative text
- [ ] Implement model switching capability in `analysis/embeddings.py`
- [ ] Add configuration options for model selection
- [ ] Benchmark new models against current models (all-MiniLM-L6-v2, all-mpnet-base-v2)
- [ ] Update database schema if needed for larger embedding dimensions
- [ ] Update documentation with new model options
- [ ] Add example usage in `examples/embeddings_example.py`

## Dependencies

- `transformers` library (already installed)
- Legal-BERT or similar pre-trained models from HuggingFace
- GPU recommended for fine-tuning (if needed)

## Success Criteria

- Legal text embeddings show improved similarity scores for related bills
- Model can be easily switched via configuration
- Documentation includes comparison of available models
- Tests pass with new models
- No breaking changes to existing API

## Related Documentation

- [OPENDISCOURSE_PROJECT.md](../../OPENDISCOURSE_PROJECT.md#1-add-specialized-embedding-models-for-legal-text)
- [analysis/embeddings.py](../../analysis/embeddings.py)
- [docs/ANALYSIS_MODULES.md](../../docs/ANALYSIS_MODULES.md)

## Additional Context

Legal-BERT models available on HuggingFace:
- `nlpaueb/legal-bert-base-uncased`
- `zlucia/custom-legalbert`
- `saibo/legal-roberta-base`

These models are pre-trained on legal documents and may provide better embeddings for legislative text compared to general-purpose models.
