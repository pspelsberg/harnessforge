"""Static AST policy for the explicit Local Trust REPL mode."""
from __future__ import annotations
import ast

class ReplPolicyError(ValueError): pass

_SAFE_CALLS=frozenset({"abs","all","any","bool","dict","enumerate","float","int","len","list","max","min","print","range","round","set","sorted","str","sum","tuple","zip"})
_SAFE_MODULE_ATTRIBUTES={"math":frozenset({"ceil","fabs","floor","isfinite","sqrt"}),"json":frozenset({"dumps","loads"})}
_SAFE_DATA_ATTRIBUTES=frozenset({"get","items","keys","values"})
_ALLOWED_NODES=(
    ast.Module,ast.Expr,ast.Assign,ast.AnnAssign,ast.AugAssign,ast.Name,ast.Load,ast.Store,
    ast.Constant,ast.List,ast.Tuple,ast.Dict,ast.Set,ast.BinOp,ast.UnaryOp,ast.BoolOp,
    ast.Compare,ast.IfExp,ast.Subscript,ast.Slice,ast.Call,ast.Attribute,ast.keyword,
    ast.ListComp,ast.SetComp,ast.DictComp,ast.GeneratorExp,ast.comprehension,ast.If,
    ast.And,ast.Or,ast.Not,ast.UAdd,ast.USub,ast.Add,ast.Sub,ast.Mult,ast.Div,ast.FloorDiv,
    ast.Mod,ast.Pow,ast.BitAnd,ast.BitOr,ast.BitXor,ast.LShift,ast.RShift,ast.Eq,ast.NotEq,
    ast.Lt,ast.LtE,ast.Gt,ast.GtE,ast.In,ast.NotIn,ast.Is,ast.IsNot,ast.keyword,
)

def validate_code(code: str, *, max_nodes: int = 4096) -> ast.Module:
    if not isinstance(code,str) or not code.strip(): raise ReplPolicyError("REPL code is empty")
    try: tree=ast.parse(code,mode="exec")
    except (SyntaxError,ValueError) as exc: raise ReplPolicyError("REPL code is invalid") from exc
    nodes=list(ast.walk(tree))
    if len(nodes)>max_nodes: raise ReplPolicyError("REPL code is too complex")
    for node in nodes:
        if not isinstance(node,_ALLOWED_NODES): raise ReplPolicyError("REPL syntax is not allowed")
        if isinstance(node,ast.Constant) and not (node.value is None or isinstance(node.value,(bool,int,float,str))): raise ReplPolicyError("REPL constant is not allowed")
        if isinstance(node,ast.Name):
            if node.id.startswith("__"): raise ReplPolicyError("private names are not allowed")
            if isinstance(node.ctx,ast.Store) and node.id.startswith("_"): raise ReplPolicyError("private assignments are not allowed")
        if isinstance(node,ast.Attribute):
            if node.attr.startswith("_") or not isinstance(node.value,ast.Name): raise ReplPolicyError("attribute access is not allowed")
            root=node.value.id
            if root not in _SAFE_MODULE_ATTRIBUTES and root!="input_data": raise ReplPolicyError("attribute access is not allowed")
            if root=="input_data" and node.attr not in _SAFE_DATA_ATTRIBUTES: raise ReplPolicyError("data attribute is not allowed")
            if root in _SAFE_MODULE_ATTRIBUTES and node.attr not in _SAFE_MODULE_ATTRIBUTES[root]: raise ReplPolicyError("module attribute is not allowed")
        if isinstance(node,ast.Call):
            func=node.func
            if isinstance(func,ast.Name) and func.id not in _SAFE_CALLS: raise ReplPolicyError("function call is not allowed")
            if isinstance(func,ast.Attribute):
                if not isinstance(func.value,ast.Name) or func.attr not in _SAFE_DATA_ATTRIBUTES: raise ReplPolicyError("method call is not allowed")
            if not isinstance(func,(ast.Name,ast.Attribute)): raise ReplPolicyError("call target is not allowed")
    return tree
