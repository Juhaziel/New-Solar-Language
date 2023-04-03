from __future__ import annotations
from dataclasses import dataclass

"""
https://docs.python.org/3/library/ast.html
"""

@dataclass  
class AST:
    _fields: tuple[str, ...] = ()
    _attribs: tuple[str, ...] = ()
    symref: any = None # A reference to a symbol in a symbol table
    lineno: int | None = None
    col_offset: int | None = None
    end_lineno: int | None = None
    end_col_offset: int | None = None

def get_source_segment(source: str, node: 'AST', padded: bool = False) -> str | None:
    """
    Get the source segment corresponding to this node.
    
    Returns None if location data is missing.
    
    https://docs.python.org/3/library/ast.html#ast.get_source_segment
    """
    lineno, col_offset, end_lineno, end_col_offset = node.lineno, node.col_offset, node.end_lineno, node.end_col_offset
    
    if None in (lineno, col_offset, end_lineno, end_col_offset): return None
    if padded:
        col_offset = 0
    
    lines = []
    cur_line = ""
    for c in source:
        if len(lines) == end_lineno: break
        if c == "\n":
            lines.append(cur_line)
            cur_line = ""
            continue
        cur_line += c
    if cur_line != "": lines.append(cur_line)
    del c, cur_line
    
    for _ in range(lineno-1): lines.pop(0)
    lines[end_lineno-lineno] = lines[end_lineno-lineno][:end_col_offset+1]
    lines[0] = lines[0][col_offset:]
    return "\n".join(lines)

def copy_location(old_node: 'AST', new_node: 'AST') -> 'AST':
    """
    Copies `old_node`'s location data to `new_node` and returns `new_node`
    """
    new_node.lineno = old_node.lineno
    new_node.col_offset = old_node.col_offset
    new_node.end_lineno = old_node.end_lineno
    new_node.end_col_offset = old_node.end_col_offset
    return new_node
    
def fix_missing_locations(node: 'AST') -> 'AST':
    """
    https://docs.python.org/3/library/ast.html#ast.fix_missing_locations
    """
    def _fix(node: 'AST', lineno, col_offset, end_lineno, end_col_offset):
        if node.lineno == None: node.lineno = lineno
        else: lineno = node.lineno
        
        if node.col_offset == None: node.col_offset = col_offset
        else: col_offset = node.col_offset
        
        if node.end_lineno == None: node.end_lineno = end_lineno
        else: end_lineno = node.end_lineno
        
        if node.end_col_offset == None: node.end_col_offset = end_col_offset
        else: end_col_offset = node.end_col_offset
        
        for child in iter_child_nodes(node):
            _fix(child, lineno, col_offset, end_lineno, end_col_offset)
    _fix(node, 1, 0, 1, 0)
    return node

def increment_lineno(node: 'AST', n=1) -> 'AST':
    """
    Increments the line number of this node and all of its descendants by n
    
    https://docs.python.org/3/library/ast.html#ast.increment_lineno
    """
    for child in walk(node):
        if child.lineno != None: child.lineno += n
        if child.end_lineno != None: child.end_lineno += n
    return node

def iter_fields(node: 'AST') -> tuple[str, any]:
    """
    Yield a tuple `(name, value)` for each field of the specified node.
    
    https://docs.python.org/3/library/ast.html#ast.iter_fields
    """
    for field in node._fields:
        try:
            yield field, getattr(node, field)
        except AttributeError:
            pass

def iter_attribs(node: 'AST') -> tuple[str, any]:
    """
    Yield a tuple `(name, value)` for each attribute of the specified node.
    """
    for attrib in node._attribs:
        try:
            yield attrib, getattr(node, attrib)
        except AttributeError:
            pass

def iter_child_nodes(node: 'AST') -> 'AST':
    """
    Yield all direct child nodes of node.
    
    https://docs.python.org/3/library/ast.html#ast.iter_child_nodes
    """
    for _, attrib in iter_attribs(node):
        if isinstance(attrib, AST):
            yield attrib
        elif isinstance(attrib, list):
            for item in attrib:
                if isinstance(item, AST):
                    yield item
    for _, field in iter_fields(node):
        if isinstance(field, AST):
            yield field
        elif isinstance(field, list):
            for item in field:
                if isinstance(item, AST):
                    yield item

def walk(node) -> 'AST':
    """
    Recursively yield all descendants in BFS. The order of child nodes is unspecified.
    
    https://docs.python.org/3/library/ast.html#ast.walk
    """
    from collections import deque
    todo = deque([node])
    while todo:
        node = todo.popleft()
        todo.extend(iter_child_nodes(node))
        yield node

