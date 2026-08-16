import pytest
from pydantic import ValidationError
from app.features.execution.api_models import RunRequest
from app.features.retrieval.api_models import RetrievalRequest
from app.features.export.api_models import ExportRequest

def test_dtos_forbid_unknown_fields_and_bound_inputs():
    with pytest.raises(ValidationError): RunRequest(graph={},query="x",extra="bad")
    with pytest.raises(ValidationError): RetrievalRequest(path="db",table="docs",vector=[],top_k=21)
    with pytest.raises(ValidationError): ExportRequest(graph={},destination="../escape")


def test_run_query_rejects_control_characters_and_huge_bindings():
    with pytest.raises(ValidationError): RunRequest(graph={},query="\x00")
