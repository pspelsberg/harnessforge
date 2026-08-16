import {render,screen,fireEvent,cleanup} from "@testing-library/react"; import {it,expect,vi,afterEach} from "vitest"; import {NodeConfigForm} from "./NodeConfigForm"; const node={id:"l",type:"llm" as const,position:{x:0,y:0},data:{config:{model:"old"},ui:{}}}; afterEach(cleanup);
it("edits bounded LLM config",()=>{const on=vi.fn();render(<NodeConfigForm node={node} onChange={on}/>);fireEvent.change(screen.getByLabelText("model"),{target:{value:"new"}});expect(on).toHaveBeenCalledWith(expect.objectContaining({model:"new"}));});

it("clamps temperature to provider bounds",()=>{const on=vi.fn();render(<NodeConfigForm node={{...node,data:{config:{},ui:{}}}} onChange={on}/>);fireEvent.change(screen.getByLabelText("temperature"),{target:{value:"9"}});expect(on).toHaveBeenCalledWith(expect.objectContaining({temperature:2}));});


it("edits loop condition key and operator",()=>{const on=vi.fn();const loop={id:"loop",type:"loop" as const,position:{x:0,y:0},data:{config:{},ui:{}}};render(<NodeConfigForm node={loop} onChange={on}/>);fireEvent.change(screen.getByLabelText("condition type"),{target:{value:"equals"}});expect(on).toHaveBeenCalledWith(expect.objectContaining({condition_type:"equals"}));});