class NodeVisitor:
    """
    Basically the same as the ast package's NodeVisitor, just worse.
    
    https://docs.python.org/3/library/ast.html#ast.NodeVisitor
    """
    def visit(self, node) -> 'AST':
        """Visit a node"""
        method = "visit_" + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node)
        
    def generic_visit(self, node) -> 'AST':
        """Called if nothing else matches the specified node."""
        for child in iter_child_nodes(node):
            self.visit(child)
        return node

class NodeTransformer(NodeVisitor):
    """
    A NodeVisitor that walks the tree and replaces nodes with the value returned by their visitor method's return value.
    If the return value is None, the node will be removed.
    
    Child nodes must be transformed or have generic_visit called on them.
    
    https://docs.python.org/3/library/ast.html#ast.NodeTransformer
    """
    def generic_visit(self, node) -> 'AST':
        for attrib, old in iter_attribs(node):
            if isinstance(old, list):
                new = []
                for value in old:
                    if isinstance(value, AST):
                        value = self.visit(old)
                        if value is None:
                            continue
                        elif isinstance(value, list):
                            new.extend(value)
                            continue
                        else:
                            new.append(value)
                            continue
                    new.append(value)
                old[:] = new
            elif isinstance(old, AST):
                new = self.visit(old)
                if new is None:
                    delattr(node, attrib)
                else:
                    setattr(node, attrib, new)
        for field, old in iter_fields(node):
            if isinstance(old, list):
                new = []
                for value in old:
                    if isinstance(value, AST):
                        value = self.visit(old)
                        if value is None:
                            continue
                        elif isinstance(value, list):
                            new.extend(value)
                            continue
                        else:
                            new.append(value)
                            continue
                    new.append(value)
                old[:] = new
            elif isinstance(old, AST):
                new = self.visit(old)
                if new is None:
                    delattr(node, field)
                else:
                    setattr(node, field, new)
        return node

### GENERATED CLASSES FOR IDK ###

## TYPE 'Module'
class Module(AST):
	def __init__(self, decls: list['Decl']):
		self._fields = ("decls",)
		self.decls: list['Decl'] = decls

## TYPE 'Type'
class Type(AST):
	def __init__(self, is_volatile: bool):
		self._attribs = ("is_volatile",)
		self.is_volatile: bool = is_volatile

class VoidType(Type): pass

class RefType(Type):
	def __init__(self, is_volatile: bool, ref_type_name: str):
		super().__init__(is_volatile)
		self._fields = ("ref_type_name",)
		self.ref_type_name: str = ref_type_name

class IntType(Type):
	def __init__(self, is_volatile: bool, type: str):
		super().__init__(is_volatile)
		self._fields = ("type",)
		self.type: str = type

class ArrayType(Type):
	def __init__(self, is_volatile: bool, inner_type: 'Type', size: 'Expr' | None):
		super().__init__(is_volatile)
		self._fields = ("inner_type", "size",)
		self.inner_type: 'Type' = inner_type
		self.size: 'Expr' | None = size

class FuncType(Type):
	def __init__(self, is_volatile: bool, return_type: 'Type', param_types: list['Type'], is_variadic: bool):
		super().__init__(is_volatile)
		self._fields = ("return_type", "param_types", "is_variadic",)
		self.return_type: 'Type' = return_type
		self.param_types: list['Type'] = param_types
		self.is_variadic: bool = is_variadic

class StructType(Type):
	def __init__(self, is_volatile: bool, members: list['MemberData']):
		super().__init__(is_volatile)
		self._fields = ("members",)
		self.members: list['MemberData'] = members

class UnionType(Type):
	def __init__(self, is_volatile: bool, members: list['MemberData']):
		super().__init__(is_volatile)
		self._fields = ("members",)
		self.members: list['MemberData'] = members

## TYPE 'MemberData'
class MemberData(AST):
	def __init__(self, name: str, type: 'Type', bits: int | None):
		self._fields = ("name", "type", "bits",)
		self.name: str = name
		self.type: 'Type' = type
		self.bits: int | None = bits

## TYPE 'Decl'
class Decl(AST):
	def __init__(self, name: str, type: 'Type', description: str | None):
		self._attribs = ("name", "type", "description",)
		self.name: str = name
		self.type: 'Type' = type
		self.description: str | None = description

