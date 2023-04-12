from __future__ import annotations
from collections import OrderedDict
import internals.astnodes as ast

"""
Strongly inspired by the `symtable` library

https://docs.python.org/3/library/symtable.html
"""

class SymbolTable:
    """
    Represents a scope in a symbol table.
    
    Contains a reference to a Module, FuncDecl, or Stmt.
    
    This class should not be built directly.
    """
    
    def __init__(self, node: ast.AST, parent: 'SymbolTable' | None = None):
        self._node = node
        self._parent = parent
        self._children: list['SymbolTable'] = []
        self._names: OrderedDict[str, 'NameSymbol'] = OrderedDict()
        self._types: OrderedDict[str, 'TypeSymbol'] = OrderedDict()
        self._labels: OrderedDict[str, 'LabelSymbol'] = OrderedDict()
    
    def get_type(self) -> str:
        "Returns the type of SymbolTable."
        raise NotImplementedError() # AbstractMethod
    
    def is_global(self) -> bool:
        "Check if this SymbolTable is the top-level table."
        return self.get_type() == "module"
    
    def get_lineno(self) -> bool:
        "Return the line number this SymbolTable begins at."
        return self._node.lineno
    
    def has_parent(self) -> bool:
        "Return `True` if this SymbolTable has a parent SymbolTable"
        return not not self._parent
    
    def get_parent(self) -> 'SymbolTable':
        "Return the parent of this SymbolTable, if any."
        return self._parent
    
    def has_children(self) -> bool:
        "Return `True` if this SymbolTable contains children SymbolTable"
        return len(self._children) > 0
    
    def get_children(self) -> list['SymbolTable']:
        "Return the children SymbolTables of this SymbolTable, if any."
        return self._children
    
    def _add_child(self, child: 'SymbolTable'):
        "Private method to add a child SymbolTable"
        self._children.append(child)
        child._parent = self
    
    def get_names(self) -> list['NameSymbol']:
        "Return a list of NameSymbol instances in this SymbolTable"
        return self._get_symbols(NameSymbol)
        
    def get_namesym(self, name: str, localonly=False) -> 'NameSymbol' | None:
        "Return a NameSymbol instance in the SymbolTable's ancestry or None if it does not exist"
        return self._get_symbol(NameSymbol, name, localonly)
        
    def get_types(self) -> list['TypeSymbol']:
        "Return a list of TypeSymbol instances in this SymbolTable"
        return self._get_symbols(TypeSymbol)
        
    def get_typesym(self, name: str, localonly=False) -> 'TypeSymbol' | None:
        "Return a TypeSymbol instance in the SymbolTable's ancestry or None if it does not exist"
        return self._get_symbol(TypeSymbol, name, localonly)
    
    def get_labels(self) -> list['LabelSymbol']:
        "Return a list of LabelSymbol instances in this SymbolTable"
        return self._get_symbols(LabelSymbol)
    
    def get_labelsym(self, name: str, localonly=False) -> 'LabelSymbol' | None:
        "Return a LabelSymbol instance in the SymbolTable's ancestry or None if it does not exist"
        return self._get_symbol(LabelSymbol, name, localonly)
    
    def _get_symbols(self, cls) -> list['Symbol']:
        "Private function to return a list of Symbol instances in this SymbolTable."
        if   cls == NameSymbol: return list(self._names.values())
        elif cls == TypeSymbol: return list(self._types.values())
        elif cls == LabelSymbol: return list(self._labels.values())
    
    def _get_symbol(self, cls, name: str, localonly=False) -> 'Symbol' | None:
        "Private function to return a Symbol instance or None if it does not exist"
        symbols: dict[str, Symbol] = None
        if   cls == NameSymbol: symbols = self._names
        elif cls == TypeSymbol: symbols = self._types
        elif cls == LabelSymbol: symbols = self._labels
        
        symbol = symbols.get(name, None)
        if symbol != None or localonly: return symbol
        if self._parent != None:
            return self._parent._get_symbol(cls, name)
        
    def _bind_symbol(self, name: str, symbol: 'Symbol', overwrite = False) -> bool:
        "Private function that binds a symbol to the SymbolTable."
        symbols: dict[str, Symbol] = None
        if   isinstance(symbol, NameSymbol): symbols = self._names
        elif isinstance(symbol, TypeSymbol): symbols = self._types
        elif isinstance(symbol, LabelSymbol): symbols = self._labels
        
        if not overwrite and symbols.get(name) != None: return False
        
        symbols[name] = symbol
        symbol._set_table(self)
        return True
        
