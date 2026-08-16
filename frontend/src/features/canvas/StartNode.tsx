import type {NodeProps} from "@xyflow/react";
import {ForgeNode} from "./ForgeNode";
import type {NodeType} from "./graphStore";
export function StartNode(props:NodeProps){const data={...(props.data as Record<string,unknown>),type:"start" as NodeType,label:"Start trigger",targetHandles:[],sourceHandles:["default"]};return <ForgeNode {...props} data={data}/>}
