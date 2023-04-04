from __future__ import annotations
import internals.astnodes as ast
import internals.nssymtab as nsst
import internals.nslog as nslog

"""
Module responsible for creating and maintaining the symbol table for an AST.
"""

__the_tree: nsst.SymbolTable  = None

def GetSymbolTable() -> nsst.SymbolTable | None:
    "Return the current SymbolTable, or None if it hasn't been instantiated"
    return __the_tree

def GenerateTable(as_tree: ast.Module | ast.FuncDecl | ast.Stmt) -> bool:
    """
    Generate or regenerate the symbol table from the AST Module passed to this method.
    
    Returns True if it was successful, False otherwise.
    """
    global __the_tree
    if not isinstance(as_tree, ast.Module): return False
    visitor = __STNodeVisitor()
    visitor.visit(as_tree)
    if visitor.success:
        __the_tree = visitor.symtab
    return visitor.success

def CompareTypesEq(type1: ast.Type, type2: ast.Type) -> bool:
    """
    Compares two types directly by name.
    
    No type expansion is done.
    """
    if not isinstance(type1, ast.Type) or type1.__class__ != type2.__class__: return False
    
    # Void types are always equivalent
    if isinstance(type1, ast.VoidType): return True
    
    # Reference types are not expanded so we only check for name matching
    if isinstance(type1, ast.RefType): return type1.ref_type_name == type2.ref_type_name
    
    # Int types match if they have the same size
    if isinstance(type1, ast.IntType): return type1.type == type2.type
    
    # Array types match if they have the same underlying type
    if isinstance(type1, ast.ArrayType):
        return CompareTypesEq(type1.inner_type, type2.inner_type)
    
    # Func types match if they have the same properties
    if isinstance(type1, ast.FuncType):
        if type1.is_variadic != type2.is_variadic: return False
        if not CompareTypesEq(type1.return_type, type2.return_type): return False
        if len(type1.param_types) != len(type2.param_types): return False
        return False not in map(lambda p: CompareTypesEq(p[0], p[1]), zip(type1.param_types, type2.param_types))
    
    # Struct types match if they have the same members
    if isinstance(type1, (ast.StructType, ast.UnionType)):
        if len(type1.members) != len(type2.members): return False
        def memEq(m: tuple[ast.MemberData, ast.MemberData]) -> bool:
            m1 = m[0]
            m2 = m[1]
            if m1.name != m2.name: return False
            if m1.bits != m2.bits: return False
            return CompareTypesEq(m1.type, m2.type)
        return False not in map(memEq, zip(type1.members, type2.members))
        
    return False # Something went wrong

def ExpandType(scope: nsst.SymbolTable, type: ast.Type, recursive: bool=True) -> ast.Type | None:
    "Expand a RefType. Recursive by default. Returns None for undefined type references"
    if not isinstance(type, ast.Type): return None
    while isinstance(type, ast.RefType):
        type = scope.get_typesym(type.ref_type_name)
        if not recursive: break
    return type

def CompareTypesEquiv(scope: nsst.SymbolTable, type1: ast.Type, type2: ast.Type) -> bool | None:
    "Compares two types with type expansion if necessary. Returns None if a type could not be expanded"
    if not isinstance(type1, ast.Type) or not isinstance(type2, ast.Type): return False
    
    # Reference types must be expanded
    type1 = ExpandType(scope, type1)
    type2 = ExpandType(scope, type2)
    
    if not type1 or not type2 or type1.__class__ != type2.__class__: return False
    
    # Expand array inner types
    if isinstance(type1, ast.ArrayType):
        return CompareTypesEquiv(scope, type1.inner_type, type2.inner_type)
    
    # Func types match if they have the same properties
    if isinstance(type1, ast.FuncType):
        if type1.is_variadic != type2.is_variadic: return False
        if not CompareTypesEquiv(type1.return_type, type2.return_type): return False
        if len(type1.param_types) != len(type2.param_types): return False
        return False not in map(lambda p1, p2: CompareTypesEquiv(p1, p2), zip(type1.param_types, type2.param_types))
    
    # Struct types match if they have the same members
    if isinstance(type1, (ast.StructType, ast.UnionType)):
        if len(type1.members) != len(type2.members): return False
        def memEq(m1: ast.MemberData, m2: ast.MemberData) -> bool:
            if m1.name != m2.name: return False
            if m1.bits != m2.bits: return False
            return CompareTypesEquiv(m1.type, m2.type)
        return False not in map(memEq, zip(type1.members, type2.members))
    
    # Otherwise just check normally
    return CompareTypesEq(type1, type2)

