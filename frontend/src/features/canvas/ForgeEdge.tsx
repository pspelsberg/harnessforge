import {BaseEdge,getBezierPath,type EdgeProps} from "@xyflow/react";

export function ForgeEdge({id,sourceX,sourceY,sourcePosition,targetX,targetY,targetPosition,data}:EdgeProps){
 const [path]=getBezierPath({sourceX,sourceY,sourcePosition,targetX,targetY,targetPosition});
 const active=Boolean((data as {active?:boolean}|undefined)?.active);
 const gradientId=`forge-gradient-${id.replace(/[^A-Za-z0-9_-]/g,"_")}`;
 return <><svg aria-hidden="true"><defs><linearGradient id={gradientId} x1="0" y1="0" x2="1" y2="0"><stop offset="0%" stopColor="#fcd34d"/><stop offset="100%" stopColor="#fb923c"/></linearGradient></defs></svg><BaseEdge id={id} path={path} style={{stroke:`url(#${gradientId})`,strokeWidth:2,strokeDasharray:active?"8 4":undefined}}/>{active&&<circle className="forge-edge-particle" r="3" fill="#fcd34d" style={{offsetPath:`path('${path}')`,offsetDistance:"0%"}} aria-hidden="true"/>}</>;
}
