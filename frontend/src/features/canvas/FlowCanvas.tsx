import {Background,Controls,MiniMap,ReactFlow,ReactFlowProvider,useReactFlow,type Node} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import {useGraphStore,validateGraph,type ForgeEdge,type ForgeNode,type NodeType} from "./graphStore";
import {NODE_LABELS,NODE_COLORS} from "./nodeRegistry";
import {ForgeNode as ForgeNodeView} from "./ForgeNode";
import {StartNode,LLMNode,RAGNode,LoopNode,ReducerNode,ToolNode,OutputNode} from "./customNodes";
import {ForgeEdge as ForgeEdgeView} from "./ForgeEdge";

const nodeTypes={default:ForgeNodeView,start:StartNode,llm:LLMNode,rag:RAGNode,loop:LoopNode,reducer:ReducerNode,tool:ToolNode,output:OutputNode};
const edgeTypes={default:ForgeEdgeView};
const NODE_TYPES=new Set<NodeType>(["start","llm","rag","loop","reducer","tool","output"]);

function CanvasSurface({nodes,edges}:{nodes:ForgeNode[];edges:ForgeEdge[]}){
 const {screenToFlowPosition}=useReactFlow();
 const {setSelected,updatePosition,connectNodes,addNode}=useGraphStore();
 const onDrop=(event:React.DragEvent)=>{
  event.preventDefault();
  const type=event.dataTransfer.getData("application/x-harnessforge-node") as NodeType;
  if(!NODE_TYPES.has(type))return;
  const node=addNode(type);
  if(!node)return;
  const position=screenToFlowPosition({x:event.clientX,y:event.clientY});
  updatePosition(node.id,{x:position.x,y:position.y});
 };
 const viewNodes=nodes.map(node=>({...node,data:{...node.data,label:NODE_LABELS[node.type],color:NODE_COLORS[node.type]}}));
 return <ReactFlow nodeTypes={nodeTypes} edgeTypes={edgeTypes} nodes={viewNodes as unknown as Node[]} edges={edges.map(edge=>({...edge,type:"default"})) as never[]} onDrop={onDrop} onDragOver={event=>event.preventDefault()} onNodeClick={(_,node)=>setSelected(String(node.id))} onNodeDragStop={(_,node)=>updatePosition(String(node.id),{x:Number(node.position.x),y:Number(node.position.y)})} onConnect={connection=>{if(connection.source&&connection.target)connectNodes(connection.source,connection.target,connection.sourceHandle||undefined)}} fitView><Background color="#1e293b"/><Controls/><MiniMap/></ReactFlow>;
}

export function FlowCanvas(){
 const {nodes,edges}=useGraphStore();
 const issues=validateGraph(nodes,edges);
 const invalid=new Set(issues.filter(issue=>issue.severity==="error"&&issue.nodeId).map(issue=>issue.nodeId));
 const warning=new Set(issues.filter(issue=>issue.severity==="warning"&&issue.nodeId).map(issue=>issue.nodeId));
 const decorated=nodes.map(node=>({...node,data:{...node.data,status:invalid.has(node.id)?"error":warning.has(node.id)?"running":node.data.ui.status}}));
 return <ReactFlowProvider><section aria-label="graph canvas" style={{height:"100vh"}}>{issues.length>0&&<aside role="status">{issues.map((issue,index)=><p key={`${issue.nodeId??issue.message}-${index}`}>{issue.message}</p>)}</aside>}<CanvasSurface nodes={decorated} edges={edges}/></section></ReactFlowProvider>;
}