class __STNodeVisitor(ast.NodeVisitor):
    L_UNKNOWN = 1
    L_INVALID_SYM_REDECL = 10
    L_TYPE_MISMATCH = 11
    L_FUNC_REDECL_MISMATCH = 12
    L_FUNC_PARAM_TWICE = 13
    L_VAR_REDECL_MISMATCH = 14
    L_CANNOT_REDEFINE = 15
    L_USE_BEFORE_DECL = 20
    
    def __init__(self):
        self.success = True
        self.symtab: nsst.SymbolTable | None = None
        self.curtab: nsst.SymbolTable | None = None
        self.logger = nslog.LoggerFactory.getLogger()
        self.globalpass = True # Used to allow global-level name resolution before local level
        
    def _fatal(self, code: int, error: str):
        "Throw a fatal error which marks lex as unsuccessful and aborts."
        self.logger.fatal(f"{{ST{code:02}}} - {error}")
        self.success = False
        raise Exception("nsstbuilder encountered a fatal error.")
        
    def visit_Module(self, modl: ast.Module) -> ast.AST:
        self.logger.debug(f"{(modl.lineno, modl.col_offset)} found Module, creating new scope.")
        self.logger.increasepad()
        
        # Do first global-level pass
        self.logger.debug("global pass")
        self.logger.increasepad()
        self.symtab = self.curtab = nsst.ModuleTable(modl, self.curtab)
        for child in ast.iter_child_nodes(modl):
            self.visit(child)
        self.logger.debug("global pass terminated.")
        self.logger.decreasepad()
        
        self.logger.debug("local pass")
        self.logger.increasepad()
        self.globalpass = False
        
        # Do second local-level pass
        super().generic_visit(modl)
        
        self.logger.debug("global pass terminated.")
        self.logger.decreasepad()
        
        self.logger.debug(f"finished analysing Module at {(modl.lineno, modl.col_offset)}-{(modl.end_lineno, modl.end_col_offset)}.")
        self.logger.decreasepad()
        self.curtab = self.curtab.get_parent()
        return modl
    
    def visit_FuncDecl(self, fdecl: ast.FuncDecl) -> ast.AST:
        self.logger.debug(f"{(fdecl.lineno, fdecl.col_offset)} found FuncDecl {fdecl.name}.")
        self.logger.increasepad()
        
        # Check if function already exists
        funcsym = self.curtab.get_namesym(fdecl.name, localonly=True)
        if funcsym != None:
            self.logger.debug(f"symbol {funcsym.get_name()} already exists, checking compatibility")
            self.logger.increasepad()
            if not isinstance(funcsym, nsst.FuncSymbol):
                self._fatal(self.L_INVALID_SYM_REDECL, f"{(fdecl.lineno, fdecl.col_offset)} invalid redeclaration of symbol {funcsym.get_name()}")
            if funcsym.is_static() != fdecl.is_static:
                self._fatal(self.L_FUNC_REDECL_MISMATCH, f"{(fdecl.lineno, fdecl.col_offset)} previous declaration of function {funcsym.get_name()} does not match static status.")
            if funcsym.is_inline() != fdecl.is_inline:
                self._fatal(self.L_FUNC_REDECL_MISMATCH, f"{(fdecl.lineno, fdecl.col_offset)} previous declaration of function {funcsym.get_name()} does not match inline status.")
            if not CompareTypesEq(funcsym.get_type(), fdecl.type):
                self._fatal(self.L_TYPE_MISMATCH, f"{(fdecl.lineno, fdecl.col_offset)} previous redeclaration of function {funcsym.get_name()} does not match type.")
            if fdecl.body and (funcsym.get_created_functable() and funcsym.get_created_functable()._node.body):
                self._fatal(self.L_CANNOT_REDEFINE, f"{(fdecl.lineno, fdecl.col_offset)} cannot define function {funcsym.get_name()} twice")
            
            self.logger.debug(f"symbol {funcsym.get_name()} is compatible.")
            self.logger.decreasepad()
            if not fdecl.body:
                self.logger.debug(f"exiting from symbol {funcsym.get_name()} early since there is no body to override previous declaration.")
                self.logger.decreasepad()
                return fdecl
        
        if self.globalpass or not fdecl.body:
            # Function is being declared, don't create a function symbol table
            funcsym = nsst.FuncSymbol(fdecl.name, fdecl.type, fdecl.is_static, fdecl.is_inline, None)
            fdecl.symref = funcsym
            self.curtab._bind_symbol(fdecl.name, funcsym)
        else:
            # Function is being defined, create a function symbol table
            functable = nsst.FuncTable(fdecl, self.curtab)
            
            # Create Function symbol
            funcsym = nsst.FuncSymbol(fdecl.name, fdecl.type, fdecl.is_static, fdecl.is_inline, functable)
            fdecl.symref = funcsym
            self.curtab._bind_symbol(fdecl.name, funcsym, overwrite=True)
            self.curtab._add_child(functable)
            self.curtab = functable
            
            for pname, ptype in zip(fdecl.param_names, fdecl.type.param_types):
                if self.curtab.get_namesym(pname, localonly=True):
                    self._fatal(self.L_FUNC_PARAM_TWICE, f"{(fdecl.lineno, fdecl.col_offset)} function parameters cannot have the same name '{pname}' twice.")
                self.curtab._bind_symbol(pname, nsst.ParamSymbol(pname, ptype))
        
            # Visit children
            super().generic_visit(fdecl)
            
            self.curtab = self.curtab.get_parent()
        
        # Exit
        self.logger.debug(f"finished analysing FuncDecl {fdecl.name} at {(fdecl.lineno, fdecl.col_offset)}-{(fdecl.end_lineno, fdecl.end_col_offset)}.")
        self.logger.decreasepad()
        return fdecl
    
    def visit_CompoundStmt(self, cstmt: ast.CompoundStmt):
        self.logger.debug(f"{(cstmt.lineno, cstmt.col_offset)} found CompoundStmt, creating new scope.")
        self.logger.increasepad()
        
        # Create table
        blocktable = nsst.BlockTable(cstmt, self.curtab)
        cstmt.symref = blocktable
        self.curtab._add_child(blocktable)
        self.curtab = blocktable
        
        # Visit children
        super().generic_visit(cstmt)
        
        self.curtab = self.curtab.get_parent()
        
        # Exit
        self.logger.debug(f"finished analysing CompoundStmt at {(cstmt.lineno, cstmt.col_offset)}-{(cstmt.end_lineno, cstmt.end_col_offset)}.")
        self.logger.decreasepad()
        return cstmt
    
    def visit_TypeDecl(self, tdecl: ast.TypeDecl) -> ast.AST:
        self.logger.debug(f"{(tdecl.lineno, tdecl.col_offset)} found TypeDecl {tdecl.name}.")
        self.logger.increasepad()
        
        if not self.globalpass and self.curtab.is_global():
            self.logger.debug(f"ignoring global typedefs in local pass.")
            self.logger.debug(f"finished analysing TypeDecl at {(tdecl.lineno, tdecl.col_offset)}-{(tdecl.end_lineno, tdecl.end_col_offset)}.")
            self.logger.decreasepad()
            return tdecl
        
        # Check that type doesn't already exist
        typesym = self.curtab.get_typesym(tdecl.name, localonly=True)
        if typesym != None:
            self._fatal(self.L_CANNOT_REDEFINE, f"{(tdecl.lineno, tdecl.col_offset)} cannot define type {typesym.get_name()} twice in the same scope.")
        
        # Create symbol
        typesym = nsst.TypeSymbol(tdecl.name, tdecl.type)
        tdecl.symref = typesym
        self.curtab._bind_symbol(tdecl.name, typesym)
        
        # Visit children
        super().generic_visit(tdecl)
        
        # Exit
        self.logger.debug(f"finished analysing TypeDecl {tdecl.name} at {(tdecl.lineno, tdecl.col_offset)}-{(tdecl.end_lineno, tdecl.end_col_offset)}.")
        self.logger.decreasepad()
        return tdecl
    
    def visit_VarDecl(self, vdecl: ast.VarDecl) -> ast.AST:
        self.logger.debug(f"{(vdecl.lineno, vdecl.col_offset)} found VarDecl {vdecl.name}.")
        self.logger.increasepad()
        
        if not self.globalpass and self.curtab.is_global():
            self.logger.debug(f"ignoring global vardefs in local pass.")
            self.logger.debug(f"finished analysing VarDecl {vdecl.name} at {(vdecl.lineno, vdecl.col_offset)}-{(vdecl.end_lineno, vdecl.end_col_offset)}.")
            self.logger.decreasepad()
            return vdecl
        
        # Check if variable already exists
        varsym = self.curtab.get_namesym(vdecl.name, localonly=True)
        if varsym != None:
            self.logger.debug(f"symbol {varsym.get_name()} already exists, checking compatibility")
            self.logger.increasepad()
            if not self.curtab.is_global():
                self._fatal(self.L_CANNOT_REDEFINE, f"{(vdecl.lineno, vdecl.col_offset)} cannot define variable {varsym.get_name()} twice in local scope.")
            if not isinstance(varsym, nsst.VarSymbol):
                self._fatal(self.L_INVALID_SYM_REDECL, f"{(vdecl.lineno, vdecl.col_offset)} invalid redeclaration of symbol {varsym.get_name()}")
            if varsym.is_static() != vdecl.is_static:
                self._fatal(self.L_VAR_REDECL_MISMATCH, f"{(vdecl.lineno, vdecl.col_offset)} previous declaration of variable {varsym.get_name()} does not match static status.")
            if not CompareTypesEq(varsym.get_type(), vdecl.type):
                self._fatal(self.L_TYPE_MISMATCH, f"{(vdecl.lineno, vdecl.col_offset)} previous declaration of variable {varsym.get_name()} does not match type.")
            if vdecl.value and varsym.get_node().value:
                self._fatal(self.L_CANNOT_REDEFINE, f"{(vdecl.lineno, vdecl.col_offset)} cannot define variable {varsym.get_name()} twice")
            
            self.logger.debug(f"symbol {varsym.get_name()} is compatible.")
            self.logger.decreasepad()
            if not vdecl.value:
                self.logger.debug(f"exiting from symbol {varsym.get_name()} early since there is no value to override previous declaration.")
                self.logger.decreasepad()
                return vdecl
        
        # Create symbol
        varsym = nsst.VarSymbol(vdecl.name, vdecl.type, vdecl.is_static, vdecl)
        vdecl.symref = varsym
        self.curtab._bind_symbol(vdecl.name, varsym, overwrite=True)
        
        # Visit children
        super().generic_visit(vdecl)
        
        # Exit
        self.logger.debug(f"finished analysing VarDecl {vdecl.name} at {(vdecl.lineno, vdecl.col_offset)}-{(vdecl.end_lineno, vdecl.end_col_offset)}.")
        self.logger.decreasepad()
        return vdecl
    
    def visit_ConstDecl(self, cdecl: ast.ConstDecl) -> ast.AST:
        self.logger.debug(f"{(cdecl.lineno, cdecl.col_offset)} found ConstDecl {cdecl.name}.")
        self.logger.increasepad()
        
        if not self.globalpass:
            self.logger.debug(f"ignoring global constdefs in local pass.")
            self.logger.debug(f"finished analysing ConstDecl at {(cdecl.lineno, cdecl.col_offset)}-{(cdecl.end_lineno, cdecl.end_col_offset)}.")
            self.logger.decreasepad()
            return cdecl
        
        # Check that constant doesn't already exist
        constsym = self.curtab.get_namesym(cdecl.name, localonly=True)
        if constsym != None:
            self._fatal(self.L_CANNOT_REDEFINE, f"{(cdecl.lineno, cdecl.col_offset)} cannot define constant {constsym.get_name()}.")
        
        # Create symbol
        constsym = nsst.ConstSymbol(cdecl.name, cdecl.type, cdecl.is_static, cdecl)
        cdecl.symref = constsym
        self.curtab._bind_symbol(cdecl.name, constsym)
        
        # Visit children
        super().generic_visit(cdecl)
        
        # Exit
        self.logger.debug(f"finished analysing ConstDecl {cdecl.name} at {(cdecl.lineno, cdecl.col_offset)}-{(cdecl.end_lineno, cdecl.end_col_offset)}.")
        self.logger.decreasepad()
        return cdecl
    
    def visit_NameExpr(self, nexpr: ast.NameExpr) -> ast.AST:
        namesym = self.curtab.get_namesym(nexpr.name)
        if namesym == None:
            self._fatal(self.L_USE_BEFORE_DECL, f"{(nexpr.lineno, nexpr.col_offset)} symbol {nexpr.name} is used here before being declared.")
        
        nexpr.symref = namesym
        namesym._reference()
        
        self.logger.debug(f"linked NameExpr {nexpr.name} to symbol at {(nexpr.lineno, nexpr.col_offset)}-{(nexpr.end_lineno, nexpr.end_col_offset)}.")
        return nexpr