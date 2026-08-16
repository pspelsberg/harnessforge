"""Intelligent LLM Graph Builder / Architect generator."""
from __future__ import annotations

import os
import re
import json
import logging
from typing import Any
import httpx
from app.features.graph_authoring.contracts import (
    ForgeGraph,
    GraphNode,
    GraphEdge,
    Position,
    NodeData,
    GraphSettings,
)
from app.features.graph_authoring.validator import validate_graph

logger = logging.getLogger(__name__)

GRAPH_SYSTEM_PROMPT = """You are the AI Graph Architect for HarnessForge.
Generate a strictly valid HarnessForge JSON graph based on the user's description.
Only output valid JSON with NO commentary or markdown codeblocks.

Available Node Types:
1. "start" - Initial input trigger. Config: {"input_key": "user_query", "default_query": "..."}
2. "rag" - LanceDB Vector Database Search. Config: {"path": ".lancedb", "table": "docs", "vector": [0.05, 0.12, 0.33, 0.45], "top_k": 5}. Use this for document search, RAG, knowledge retrieval! DO NOT use tool nodes for RAG.
3. "llm" - Language Model reasoning. Config: {"provider": "mistral"|"openai"|"anthropic"|"ollama", "model": "codestral-latest", "temperature": 0.2, "node_prompt": "Instructions with {variables}"}
4. "tool" - Local CLI command execution. Config: {"path": "pytest", "args": ["tests/"], "max_output_bytes": 51200}
5. "loop" - Conditional routing. Config: {"condition_type": "equals", "key": "exit_code", "value": "0", "max_iterations": 4, "fallback": "out-1"}.
   IMPORTANT: A loop node MUST have 3 outgoing edges with source_handle: "true", "false", and "fallback".
6. "output" - Final response sink. Config: {"format": "markdown", "target_sink": "result"}

Example Valid Schema:
{
  "schema_version": "1",
  "id": "generated-agent",
  "name": "Meaningful Name",
  "workspace_path": ".",
  "nodes": [
    {"id": "start-1", "type": "start", "position": {"x": 80, "y": 150}, "data": {"config": {"input_key": "task"}, "ui": {"status": "idle"}}},
    {"id": "rag-1", "type": "rag", "position": {"x": 320, "y": 150}, "data": {"config": {"path": ".lancedb", "table": "docs", "vector": [0.05, 0.12, 0.33, 0.45], "top_k": 5}, "ui": {"status": "idle"}}},
    {"id": "llm-1", "type": "llm", "position": {"x": 580, "y": 150}, "data": {"config": {"provider": "mistral", "model": "codestral-latest", "temperature": 0.2, "node_prompt": "Answer using {rag_context}"}, "ui": {"status": "idle"}}},
    {"id": "loop-1", "type": "loop", "position": {"x": 840, "y": 150}, "data": {"config": {"condition_type": "equals", "key": "quality_score", "value": "high", "max_iterations": 3, "fallback": "out-1"}, "ui": {"status": "idle"}}},
    {"id": "out-1", "type": "output", "position": {"x": 1100, "y": 150}, "data": {"config": {"format": "markdown"}, "ui": {"status": "idle"}}}
  ],
  "edges": [
    {"id": "e1", "source": "start-1", "target": "rag-1"},
    {"id": "e2", "source": "rag-1", "target": "llm-1"},
    {"id": "e3", "source": "llm-1", "target": "loop-1"},
    {"id": "e4", "source": "loop-1", "target": "out-1", "source_handle": "true"},
    {"id": "e5", "source": "loop-1", "target": "llm-1", "source_handle": "false"},
    {"id": "e6", "source": "loop-1", "target": "out-1", "source_handle": "fallback"}
  ],
  "settings": {"review_only": true, "external_dataflow_activated": false, "debug_mode": false, "retention_days": 30}
}
"""

def _derive_provider_for_model(model: str) -> str:
    m = model.lower()
    if "codestral" in m or "mistral" in m:
        return "mistral"
    if "claude" in m or "sonnet" in m or "opus" in m:
        return "anthropic"
    if "gpt-" in m or "openai" in m:
        return "openai"
    if "gemini" in m:
        return "openai"
    return "ollama"

