import {render,screen} from "@testing-library/react"; import {ReactFlowProvider} from "@xyflow/react"; import {it,expect} from "vitest"; import {StartNode,LLMNode,RAGNode,LoopNode,ReducerNode,ToolNode,OutputNode} from "./customNodes"; it("exports all custom node archetypes",()=>{const props={id:"x",data:{},type:"default",dragging:false,zIndex:0,isConnectable:true,positionAbsoluteX:0,positionAbsoluteY:0};const components=[StartNode,LLMNode,RAGNode,LoopNode,ReducerNode,ToolNode,OutputNode];render(<ReactFlowProvider><div>{components.map((Component,index)=>{const C=Component as unknown as (p:Record<string,unknown>)=>React.ReactElement;return <span key={index}>{C(props)}</span>})}</div></ReactFlowProvider>);expect(screen.getAllByText(/idle/).length).toBe(7);});

it("gives loop routers distinct true, false, and fallback handles",()=>{
 const props={id:"loop",data:{},type:"loop",dragging:false,zIndex:0,isConnectable:true,positionAbsoluteX:0,positionAbsoluteY:0};
 const C=LoopNode as unknown as (p:Record<string,unknown>)=>React.ReactElement;
 const {container}=render(<ReactFlowProvider>{C(props)}</ReactFlowProvider>);
 expect(container.querySelectorAll("[data-handleid]")).toHaveLength(3);
 expect(container.querySelector('[data-handleid="true"]')).toBeTruthy();
 expect(container.querySelector('[data-handleid="false"]')).toBeTruthy();
 expect(container.querySelector('[data-handleid="fallback"]')).toBeTruthy();
});
