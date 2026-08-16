import type {NodeProps} from "@xyflow/react";
import {ForgeNode} from "./ForgeNode";
import type {NodeType} from "./graphStore";
export function ReducerNode(props:NodeProps){const data={...(props.data as Record<string,unknown>),type:"reducer" as NodeType,label:"State Reducer",targetHandles:["default"],sourceHandles:["default"]};return <ForgeNode {...props} data={data}/>}