def normalize_and_repair_graph(graph: ForgeGraph, default_model: str = "codestral-latest") -> ForgeGraph:
    """Ensure generated graph conforms strictly to all schema and semantic rules."""
    nodes = list(graph.nodes)
    edges = list(graph.edges)

    # 1. Normalize Nodes
    output_node_id = "out-1"
    for n in nodes:
        if n.type == "output":
            output_node_id = n.id

    for i, node in enumerate(nodes):
        cfg = dict(node.data.config)
        node_id = node.id.lower()

        # Fix mistaken RAG as tool node
        if node.type == "tool" and ("rag" in node_id or "lance" in str(cfg.get("path", "")).lower() or "search" in str(cfg.get("path", "")).lower() and "rag" in node_id):
            nodes[i] = node.model_copy(
                update={
                    "type": "rag",
                    "data": NodeData(
                        config={
                            "path": ".lancedb",
                            "table": "docs",
                            "vector": [0.05, 0.12, 0.33, 0.45],
                            "top_k": int(cfg.get("top_k", 5)),
                        },
                        ui=node.data.ui,
                    ),
                }
            )
            continue

        if node.type == "rag":
            if not isinstance(cfg.get("path"), str) or not cfg["path"]:
                cfg["path"] = ".lancedb"
            if not isinstance(cfg.get("table"), str) or not cfg["table"]:
                cfg["table"] = "docs"
            if not isinstance(cfg.get("vector"), list) or not cfg["vector"]:
                cfg["vector"] = [0.05, 0.12, 0.33, 0.45]
            if not isinstance(cfg.get("top_k"), int):
                cfg["top_k"] = 5
            nodes[i] = node.model_copy(update={"data": NodeData(config=cfg, ui=node.data.ui)})

        elif node.type == "llm":
            if not cfg.get("provider"):
                cfg["provider"] = _derive_provider_for_model(str(cfg.get("model", default_model)))
            if not cfg.get("model"):
                cfg["model"] = default_model
            if not cfg.get("node_prompt"):
                cfg["node_prompt"] = "Verarbeite die Eingabe und antworte strukturiert."
            if "temperature" not in cfg or not isinstance(cfg.get("temperature"), (int, float)):
                cfg["temperature"] = 0.2
            nodes[i] = node.model_copy(update={"data": NodeData(config=cfg, ui=node.data.ui)})

        elif node.type == "loop":
            if not isinstance(cfg.get("max_iterations"), int) or isinstance(cfg.get("max_iterations"), bool):
                cfg["max_iterations"] = 4
            if not cfg.get("condition_type") or cfg.get("condition_type") not in {"equals", "regex", "number", "exists"}:
                cfg["condition_type"] = "equals"
            if not cfg.get("key"):
                cfg["key"] = "exit_code"
            if "value" not in cfg:
                cfg["value"] = "0"
            if not cfg.get("fallback") or not isinstance(cfg.get("fallback"), str):
                cfg["fallback"] = output_node_id
            nodes[i] = node.model_copy(update={"data": NodeData(config=cfg, ui=node.data.ui)})

    # 2. Normalize Edges around Loop nodes
    loop_nodes = [n for n in nodes if n.type == "loop"]
    new_edges = list(edges)

    for loop in loop_nodes:
        loop_cfg = loop.data.config
        fallback_target = loop_cfg.get("fallback", output_node_id)
        
        loop_out_edges = [e for e in new_edges if e.source == loop.id]
        
        # Check handles
        has_true = any(e.source_handle == "true" for e in loop_out_edges)
        has_false = any(e.source_handle == "false" for e in loop_out_edges)
        has_fallback = any(e.source_handle == "fallback" for e in loop_out_edges)

        # If edges lack handle names, assign them intelligently
        if not has_true or not has_false or not has_fallback:
            # Remove unhandled outgoing edges from loop
            new_edges = [e for e in new_edges if e.source != loop.id]
            
            # Find a preceding node (for false loopback) and forward node (for true)
            preceding_llm = next((n.id for n in nodes if n.type in {"llm", "tool"}), "start-1")
            forward_out = output_node_id

            new_edges.append(GraphEdge(id=f"e-loop-{loop.id}-true", source=loop.id, target=forward_out, source_handle="true"))
            new_edges.append(GraphEdge(id=f"e-loop-{loop.id}-false", source=loop.id, target=preceding_llm, source_handle="false"))
            new_edges.append(GraphEdge(id=f"e-loop-{loop.id}-fallback", source=loop.id, target=fallback_target, source_handle="fallback"))

    return graph.model_copy(update={"nodes": nodes, "edges": new_edges})


