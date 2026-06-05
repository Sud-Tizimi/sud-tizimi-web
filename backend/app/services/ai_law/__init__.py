"""SudAI-Law-UZ legal document analysis services.

Ported from the standalone ``sudai-research-raw`` MVP. All seven modules
form a small pipeline:

    pipeline.analyze_document / analyze_text
        └─ anonymizer          (PII/PHI redaction)
        └─ classifier          (legal category + document type)
        └─ extractor           (legal objects: claimant, contract #, etc.)
        └─ rag.retrieve_sources(matched laws & articles)
        └─ reasoner            (human-readable explanation + recommendation)

Public entry points live in :mod:`app.services.ai_law.pipeline`.
Aggregation of multiple document analyses into a single case-level
result lives in :mod:`app.services.ai_law.aggregator`.
"""
from app.services.ai_law.pipeline import analyze_document, analyze_text

__all__ = ["analyze_document", "analyze_text"]
