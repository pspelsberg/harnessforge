import type {NodeProps} from "@xyflow/react"; import {ForgeNode} from "./ForgeNode"; import type {NodeType} from "./graphStore";
export function ToolNode(props:NodeProps){const data={...(props.data as Record<string,unknown>),type:"tool" as NodeType,label:"Tool · Local Trust Mode"};return <ForgeNode {...props} data={data}/>}
