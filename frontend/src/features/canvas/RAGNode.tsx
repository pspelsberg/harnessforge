import type {NodeProps} from "@xyflow/react";
import {ForgeNode} from "./ForgeNode";
import type {NodeType} from "./graphStore";
export function RAGNode(props:NodeProps){const data={...(props.data as Record<string,unknown>),type:"rag" as NodeType,label:"RAG / LanceDB",targetHandles:["default"],sourceHandles:["default"]};return <ForgeNode {...props} data={data}/>}