class VarDecl(Decl):
	def __init__(self, name: str, type: 'Type', description: str | None, value: 'Expr' | None, is_static: bool):
		super().__init__(name, type, description)
		self._fields = ("value", "is_static",)
		self.value: 'Expr' | None = value
		self.is_static: bool = is_static

class ConstDecl(Decl):
	def __init__(self, name: str, type: 'Type', description: str | None, value: 'Expr', is_static: bool):
		super().__init__(name, type, description)
		self._fields = ("value", "is_static",)
		self.value: 'Expr' = value
		self.is_static: bool = is_static

class FuncDecl(Decl):
	def __init__(self, name: str, type: 'Type', description: str | None, param_names: list[str], body: 'Stmt' | None, is_static: bool, is_inline: bool):
		super().__init__(name, type, description)
		self._fields = ("param_names", "body", "is_static", "is_inline",)
		self.param_names: list[str] = param_names
		self.body: 'Stmt' | None = body
		self.is_static: bool = is_static
		self.is_inline: bool = is_inline

class TypeDecl(Decl): pass

## TYPE 'Stmt'
class Stmt(AST): pass

class EmptyStmt(Stmt): pass

class DefStmt(Stmt):
	def __init__(self, decl: 'Decl'):
		self._fields = ("decl",)
		self.decl: 'Decl' = decl

class CompoundStmt(Stmt):
	def __init__(self, stmts: list['Stmt']):
		self._fields = ("stmts",)
		self.stmts: list['Stmt'] = stmts

class ExprStmt(Stmt):
	def __init__(self, expr: 'Expr'):
		self._fields = ("expr",)
		self.expr: 'Expr' = expr

class ContinueStmt(Stmt):
	def __init__(self, label: str | None):
		self._fields = ("label",)
		self.label: str | None = label

class BreakStmt(Stmt):
	def __init__(self, breakif: bool, label: str | None):
		self._fields = ("breakif", "label",)
		self.breakif: bool = breakif
		self.label: str | None = label

class ReturnStmt(Stmt):
	def __init__(self, ret_expr: 'Expr' | None):
		self._fields = ("ret_expr",)
		self.ret_expr: 'Expr' | None = ret_expr

class IfStmt(Stmt):
	def __init__(self, cond_expr: 'Expr', body: 'Stmt', else_body: 'Stmt' | None, label: str | None):
		self._fields = ("cond_expr", "body", "else_body", "label",)
		self.cond_expr: 'Expr' = cond_expr
		self.body: 'Stmt' = body
		self.else_body: 'Stmt' | None = else_body
		self.label: str | None = label

class IterStmt(Stmt):
	def __init__(self, init_expr: 'Expr' | None, cond_expr: 'Expr' | None, inc_expr: 'Expr' | None, body: 'Stmt', else_body: 'Stmt' | None, label: str | None):
		self._fields = ("init_expr", "cond_expr", "inc_expr", "body", "else_body", "label",)
		self.init_expr: 'Expr' | None = init_expr
		self.cond_expr: 'Expr' | None = cond_expr
		self.inc_expr: 'Expr' | None = inc_expr
		self.body: 'Stmt' = body
		self.else_body: 'Stmt' | None = else_body
		self.label: str | None = label

## TYPE 'Expr'
class Expr(AST): pass

class CompoundExpr(Expr):
	def __init__(self, record_or_array_type: 'Type', exprs: list['Expr']):
		self._fields = ("record_or_array_type", "exprs",)
		self.record_or_array_type: 'Type' = record_or_array_type
		self.exprs: list['Expr'] = exprs

class NameExpr(Expr):
	def __init__(self, name: str):
		self._fields = ("name",)
		self.name: str = name

class IntExpr(Expr):
	def __init__(self, type: 'IntType', value: int):
		self._fields = ("type", "value",)
		self.type: 'IntType' = type
		self.value: int = value

class StrExpr(Expr):
	def __init__(self, utf8: list[int]):
		self._fields = ("utf8",)
		self.utf8: list[int] = utf8

class SzexprExpr(Expr):
	def __init__(self, expr: 'Expr'):
		self._fields = ("expr",)
		self.expr: 'Expr' = expr

class SztypeExpr(Expr):
	def __init__(self, type: 'Type'):
		self._fields = ("type",)
		self.type: 'Type' = type

class CallExpr(Expr):
	def __init__(self, func_expr: 'Expr', args: list['Expr']):
		self._fields = ("func_expr", "args",)
		self.func_expr: 'Expr' = func_expr
		self.args: list['Expr'] = args