def synthesize_fallback_graph(prompt: str, model_name: str = "codestral-latest") -> ForgeGraph:
    """Deterministic, high-quality heuristic graph synthesizer."""
    p = prompt.lower()
    clean_model = model_name if model_name else "codestral-latest"
    provider = _derive_provider_for_model(clean_model)

    # 1. RAG pipeline requested
    if any(k in p for k in ["rag", "lancedb", "vektor", "vector", "dokument", "wissen", "knowledge", "search"]):
        name = "LanceDB RAG Assistant"
        nodes = [
            GraphNode(
                id="start-1",
                type="start",
                position=Position(x=80, y=150),
                data=NodeData(config={"input_key": "user_query", "default_query": prompt[:120]}, ui={"status": "idle"}),
            ),
            GraphNode(
                id="rag-1",
                type="rag",
                position=Position(x=320, y=150),
                data=NodeData(config={"path": ".lancedb", "table": "docs", "vector": [0.05, 0.12, 0.33, 0.45], "top_k": 5}, ui={"status": "idle"}),
            ),
            GraphNode(
                id="llm-1",
                type="llm",
                position=Position(x=600, y=150),
                data=NodeData(
                    config={
                        "provider": provider,
                        "model": clean_model,
                        "temperature": 0.3,
                        "node_prompt": f"Du bist ein intelligenter RAG-Assistent. Beantworte die Anfrage präzise anhand des LanceDB-Kontexts:\n\nKontext:\n{{rag_context}}\n\nBenutzer-Anfrage:\n{{user_query}}\n\nFokus:\n{prompt}",
                    },
                    ui={"status": "idle"},
                ),
            ),
            GraphNode(
                id="out-1",
                type="output",
                position=Position(x=880, y=150),
                data=NodeData(config={"format": "markdown", "target_sink": "chat_stream"}, ui={"status": "idle"}),
            ),
        ]
        edges = [
            GraphEdge(id="e1", source="start-1", target="rag-1"),
            GraphEdge(id="e2", source="rag-1", target="llm-1"),
            GraphEdge(id="e3", source="llm-1", target="out-1"),
        ]

    # 2. ReAct / Loop / Tool / Fixer requested
    elif any(k in p for k in ["loop", "schleife", "react", "tool", "pytest", "test", "fix", "code", "coder", "refactor"]):
        name = "Self-Healing ReAct Agent"
        nodes = [
            GraphNode(
                id="start-1",
                type="start",
                position=Position(x=80, y=150),
                data=NodeData(config={"input_key": "task", "default_query": prompt[:120]}, ui={"status": "idle"}),
            ),
            GraphNode(
                id="llm-1",
                type="llm",
                position=Position(x=320, y=150),
                data=NodeData(
                    config={
                        "provider": provider,
                        "model": clean_model,
                        "temperature": 0.2,
                        "node_prompt": f"Du bist ein autonomer Coding-Agent. Erstelle oder repariere den Code:\n\nAufgabe: {prompt}\nTest-Log: {{test_output}}\nDateien: {{workspace_files}}\n\nSchreibe die vollständige Lösung.",
                    },
                    ui={"status": "idle"},
                ),
            ),
            GraphNode(
                id="tool-1",
                type="tool",
                position=Position(x=600, y=150),
                data=NodeData(config={"path": "pytest", "args": ["tests/", "-q", "--tb=short"], "max_output_bytes": 51200}, ui={"status": "idle"}),
            ),
            GraphNode(
                id="loop-1",
                type="loop",
                position=Position(x=880, y=150),
                data=NodeData(config={"condition_type": "equals", "key": "exit_code", "value": "0", "max_iterations": 4, "fallback": "out-1"}, ui={"status": "idle"}),
            ),
            GraphNode(
                id="out-1",
                type="output",
                position=Position(x=1180, y=150),
                data=NodeData(config={"format": "markdown", "return_fields": ["code_fix", "exit_code", "iterations"]}, ui={"status": "idle"}),
            ),
        ]
        edges = [
            GraphEdge(id="e1", source="start-1", target="llm-1"),
            GraphEdge(id="e2", source="llm-1", target="tool-1"),
            GraphEdge(id="e3", source="tool-1", target="loop-1"),
            GraphEdge(id="e4", source="loop-1", target="out-1", source_handle="true"),
            GraphEdge(id="e5", source="loop-1", target="llm-1", source_handle="false"),
            GraphEdge(id="e6", source="loop-1", target="out-1", source_handle="fallback"),
        ]

    # 3. Multi-Step Chain / General Agent
    else:
        name = "Custom Multi-Step Agent"
        nodes = [
            GraphNode(
                id="start-1",
                type="start",
                position=Position(x=80, y=150),
                data=NodeData(config={"input_key": "input", "default_query": prompt[:120]}, ui={"status": "idle"}),
            ),
            GraphNode(
                id="llm-1",
                type="llm",
                position=Position(x=320, y=150),
                data=NodeData(
                    config={
                        "provider": provider,
                        "model": clean_model,
                        "temperature": 0.3,
                        "node_prompt": f"Schritt 1 (Planung & Analyse):\n\nAufgabe: {prompt}\nInput: {{input}}\n\nErstelle einen strukturierten Ausführungsplan.",
                    },
                    ui={"status": "idle"},
                ),
            ),
            GraphNode(
                id="llm-2",
                type="llm",
                position=Position(x=600, y=150),
                data=NodeData(
                    config={
                        "provider": provider,
                        "model": clean_model,
                        "temperature": 0.2,
                        "node_prompt": f"Schritt 2 (Ausführung & Synthese):\n\nPlan: {{plan}}\nGeneriere das finale Resultat für: {prompt}",
                    },
                    ui={"status": "idle"},
                ),
            ),
            GraphNode(
                id="out-1",
                type="output",
                position=Position(x=880, y=150),
                data=NodeData(config={"format": "markdown", "target_sink": "result"}, ui={"status": "idle"}),
            ),
        ]
        edges = [
            GraphEdge(id="e1", source="start-1", target="llm-1"),
            GraphEdge(id="e2", source="llm-1", target="llm-2"),
            GraphEdge(id="e3", source="llm-2", target="out-1"),
        ]

    graph = ForgeGraph(
        schema_version="1",
        id=f"ai-{re.sub(r'[^a-zA-Z0-9_-]', '-', name.lower())[:32]}",
        name=name,
        workspace_path=".",
        nodes=nodes,
        edges=edges,
        settings=GraphSettings(review_only=True),
    )
    return normalize_and_repair_graph(graph, clean_model)