class ModuleTable(SymbolTable):
    """
    The SymbolTable created by a file.
    
    Contains symbols defined at the global level.
    """
    def get_type(self) -> str:
        "Returns the type of SymbolTable."
        return "module"

class FuncTable(SymbolTable):
    """
    The SymbolTable created by a function.
    
    Contains parameters only. Its compound statement body has its own scope.
    """
    def get_type(self) -> str:
        "Returns the type of SymbolTable."
        return "func"

class BlockTable(SymbolTable):
    """
    The SymbolTable created by a CompoundStmt.
    
    Contains symbols defined at the local level.
    """
    def get_type(self) -> str:
        "Returns the type of SymbolTable."
        return "block"

class Symbol:
    def __init__(self, name: str):
        self._table: SymbolTable = None
        self._name = name
        self._isreferenced: bool = False
    
    def get_name(self) -> str:
        "Return the name of this symbol."
        return self._name
    
    def is_referenced(self) -> bool:
        "Return whether this symbol is referenced somewhere."
        return self._isreferenced
    
    def _reference(self):
        "Tell the symbol it has been referenced somewhere."
        self._isreferenced = True
    
    def get_table(self) -> SymbolTable:
        "Return the SymbolTable containing this Symbol."
        return self._table
    
    def _set_table(self, table: SymbolTable):
        "Private method to set the SymbolTable containing this Symbol."
        self._table = table
        
class NameSymbol(Symbol):
    def __init__(self, name: str, type: ast.Type):
        super().__init__(name)
        self._type = type
    
    def get_type(self) -> ast.Type:
        "Return the Type instance of this symbol."
        return self._type
        
    def get_namesymbol_type(self) -> str:
        "Return the type of NameSymbol this symbol is (var, const, param, func)"
        raise NotImplementedError()
        
class VarSymbol(NameSymbol):
    def __init__(self, name: str, type: ast.Type, is_static: bool, node: ast.VarDecl):
        super().__init__(name, type)
        self._isstatic = is_static
        self._node = node
    
    def is_static(self) -> bool:
        "Return `True` if the variable is static"
        return self._isstatic
    
    def get_node(self) -> ast.VarDecl:
        "Return the VarDecl node associated to this symbol"
        return self._node
    
    def get_namesymbol_type(self) -> str:
        return "var"

class ConstSymbol(NameSymbol):
    def __init__(self, name: str, type: ast.Type, is_static: bool, node: ast.ConstDecl):
        super().__init__(name, type)
        self._isstatic = is_static
        self._node = node
    
    def is_static(self) -> ast.Expr | None:
        "Return `True` if the constant is static"
        return self._isstatic
    
    def get_node(self) -> ast.VarDecl:
        "Return the VarDecl node associated to this symbol"
        return self._node
    
    def get_namesymbol_type(self) -> str:
        return "const"

class ParamSymbol(NameSymbol):        
    def get_namesymbol_type(self) -> str:
        return "param"

class FuncSymbol(NameSymbol):
    def __init__(self, name: str, type: ast.Type, is_static: bool, is_inline: bool, functable: FuncTable):
        super().__init__(name, type)
        self._isstatic = is_static
        self._isinline = is_inline
        self._functable = functable
    
    def is_static(self) -> bool:
        "Return `True` if the constant is static"
        return self._isstatic
    
    def is_inline(self) -> bool:
        "Return `True` if the constant is inline"
        return self._isinline
    
    def get_namesymbol_type(self) -> str:
        return "func"
    
    def get_created_functable(self) -> FuncTable:
        "Return the FuncTable associated to this FuncSymbol."
        return self._functable

class TypeSymbol(Symbol):
    def __init__(self, name: str, type: ast.Type):
        super().__init__(name)
        self._type = type
        
    def get_type(self) -> ast.Type:
        return self._type

class LabelSymbol(Symbol): pass