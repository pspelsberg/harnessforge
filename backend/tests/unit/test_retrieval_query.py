import pytest
from app.features.retrieval.query import LanceQueryRunner, RetrievalQueryError

class FakeQuery:
    def __init__(self, rows): self.rows=rows; self.k=None
    def limit(self,k): self.k=k; return self
    def to_list(self): return self.rows[:self.k]
class FakeTable:
    def __init__(self): self.last=None
    def search(self,vector): self.last=vector; return FakeQuery([{"text":"doc","_distance":0.1,"source":"x"}])
class FakeDB:
    def __init__(self): self.table=FakeTable()
    def open_table(self,name): assert name=="docs"; return self.table

def test_query_is_read_only_bounded_and_normalized(tmp_path,monkeypatch):
    (tmp_path/"db").mkdir(); db=FakeDB()
    monkeypatch.setattr("app.features.retrieval.query.lancedb",type("L",(),{"connect":lambda path,**kwargs:db}))
    result=LanceQueryRunner(tmp_path).search("db","docs",[0.1,0.2],top_k=1)
    assert result == [{"text":"doc","score":0.1,"metadata":{"source":"x"}}]
    assert db.table.last == [0.1,0.2]

def test_query_rejects_bad_vectors_and_limits(tmp_path):
    (tmp_path/"db").mkdir()
    with pytest.raises(RetrievalQueryError): LanceQueryRunner(tmp_path).search("db","docs",[],top_k=1)
    with pytest.raises(RetrievalQueryError): LanceQueryRunner(tmp_path).search("db","docs",[0.1],top_k=21)


def test_query_api_is_authenticated(tmp_path):
    from fastapi.testclient import TestClient
    from app.main import create_app
    client=TestClient(create_app(session_value="t",workspace=tmp_path))
    assert client.post("/api/retrieval/query",json={"path":"db","table":"docs","vector":[1]},headers={"host":"127.0.0.1"}).status_code==401


def test_query_rejects_non_finite_vectors(tmp_path):
    (tmp_path/"db").mkdir()
    with pytest.raises(RetrievalQueryError): LanceQueryRunner(tmp_path).search("db","docs",[float("nan")])


def test_query_supports_bounded_hybrid_search(tmp_path,monkeypatch):
    (tmp_path/"db").mkdir()
    class HybridQuery(FakeQuery):
        def vector(self, value): self.vector_value=value; return self
        def text(self, value): self.text_value=value; return self
    class HybridTable:
        def search(self, *args, **kwargs):
            assert kwargs.get("query_type")=="hybrid"
            return HybridQuery([{"text":"hybrid","score":0.2}])
    class HybridDB:
        def open_table(self,name): return HybridTable()
    monkeypatch.setattr("app.features.retrieval.query.lancedb",type("L",(),{"connect":lambda path,**kwargs:HybridDB()}))
    result=LanceQueryRunner(tmp_path).search("db","docs",[0.1],top_k=1,text_query="reference",hybrid=True)
    assert result[0]["text"]=="hybrid"
