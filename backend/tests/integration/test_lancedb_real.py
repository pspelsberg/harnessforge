import pytest
from app.features.retrieval.inspector import LanceInspector
from app.features.retrieval.query import LanceQueryRunner

def test_real_lancedb_read_only_inspection_and_query(tmp_path):
    lancedb=pytest.importorskip("lancedb"); db_path=tmp_path/"db"; db=lancedb.connect(str(db_path)); db.create_table("docs",data=[{"text":"hello","vector":[1.0,0.0],"source":"test"}])
    inspector=LanceInspector(tmp_path); assert "docs" in inspector.list_tables("db")
    description=inspector.describe("db","docs"); assert description["text_column"]=="text" and description["vector_column"]=="vector"
    results=LanceQueryRunner(tmp_path).search("db","docs",[1.0,0.0],top_k=1); assert results[0]["text"]=="hello"
