import {Handle,Position} from "@xyflow/react";
import type {NodeProps} from "@xyflow/react";
import type {NodeType} from "./graphStore";
import {NODE_LABELS,NODE_COLORS} from "./nodeRegistry";

export type ForgeVisualData={type:NodeType;label?:string;color?:string;status?:"idle"|"running"|"success"|"error";sourceHandles?:string[];targetHandles?:string[]};

export function ForgeNode(props:NodeProps){
 const data=props.data as unknown as ForgeVisualData;
 const color=data.color||NODE_COLORS[data.type];
 const sourceHandles=data.sourceHandles ?? ["default"];
 const targetHandles=data.targetHandles ?? ["default"];
 const handles=(type:"source"|"target",values:string[])=>values.map((id,index)=><Handle key={`${type}-${id}`} id={id==="default"?undefined:id} type={type} position={type==="source"?Position.Right:Position.Left} style={{top:`${((index+1)/(values.length+1))*100}%`}}/>);
 return <article aria-label={`${NODE_LABELS[data.type]} node`} className={`forge-node forge-node-${data.status||"idle"}`} style={{borderColor:color}}>{handles("target",targetHandles)}<strong>{data.label||NODE_LABELS[data.type]}</strong><span>{data.status||"idle"}</span>{handles("source",sourceHandles)}</article>;
}
