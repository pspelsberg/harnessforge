import { create } from "zustand";
import {canConnect} from "./connectionRules";
export type NodeType = "start"|"llm"|"rag"|"loop"|"reducer"|"tool"|"output";
export type ForgeNode = { id:string; type:NodeType; position:{x:number;y:number}; data:{config:Record<string,unknown>;ui:Record<string,unknown>} };
export type ForgeEdge = { id:string; source:string; target:string; sourceHandle?:string; targetHandle?:string };
export type ValidationIssue={severity:"error"|"warning"|"info";message:string;nodeId?:string};
export const MAX_NODES=50; export const MAX_EDGES=200; export const RECOVERY_KEY="harnessforge.graph.recovery";
export function importGraphJson(raw:string): {nodes:ForgeNode[];edges:ForgeEdge[];reviewOnly:true} {
  if(raw.length>2_000_000) throw new Error("graph payload too large"); let parsed:unknown; try{parsed=JSON.parse(raw)}catch{throw new Error("invalid graph JSON")};
  if(!parsed||typeof parsed!=="object"||((parsed as {schema_version?:unknown}).schema_version!=="1")||!Array.isArray((parsed as {nodes?:unknown}).nodes)||!Array.isArray((parsed as {edges?:unknown}).edges)) throw new Error("invalid graph shape");
  const graph=parsed as {nodes:unknown[];edges:unknown[]}; if(graph.nodes.length>MAX_NODES||graph.edges.length>MAX_EDGES) throw new Error("graph limits exceeded");
  const types=new Set<NodeType>(["start","llm","rag","loop","reducer","tool","output"]);
  const validateJson=(value:unknown,depth=0):void=>{if(depth>8)throw new Error("value nesting is too deep");if(value===null||typeof value==="boolean"||(typeof value==="string"&&new TextEncoder().encode(value).byteLength<=128*1024)||(typeof value==="number"&&Number.isFinite(value)))return;if(Array.isArray(value)){if(value.length>128)throw new Error("list too large");value.forEach(v=>validateJson(v,depth+1));return}if(typeof value==="object"){const entries=Object.entries(value as Record<string,unknown>);if(entries.length>64)throw new Error("object too large");entries.forEach(([key,v])=>{if(key.length>128)throw new Error("key too long");validateJson(v,depth+1)});return}throw new Error("invalid JSON value")};
  const containsForbiddenKey=(value:unknown):boolean=>{
    if(Array.isArray(value))return value.some(containsForbiddenKey);
    if(value&&typeof value==="object")return Object.entries(value as Record<string,unknown>).some(([key,item])=>/^(?:__proto__|constructor|prototype)$/.test(key)||/(api[_-]?key|secret|password|token|authorization)/i.test(key)||containsForbiddenKey(item));
    return false;
  };
  const nodes=graph.nodes.map((node):ForgeNode=>{if(!node||typeof node!=="object")throw new Error("invalid node");const n=node as Partial<ForgeNode>;if(typeof n.id!=="string"||!/^[A-Za-z0-9._-]{1,128}$/.test(n.id)||!types.has(n.type as NodeType)||!n.position||typeof n.position.x!=="number"||typeof n.position.y!=="number"||!Number.isFinite(n.position.x)||!Number.isFinite(n.position.y)||Math.abs(n.position.x)>1000000||Math.abs(n.position.y)>1000000||!n.data||typeof n.data!=="object")throw new Error("invalid node");const data=n.data as Partial<ForgeNode["data"]>;if(!data.config||!data.ui||typeof data.config!=="object"||Array.isArray(data.config)||typeof data.ui!=="object"||Array.isArray(data.ui))throw new Error("invalid node data");if(containsForbiddenKey(data.config))throw new Error("secret-shaped configuration is forbidden");validateJson(data.config);validateJson(data.ui);return n as ForgeNode});
  if(new Set(nodes.map(n=>n.id)).size!==nodes.length) throw new Error("duplicate node id"); const ids=new Set(nodes.map(n=>n.id));
  const edges=graph.edges.map((edge):ForgeEdge=>{if(!edge||typeof edge!=="object")throw new Error("invalid edge");const e=edge as Partial<ForgeEdge>;if(typeof e.id!=="string"||!/^[A-Za-z0-9._-]{1,128}$/.test(e.id)||typeof e.source!=="string"||typeof e.target!=="string"||!ids.has(e.source)||!ids.has(e.target))throw new Error("invalid edge");return e as ForgeEdge});
  if(new Set(edges.map(e=>e.id)).size!==edges.length) throw new Error("duplicate edge id"); return {nodes,edges,reviewOnly:true};
}
export function validateGraph(nodes:ForgeNode[],edges:ForgeEdge[]):ValidationIssue[]{
 const issues:ValidationIssue[]=[];
 const ids=new Set(nodes.map(n=>n.id));
 const outgoing=new Map<string,ForgeEdge[]>();
 for(const node of nodes)outgoing.set(node.id,[]);
 for(const edge of edges){
  if(!ids.has(edge.source)||!ids.has(edge.target)){issues.push({severity:"error",message:"edge references an unknown node"});continue;}
  outgoing.get(edge.source)!.push(edge);
 }
 const starts=nodes.filter(n=>n.type==="start"),outputs=nodes.filter(n=>n.type==="output");
 if(starts.length!==1)issues.push({severity:"error",message:"exactly one start node required"});
 if(outputs.length!==1)issues.push({severity:"error",message:"exactly one output node required"});
 const reachable=new Set<string>(),stack=starts.map(n=>n.id);
 while(stack.length){const id=stack.pop()!;if(reachable.has(id))continue;reachable.add(id);for(const edge of outgoing.get(id)||[])stack.push(edge.target);}
 nodes.filter(n=>!reachable.has(n.id)).forEach(n=>issues.push({severity:"error",message:"unreachable node",nodeId:n.id}));
 const visiting:string[]=[],visited=new Set<string>();
 const walk=(id:string)=>{const cycleIndex=visiting.indexOf(id);if(cycleIndex>=0){if(!visiting.slice(cycleIndex).some(member=>nodes.find(n=>n.id===member)?.type==="loop"))issues.push({severity:"error",message:"cycles require a loop node",nodeId:id});return;}if(visited.has(id))return;visiting.push(id);for(const edge of outgoing.get(id)||[])walk(edge.target);visiting.pop();visited.add(id);};
 if(starts.length===1)walk(starts[0].id);
 for(const node of nodes){
  const config=node.data.config;
  if(node.type==="output"&&outgoing.get(node.id)!.length)issues.push({severity:"error",message:"output node must be terminal",nodeId:node.id});
  if(node.type==="llm"&&!config.provider)issues.push({severity:"warning",message:"LLM provider is not configured",nodeId:node.id});
  if((node.type==="rag"||node.type==="tool")&&(typeof config.path!=="string"||!config.path))issues.push({severity:"error",message:"referenced path is missing",nodeId:node.id});
  if(node.type==="loop"){
   const loopEdges=outgoing.get(node.id)||[], handles=new Set(loopEdges.map(e=>e.sourceHandle));
   if(!["true","false","fallback"].every(handle=>handles.has(handle)))issues.push({severity:"error",message:"loop requires true, false, and fallback routes",nodeId:node.id});
   if(typeof config.max_iterations!=="number"||!Number.isInteger(config.max_iterations)||config.max_iterations<1||config.max_iterations>50)issues.push({severity:"error",message:"loop max_iterations must be 1..50",nodeId:node.id});
   if(!["equals","regex","number","exists"].includes(String(config.condition_type)))issues.push({severity:"error",message:"loop condition is not declarative",nodeId:node.id});
   if(typeof config.fallback!=="string"||!loopEdges.some(e=>e.sourceHandle==="fallback"&&e.target===config.fallback))issues.push({severity:"error",message:"loop requires a valid fallback route",nodeId:node.id});
  }
 }
 return issues;
}
type Snapshot={nodes:ForgeNode[];edges:ForgeEdge[]}; type GraphState=Snapshot&{reviewOnly:boolean;externalDataflowActivated:boolean;selectedNodeId:string|null;history:Snapshot[];future:Snapshot[];setSelected:(id:string|null)=>void;updateConfig:(id:string,config:Record<string,unknown>)=>boolean;setExternalDataflow:(value:boolean)=>void;setGraph:(nodes:ForgeNode[],edges:ForgeEdge[])=>void;addNode:(type:NodeType)=>ForgeNode|null;connectNodes:(source:string,target:string,sourceHandle?:string)=>boolean;removeNode:(id:string)=>boolean;updatePosition:(id:string,position:{x:number;y:number})=>boolean;setNodeStatus:(id:string,status:"idle"|"running"|"success"|"error")=>boolean;duplicateNode:(id:string)=>ForgeNode|null;deleteSelected:()=>boolean;undo:()=>void;redo:()=>void;setReviewOnly:(value:boolean)=>void;recover:()=>void};
const snap=()=>{const s=useGraphStore.getState();return {nodes:s.nodes,edges:s.edges}};
export const useGraphStore=create<GraphState>((set,get)=>({nodes:[],edges:[],reviewOnly:true,externalDataflowActivated:false,selectedNodeId:null,history:[],future:[],setGraph:(nodes,edges)=>{const current=snap();set({nodes,edges,externalDataflowActivated:false,history:[...get().history,current].slice(-50),future:[]});try{localStorage.setItem(RECOVERY_KEY,JSON.stringify({schema_version:"1",nodes,edges}))}catch{}},addNode:(type)=>{const state=get();if(state.nodes.length>=MAX_NODES)return null;const base=`${type}-${Date.now()}`;let id=base;let suffix=1;while(state.nodes.some(node=>node.id===id))id=`${base}-${suffix++}`;const node:ForgeNode={id,type,position:{x:100+state.nodes.length*20,y:100+state.nodes.length*20},data:{config:{},ui:{}}};state.setGraph([...state.nodes,node],state.edges);return node},connectNodes:(source,target,sourceHandle)=>{const state=get();const sourceNode=state.nodes.find(node=>node.id===source),targetNode=state.nodes.find(node=>node.id===target);if(!sourceNode||!targetNode||!canConnect(sourceNode,targetNode,state.edges)||state.edges.length>=MAX_EDGES||state.edges.some(edge=>edge.source===source&&edge.target===target&&edge.sourceHandle===sourceHandle))return false;const next=[...state.edges,{id:`edge-${Date.now()}-${state.edges.length}`,source,target,sourceHandle}];state.setGraph(state.nodes,next);return true},removeNode:(id)=>{const state=get();if(!state.nodes.some(node=>node.id===id))return false;state.setGraph(state.nodes.filter(node=>node.id!==id),state.edges.filter(edge=>edge.source!==id&&edge.target!==id));if(state.selectedNodeId===id)set({selectedNodeId:null});return true},setNodeStatus:(id,status)=>{const state=get();if(!state.nodes.some(node=>node.id===id))return false;set({nodes:state.nodes.map(node=>node.id===id?{...node,data:{...node.data,ui:{...node.data.ui,status}}}:node)});return true},duplicateNode:(id)=>{const state=get();const original=state.nodes.find(node=>node.id===id);if(!original||state.nodes.length>=MAX_NODES)return null;const copy={...original,id:`${original.id}-copy-${Date.now()}`,position:{x:original.position.x+40,y:original.position.y+40},data:{config:{...original.data.config},ui:{...original.data.ui}}};state.setGraph([...state.nodes,copy],state.edges);return copy},deleteSelected:()=>{const id=get().selectedNodeId;return id?get().removeNode(id):false},updatePosition:(id,position)=>{const state=get();if(!Number.isFinite(position.x)||!Number.isFinite(position.y)||Math.abs(position.x)>1000000||Math.abs(position.y)>1000000)return false;const nodes=state.nodes.map(node=>node.id===id?{...node,position}:node);if(nodes.every((node,index)=>node===state.nodes[index]))return false;state.setGraph(nodes,state.edges);return true},undo:()=>{const h=get().history;if(!h.length)return;const current=snap();const previous=h[h.length-1];set({nodes:previous.nodes,edges:previous.edges,externalDataflowActivated:false,history:h.slice(0,-1),future:[...get().future,current]})},redo:()=>{const f=get().future;if(!f.length)return;const current=snap();const next=f[f.length-1];set({nodes:next.nodes,edges:next.edges,externalDataflowActivated:false,history:[...get().history,current],future:f.slice(0,-1)})},setReviewOnly:(reviewOnly)=>set({reviewOnly}),setExternalDataflow:(externalDataflowActivated)=>set({externalDataflowActivated}),setSelected:(selectedNodeId)=>set({selectedNodeId}),updateConfig:(id,config)=>{const state=get();if(!state.nodes.some(node=>node.id===id))return false;state.setGraph(state.nodes.map(node=>node.id===id?{...node,data:{...node.data,config}}:node),state.edges);return true},recover:()=>{try{const raw=localStorage.getItem(RECOVERY_KEY);if(raw){const g=importGraphJson(raw);set({nodes:g.nodes,edges:g.edges,reviewOnly:true,externalDataflowActivated:false})}}catch{}}}));
