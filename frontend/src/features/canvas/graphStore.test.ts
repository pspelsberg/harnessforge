import { beforeEach, describe, expect, it } from "vitest"; import {useGraphStore, MAX_NODES, importGraphJson, type NodeType, validateGraph} from "./graphStore"; describe("graph store",()=>{beforeEach(()=>useGraphStore.setState({nodes:[],edges:[],reviewOnly:true,selectedNodeId:null})); it("starts review-only and replaces graph",()=>{useGraphStore.getState().setGraph([{id:"s",type:"start",position:{x:0,y:0},data:{config:{},ui:{}}}],[]); expect(useGraphStore.getState().reviewOnly).toBe(true); expect(useGraphStore.getState().nodes).toHaveLength(1);}); it("rejects oversized or malformed imports and stays review-only",()=>{expect(()=>importGraphJson(JSON.stringify({schema_version:"1",nodes:Array.from({length:MAX_NODES+1},(_,i)=>({id:String(i)})),edges:[]}))).toThrow(); expect(()=>importGraphJson("{bad")).toThrow(); expect(importGraphJson(JSON.stringify({schema_version:"1",nodes:[],edges:[]})).reviewOnly).toBe(true); expect(()=>importGraphJson(JSON.stringify({schema_version:"1",nodes:[{id:"x",type:"evil"}],edges:[]}))).toThrow(); expect(()=>importGraphJson(JSON.stringify({schema_version:"1",nodes:[{id:"x",type:"start",position:{x:0,y:0},data:{}}],edges:[{id:"e",source:"x",target:"missing"}]}))).toThrow();});});
it("validates reachability and supports undo/redo",()=>{const store=useGraphStore.getState(); const node={id:"s",type:"start" as const,position:{x:0,y:0},data:{config:{},ui:{}}}; store.setGraph([node],[]); expect(validateGraph([node],[])[0].severity).toBe("error"); store.setGraph([],[]); store.undo(); expect(useGraphStore.getState().nodes).toHaveLength(1); store.redo(); expect(useGraphStore.getState().nodes).toHaveLength(0);});


it("rejects malformed config values, non-finite positions, and oversized ids",()=>{
 expect(()=>importGraphJson(JSON.stringify({schema_version:"1",nodes:[{id:"s",type:"start",position:{x:NaN,y:0},data:{config:{},ui:{}}}],edges:[]}))).toThrow();
 expect(()=>importGraphJson(JSON.stringify({schema_version:"1",nodes:[{id:"s",type:"start",position:{x:0,y:0},data:{config:null,ui:{}}}],edges:[]}))).toThrow();
 expect(()=>importGraphJson(JSON.stringify({schema_version:"1",nodes:[{id:"s".repeat(129),type:"start",position:{x:0,y:0},data:{config:{},ui:{}}}],edges:[]}))).toThrow();
});


it("supports bounded node and edge authoring actions",()=>{const store=useGraphStore.getState();const first=store.addNode("start")!;const second=useGraphStore.getState().addNode("output")!;expect(useGraphStore.getState().nodes).toHaveLength(2);expect(useGraphStore.getState().connectNodes(first.id,second.id)).toBe(true);expect(useGraphStore.getState().edges).toHaveLength(1);expect(useGraphStore.getState().removeNode(first.id)).toBe(true);expect(useGraphStore.getState().edges).toHaveLength(0);});


it("rejects out-of-bounds position updates",()=>{const state=useGraphStore.getState();const node=state.addNode("start")!;expect(useGraphStore.getState().updatePosition(node.id,{x:2e9,y:0})).toBe(false);});


it("duplicates and deletes selected nodes through actions",()=>{useGraphStore.setState({nodes:[],edges:[],reviewOnly:true,selectedNodeId:null,history:[],future:[]});const state=useGraphStore.getState();const node=state.addNode("llm")!;expect(state.duplicateNode(node.id)).not.toBeNull();expect(useGraphStore.getState().nodes).toHaveLength(2);expect(useGraphStore.getState().deleteSelected()).toBe(false);useGraphStore.getState().setSelected(node.id);expect(useGraphStore.getState().deleteSelected()).toBe(true);});


