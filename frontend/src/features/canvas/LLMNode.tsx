import type {NodeProps} from "@xyflow/react"; import {ForgeNode} from "./ForgeNode"; import type {NodeType} from "./graphStore";
export function LLMNode(props:NodeProps){const data={...(props.data as Record<string,unknown>),type:"llm" as NodeType,label:"LLM Call"};return <ForgeNode {...props} data={data}/>}
