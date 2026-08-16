import type {NodeProps} from "@xyflow/react";
import {ForgeNode} from "./ForgeNode";
import type {NodeType} from "./graphStore";
export function OutputNode(props:NodeProps){const data={...(props.data as Record<string,unknown>),type:"output" as NodeType,label:"Output",targetHandles:["default"],sourceHandles:[]};return <ForgeNode {...props} data={data}/>}