async def generate_graph_from_prompt(prompt: str, model_name: str = "codestral-latest") -> ForgeGraph:
    """Generate a valid ForgeGraph by querying Mistral Native API, local Ollama, or falling back to synthesis."""
    if not prompt or len(prompt.strip()) == 0:
        raise ValueError("Prompt cannot be empty")

    clean_model = model_name.strip() if model_name else "codestral-latest"
    mistral_key = os.environ.get("MISTRAL_API_KEY")

    # 1. Native Mistral API call if Mistral model or MISTRAL_API_KEY available
    if mistral_key and ("mistral" in clean_model.lower() or "codestral" in clean_model.lower()):
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.post(
                    "https://api.mistral.ai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {mistral_key}"},
                    json={
                        "model": clean_model if ("mistral" in clean_model or "codestral" in clean_model) else "codestral-latest",
                        "messages": [
                            {"role": "system", "content": GRAPH_SYSTEM_PROMPT},
                            {"role": "user", "content": f"Create a HarnessForge graph for: {prompt}"},
                        ],
                        "response_format": {"type": "json_object"},
                    },
                )
                if res.status_code == 200:
                    body = res.json()
                    content = body.get("choices", [{}])[0].get("message", {}).get("content", "")
                    if content:
                        parsed = json.loads(content)
                        raw_graph = ForgeGraph.model_validate(parsed)
                        repaired = normalize_and_repair_graph(raw_graph, clean_model)
                        val = validate_graph(repaired)
                        if val.valid:
                            return repaired
        except Exception as exc:
            logger.info(f"Mistral API generation error ({exc}), falling back.")

    # 2. Local Ollama call if available on 127.0.0.1:11434
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.post(
                "http://127.0.0.1:11434/api/chat",
                json={
                    "model": clean_model,
                    "messages": [
                        {"role": "system", "content": GRAPH_SYSTEM_PROMPT},
                        {"role": "user", "content": f"Create a HarnessForge graph for: {prompt}"},
                    ],
                    "stream": False,
                    "format": "json",
                },
            )
            if res.status_code == 200:
                body = res.json()
                content = body.get("message", {}).get("content", "")
                if content:
                    parsed = json.loads(content)
                    raw_graph = ForgeGraph.model_validate(parsed)
                    repaired = normalize_and_repair_graph(raw_graph, clean_model)
                    val = validate_graph(repaired)
                    if val.valid:
                        return repaired
    except Exception as exc:
        logger.info(f"Ollama generation skipped or failed ({exc}), using intelligent graph synthesizer.")

    # 3. Intelligent fallback synthesis
    graph = synthesize_fallback_graph(prompt, clean_model)
    val = validate_graph(graph)
    if not val.valid:
        raise ValueError(f"Synthesized graph invalid: {val.issues}")
    return graph
