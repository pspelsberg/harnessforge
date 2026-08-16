import type {NodeProps} from "@xyflow/react"; import {ForgeNode} from "./ForgeNode"; import type {NodeType} from "./graphStore";
export function LoopNode(props:NodeProps){const data={...(props.data as Record<string,unknown>),type:"loop" as NodeType,label:"Loop / Router"};return <ForgeNode {...props} data={data}/>}