class IndexExpr(Expr):
	def __init__(self, array_expr: 'Expr', index_expr: 'Expr'):
		self._fields = ("array_expr", "index_expr",)
		self.array_expr: 'Expr' = array_expr
		self.index_expr: 'Expr' = index_expr

class AccessExpr(Expr):
	def __init__(self, record_expr: 'Expr', member_name: str):
		self._fields = ("record_expr", "member_name",)
		self.record_expr: 'Expr' = record_expr
		self.member_name: str = member_name

class CastExpr(Expr):
	def __init__(self, expr: 'Expr', cast_type: 'Type', signed: bool):
		self._fields = ("expr", "cast_type", "signed",)
		self.expr: 'Expr' = expr
		self.cast_type: 'Type' = cast_type
		self.signed: bool = signed

class DerefExpr(Expr):
	def __init__(self, pointer_expr: 'Expr'):
		self._fields = ("pointer_expr",)
		self.pointer_expr: 'Expr' = pointer_expr

class AddrOfExpr(Expr):
	def __init__(self, expr: 'Expr'):
		self._fields = ("expr",)
		self.expr: 'Expr' = expr

class UnaryExpr(Expr):
	def __init__(self, op: 'UnaryOp', expr: 'Expr'):
		self._fields = ("op", "expr",)
		self.op: 'UnaryOp' = op
		self.expr: 'Expr' = expr

class UnaryCondExpr(Expr):
	def __init__(self, op: 'UnaryCOp', expr: 'Expr'):
		self._fields = ("op", "expr",)
		self.op: 'UnaryCOp' = op
		self.expr: 'Expr' = expr

class BinaryExpr(Expr):
	def __init__(self, left: 'Expr', op: 'BinOp', right: 'Expr'):
		self._fields = ("left", "op", "right",)
		self.left: 'Expr' = left
		self.op: 'BinOp' = op
		self.right: 'Expr' = right

class BinaryCondExpr(Expr):
	def __init__(self, left: 'Expr', op: 'BinCOp', right: 'Expr'):
		self._fields = ("left", "op", "right",)
		self.left: 'Expr' = left
		self.op: 'BinCOp' = op
		self.right: 'Expr' = right

class TernaryExpr(Expr):
	def __init__(self, cond_expr: 'Expr', true_expr: 'Expr', false_expr: 'Expr'):
		self._fields = ("cond_expr", "true_expr", "false_expr",)
		self.cond_expr: 'Expr' = cond_expr
		self.true_expr: 'Expr' = true_expr
		self.false_expr: 'Expr' = false_expr

class AssignExpr(Expr):
	def __init__(self, lhs: 'Expr', rhs: 'Expr', op: 'BinOp' | None):
		self._fields = ("lhs", "rhs", "op",)
		self.lhs: 'Expr' = lhs
		self.rhs: 'Expr' = rhs
		self.op: 'BinOp' | None = op

class CommaExpr(Expr):
	def __init__(self, exprs: list['Expr']):
		self._fields = ("exprs",)
		self.exprs: list['Expr'] = exprs

class ComplexExpr(Expr):
	def __init__(self, type: str, value: 'any'):
		self._fields = ("type", "value",)
		self.type: str = type
		self.value: 'any' = value

## TYPE 'UnaryOp'
class UnaryOp(AST): pass

class UnaryPlus(UnaryOp): pass

class UnaryMinus(UnaryOp): pass

class BitNot(UnaryOp): pass

## TYPE 'UnaryCOp'
class UnaryCOp(AST): pass

class LogicalNot(UnaryCOp): pass

## TYPE 'BinOp'
class BinOp(AST): pass

class Add(BinOp): pass

class Sub(BinOp): pass

class Mult(BinOp): pass

class UDiv(BinOp): pass

class SDiv(BinOp): pass

class UMod(BinOp): pass

class SMod(BinOp): pass

class ShLogLeft(BinOp): pass

class ShLogRight(BinOp): pass

class ShArRight(BinOp): pass

class BitAnd(BinOp): pass

class BitXor(BinOp): pass

class BitOr(BinOp): pass

## TYPE 'BinCOp'
class BinCOp(AST): pass

class LogicalAnd(BinCOp): pass

class LogicalOr(BinCOp): pass

class Eq(BinCOp): pass

class NotEq(BinCOp): pass

class ULt(BinCOp): pass

class ULtE(BinCOp): pass

class SLt(BinCOp): pass

class SLtE(BinCOp): pass

class UGt(BinCOp): pass

class UGtE(BinCOp): pass

class SGt(BinCOp): pass

class SGtE(BinCOp): pass