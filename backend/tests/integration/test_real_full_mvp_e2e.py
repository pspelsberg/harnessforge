import json, subprocess, sys, threading, asyncio
from http.server import BaseHTTPRequestHandler, HTTPServer
import lancedb
from app.features.graph_authoring.contracts import ForgeGraph,GraphNode,GraphEdge
from app.features.execution.services import build_services
from app.features.execution.engine import GraphRunner,RunState
from app.features.tool_execution.runner import ToolRunner,ToolSpec

def n(i,t,c=None): return GraphNode(id=i,type=t,position={"x":0,"y":0},data={"config":c or {},"ui":{}})
class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length=int(self.headers.get("content-length",0)); body=json.loads(self.rfile.read(length)); assert body["stream"] is True
        payload=json.dumps({"choices":[{"delta":{"content":"model"},"finish_reason":"stop"}]}).encode()
        self.send_response(200); self.send_header("content-type","text/event-stream"); self.send_header("content-length",str(len(payload)+len(b"data: \n\n"))); self.end_headers(); self.wfile.write(b"data: "+payload+b"\n\ndata: [DONE]\n\n")
    def log_message(self,*args): pass

def test_real_lance_provider_loop_tool_output(tmp_path):
    db=lancedb.connect(str(tmp_path/"db")); db.create_table("docs",data=[{"text":"reference","vector":[1.0,0.0]}])
    (tmp_path/"tool.py").write_text("print('real-tool')")
    tool_runner=ToolRunner(tmp_path); approved=tool_runner.config_hash(ToolSpec(path="tool.py",args=[],timeout_seconds=15,allowed_write_dirs=[],env_allowlist=[]))
    server=HTTPServer(("127.0.0.1",0),Handler); thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
    try:
        nodes=[n("s","start"),n("r","rag",{"path":"db","table":"docs","vector":[1.0,0.0],"top_k":1}),n("l","llm",{"provider":{"kind":"local_openai","base_url":f"http://127.0.0.1:{server.server_port}/v1","model":"x","timeout_seconds":2},"node_prompt":"{query}"}),n("loop","loop",{"condition_type":"equals","key":"last_output","value":"model","max_iterations":3,"fallback":"tool"}),n("tool","tool",{"path":"tool.py","args":[],"approved_hash":approved}),n("o","output")]
        edges=[GraphEdge(id="1",source="s",target="r"),GraphEdge(id="2",source="r",target="l"),GraphEdge(id="3",source="l",target="loop"),GraphEdge(id="4",source="loop",target="tool",source_handle="true"),GraphEdge(id="5",source="loop",target="tool",source_handle="false"),GraphEdge(id="6",source="loop",target="tool",source_handle="fallback"),GraphEdge(id="7",source="tool",target="o")]
        graph=ForgeGraph(id="real-e2e",name="real",workspace_path=str(tmp_path),settings={"review_only":False,"external_dataflow_activated":False},nodes=nodes,edges=edges)
        services=build_services(graph,tmp_path)
        result=asyncio.run(GraphRunner(graph,services=services).run(query="hello"))
        assert result.status is RunState.SUCCEEDED and result.state.retrieved_context[0]["text"]=="reference" and result.state.last_output=="real-tool\n"
    finally:
        server.shutdown(); thread.join(timeout=2)