it("updates node execution status for live trace highlighting",()=>{useGraphStore.setState({nodes:[{id:"n",type:"llm",position:{x:0,y:0},data:{config:{},ui:{}}}],edges:[],reviewOnly:true,selectedNodeId:null,history:[],future:[]});expect(useGraphStore.getState().setNodeStatus("n","running")).toBe(true);expect(useGraphStore.getState().nodes[0].data.ui.status).toBe("running");});


it("updates selected node config and explicit dataflow setting",()=>{useGraphStore.setState({nodes:[{id:"l",type:"llm",position:{x:0,y:0},data:{config:{},ui:{}}}],edges:[],reviewOnly:true,selectedNodeId:"l",history:[],future:[]});expect(useGraphStore.getState().updateConfig("l",{temperature:0.2})).toBe(true);expect(useGraphStore.getState().nodes[0].data.config.temperature).toBe(0.2);useGraphStore.getState().setExternalDataflow(true);expect(useGraphStore.getState().externalDataflowActivated).toBe(true);});


it("rejects unsupported graph schema versions",()=>{expect(()=>importGraphJson(JSON.stringify({schema_version:"2",nodes:[],edges:[]}))).toThrow();});


it("invalidates external dataflow approval on graph/config changes",()=>{useGraphStore.setState({nodes:[{id:"l",type:"llm",position:{x:0,y:0},data:{config:{model:"x"},ui:{}}}],edges:[],reviewOnly:false,externalDataflowActivated:true,selectedNodeId:"l",history:[],future:[]});useGraphStore.getState().updateConfig("l",{model:"changed"});expect(useGraphStore.getState().externalDataflowActivated).toBe(false);useGraphStore.getState().setExternalDataflow(true);useGraphStore.getState().setGraph([],[]);expect(useGraphStore.getState().externalDataflowActivated).toBe(false);});


it("requires schema version and preserves approval during live status updates",()=>{expect(()=>importGraphJson(JSON.stringify({nodes:[],edges:[]}))).toThrow();useGraphStore.setState({nodes:[{id:"l",type:"llm",position:{x:0,y:0},data:{config:{},ui:{}}}],edges:[],reviewOnly:false,externalDataflowActivated:true,selectedNodeId:null,history:[],future:[]});useGraphStore.getState().setNodeStatus("l","running");expect(useGraphStore.getState().externalDataflowActivated).toBe(true);});


it("rejects oversized string config values",()=>{const config={x:"a".repeat(200000)};expect(()=>importGraphJson(JSON.stringify({schema_version:"1",nodes:[{id:"s",type:"start",position:{x:0,y:0},data:{config,ui:{}}}],edges:[]}))).toThrow();});



it("rejects secret-shaped runtime config and malformed node surfaces",()=>{
 expect(()=>importGraphJson(JSON.stringify({schema_version:"1",nodes:[{id:"s",type:"start",position:{x:0,y:0},data:{config:{api_key:"secret"},ui:{}}}],edges:[]}))).toThrow();
 expect(()=>importGraphJson(JSON.stringify({schema_version:"1",nodes:[{id:"s",type:"start",position:{x:0,y:0},data:{config:[],ui:{}}}],edges:[]}))).toThrow();
});

it("reports governed loop requirements and ungoverned cycles",()=>{
 const n=(id:string,type:NodeType,config:Record<string,unknown>={})=>({id,type,position:{x:0,y:0},data:{config,ui:{}}});
 const nodes=[n("s","start"),n("loop","loop",{max_iterations:3,fallback:"o",condition_type:"exists"}),n("o","output")];
 expect(validateGraph(nodes,[{id:"a",source:"s",target:"loop"},{id:"b",source:"loop",target:"o",sourceHandle:"fallback"}]).some(i=>i.message.includes("true, false"))).toBe(true);
 const a=n("a","llm"),b=n("b","llm");
 const cycleIssues=validateGraph([a,b,n("s2","start"),n("o2","output")],[{id:"1",source:"s2",target:"a"},{id:"2",source:"a",target:"b"},{id:"3",source:"b",target:"a"},{id:"4",source:"b",target:"o2"}]); expect(cycleIssues.some(i=>i.message.includes("cycles"))).toBe(true);
});
