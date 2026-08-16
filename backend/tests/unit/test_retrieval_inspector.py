import pytest
from app.features.retrieval.inspector import LanceInspector, RetrievalError

def test_inspector_uses_workspace_boundary_and_read_only(monkeypatch,tmp_path):
    root=tmp_path/"db"; root.mkdir()
    class FakeTable:
        def schema(self): return {"fields":[{"name":"text","type":"string"},{"name":"vector","type":"vector"}]}
    class FakeDB:
        def table_names(self): return ["docs"]
        def open_table(self,name): assert name=="docs"; return FakeTable()
    monkeypatch.setattr("app.features.retrieval.inspector.lancedb", type("L",(),{"connect":lambda path: FakeDB()}))
    inspector=LanceInspector(tmp_path)
    assert inspector.list_tables("db")==["docs"]
    assert inspector.describe("db","docs")["text_column"] == "text"
    with pytest.raises(RetrievalError): inspector.list_tables("../")

def test_inspector_fails_closed_for_missing_dependency(tmp_path,monkeypatch):
    monkeypatch.setattr("app.features.retrieval.inspector.lancedb", None)
    with pytest.raises(RetrievalError,match="LanceDB"):
        LanceInspector(tmp_path).list_tables("db")
