from __future__ import annotations
import internals.astnodes as ast
import internals.nssymtab as nssym
import internals.nsstbuilder as nsst
import internals.nslog as nslog
import internals.nstypes as nstypes

def GetExpressionType(scope: nssym.SymbolTable, expr: ast.Expr) -> ast.Type:
    "Returns the type of an expression. The nodes must have been semantically checked, otherwise behaviour is undefined."
    if isinstance(expr, ast.NameExpr): return nsst.ExpandType(scope, scope.get_namesym(expr.name).get_type())
    if isinstance(expr, ast.IntExpr): return expr.type
    if isinstance(expr, ast.StrExpr): return ast.ArrayType(
        is_volatile=False,
        inner_type=ast.IntType(is_volatile=False, type="int"),
        size=ast.IntExpr(
            type=ast.IntType(is_volatile=False, type="int"),
            value=len(expr.utf8)))
    if isinstance(expr, ast.SzexprExpr): return ast.IntType(is_volatile=False, type="long")
    if isinstance(expr, ast.SztypeExpr): return ast.IntType(is_volatile=False, type="long")
    if isinstance(expr, ast.CallExpr): return nsst.ExpandType(scope, nsst.ExpandType(scope, GetExpressionType(scope, expr.func_expr)).return_type)
    if isinstance(expr, ast.IndexExpr): return nsst.ExpandType(scope, nsst.ExpandType(scope, GetExpressionType(scope, expr.array_expr)).inner_type)
    if isinstance(expr, ast.AccessExpr):
        for member in nsst.ExpandType(scope, GetExpressionType(scope, expr.record_expr)).members:
            if member.name == expr.member_name: return nsst.ExpandType(scope, member.type)
        raise Exception() # This should never be reached if checking was successful
    if isinstance(expr, ast.CastExpr): return nsst.ExpandType(scope, expr.cast_type)
    if isinstance(expr, ast.DerefExpr): return nsst.ExpandType(scope, nsst.ExpandType(scope, GetExpressionType(scope, expr.pointer_expr)).inner_type)
    if isinstance(expr, ast.AddrOfExpr): return ast.ArrayType(
        is_volatile=False,
        inner_type=nsst.ExpandType(scope, GetExpressionType(scope, expr.expr)),
        size=False)
    if isinstance(expr, ast.UnaryExpr): return nsst.ExpandType(scope, GetExpressionType(scope, expr.expr))
    if isinstance(expr, ast.UnaryCondExpr): return ast.IntType(is_volatile=False, type="int")
    if isinstance(expr, ast.BinaryExpr): return nsst.ExpandType(scope, GetExpressionType(scope, expr.left))
    if isinstance(expr, ast.BinaryCondExpr): return ast.IntType(is_volatile=False, type="int")
    if isinstance(expr, ast.TernaryExpr): return nsst.ExpandType(scope, GetExpressionType(scope, expr.true_expr))
    if isinstance(expr, ast.AssignExpr): return nsst.ExpandType(scope, GetExpressionType(scope, expr.lhs))
    if isinstance(expr, ast.CommaExpr): return nsst.ExpandType(scope, GetExpressionType(scope, expr.exprs[-1]))
    if isinstance(expr, ast.ComplexExpr):
        if expr.type in ("str", "array"):
            return ast.ArrayType(
                is_volatile=False,
                inner_type=nsst.ExpandType(scope, GetExpressionType(scope, expr.value[0])),
                size=ast.IntExpr(
                    type=ast.IntType(is_volatile=False, type="long"),
                    value=len(expr.value)))
        if expr.type == "struct": return ast.StructType(
            is_volatile=False,
            members=[
                ast.MemberData(name=name, type=nsst.ExpandType(scope, GetExpressionType(scope, value)), bits=None)
                for name, value in expr.value.items()])
    raise Exception()

def CanCastTypes(scope: nssym.SymbolTable, from_type: ast.Type, to_type: ast.Type) -> None | str:
    "Check if two types are compatible. Returns None if successful or an error string otherwise."
    is_valid = False
    
    if isinstance(to_type, (ast.IntType, ast.ArrayType, ast.FuncType)):
        if not isinstance(from_type, (ast.IntType, ast.ArrayType, ast.FuncType)):
            return "integers, arrays, pointers, and functions can only be casted to each other."
        is_valid = True
    
    if not is_valid:
        if not isinstance(from_type, to_type.__class__):
            return "inner type and cast type are not of the same type."
        if not nsst.CompareTypesEquiv(scope, from_type, to_type):
            return "inner type and cast type are not equivalent."
    
    return None

class ExprProperty:
    def __init__(self):
        self._const: bool = False
        self._lvalue: bool = False
    
    def is_const(self): return self._const
    def set_const(self, const: bool): self._const = const
    def is_lvalue(self): return self._lvalue
    def is_rvalue(self): return not self._lvalue
    def set_lvalue(self, lvalue: bool): self._lvalue = lvalue

class ExprPropertyChecker(ast.NodeVisitor):
    "Return the properties of an expression."
    def __init__(self, scope: nssym.SymbolTable):
        self.scope = scope
    
    _mapping: dict[ast.Expr, tuple[bool, bool]] = {
        ast.IntExpr: (True, False),
        ast.StrExpr: (False, False),
        ast.SzexprExpr: (True, False),
        ast.SztypeExpr: (True, False),
        ast.CallExpr: (False, False),
        ast.IndexExpr: (False, True),
        ast.AccessExpr: (False, True),
        ast.DerefExpr: (False, True),
        ast.AddrOfExpr: (False, False),
        ast.AssignExpr: (False, True),
        ast.ComplexExpr: (False, False)
    }
    
    def generic_visit(self, node: ast.AST) -> ExprProperty:
        if node.__class__ in ExprPropertyChecker._mapping:
            mapping = ExprPropertyChecker._mapping[node.__class__]
            prop = ExprProperty()
            prop.set_const(mapping[0])
            prop.set_lvalue(mapping[1])
            return prop
        return False
    
    def visit_NameExpr(self, node: ast.NameExpr) -> ExprProperty:
        prop = ExprProperty()
        namesymbol = self.scope.get_namesym(node.name)
        if isinstance(namesymbol, nssym.VarSymbol): prop.set_lvalue(True)
        if isinstance(namesymbol, nssym.ConstSymbol): prop.set_const(True)
        return prop
    
    def visit_CastExpr(self, node: ast.CastExpr) -> ExprProperty:
        return self.visit(node.expr)
    
    def visit_UnaryExpr(self, node: ast.UnaryExpr) -> ExprProperty:
        prop = ExprProperty()
        prop.set_const(self.visit(node.expr).is_const())
        prop.set_lvalue(False)
        return prop
    
    def visit_UnaryCondExpr(self, node: ast.UnaryCondExpr) -> ExprProperty:
        prop = ExprProperty()
        prop.set_const(self.visit(node.expr).is_const())
        prop.set_lvalue(False)
        return prop
    
    def visit_BinaryExpr(self, node: ast.BinaryExpr) -> ExprProperty:
        prop = ExprProperty()
        prop.set_const(self.visit(node.left).is_const() and self.visit(node.right).is_const())
        prop.set_lvalue(False)
        return prop
    
    def visit_BinaryCondExpr(self, node: ast.BinaryCondExpr) -> ExprProperty:
        prop = ExprProperty()
        prop.set_const(self.visit(node.left).is_const() and self.visit(node.right).is_const())
        prop.set_lvalue(False)
        return prop
    
    def visit_TernaryExpr(self, node: ast.TernaryExpr) -> ExprProperty:
        prop = ExprProperty()
        true_prop: ExprProperty = self.visit(node.true_expr)
        false_prop: ExprProperty = self.visit(node.false_expr)
        prop.set_const(true_prop.is_const() and false_prop.is_const())
        prop.set_lvalue(true_prop.is_value() and false_prop.is_lvalue())
        return prop
    
    def visit_CommaExpr(self, node: ast.CommaExpr) -> ExprProperty:
        prop = ExprProperty()
        prop.set_const(False not in [self.visit(expr).is_const() for expr in node.exprs])
        prop.set_lvalue(self.visit(node.exprs[-1]).is_lvalue())
        return prop

class Checker(ast.NodeVisitor):
    L_UNKNOWN = 1
    L_TYPENOTEXIST = 10
    L_CIRCTYPEDEF = 20
    L_INVALIDBITS = 30
    L_VOIDTYPE_DISALLOWED = 40
    L_TYPE_MISMATCH = 50
    L_INT_PRECISION = 51
    L_MISSING_MEMBER = 60
    L_LABEL_NOT_EXIST = 70
    L_LABEL_WRONG_TYPE = 80
    L_NOT_IN_IF_ITER = 90
    
    def __init__(self):
        self.scope: nssym.SymbolTable = nsst.GetSymbolTable()
        self.logger = nslog.LoggerFactory.getLogger()
        self.success = True
        self.typedef_check = True
        self.typenames: list[str] = []
        self.refpos: tuple[int, int] = (None,None)
        self.ret_type: ast.Type = None # Return type for current function
        self.last_if: ast.IfStmt | None = None
        self.last_iter: ast.IterStmt | None = None
    
    def _fatal(self, code: int, error: str):
        "Throw a fatal error which marks semantic analysis as unsuccessful and aborts."
        self.logger.fatal(f"{{C{code:02}}} {error}")
        self.success = False
        raise Exception("nschk encountered a fatal error.")
    
    def visit_Module(self, modl: ast.Module) -> ast.AST:
        "Check typedecls first"
        self.logger.debug("first pass, checking types")
        self.logger.increasepad()
        super().generic_visit(modl)
        self.logger.decreasepad()
        
        self.typedef_check = False
        self.logger.debug("second pass, checking everything else")
        self.logger.increasepad()
        super().generic_visit(modl)
        self.logger.decreasepad()
    
    # Manage statements
    def visit_IfStmt(self, istmt: ast.IfStmt) -> ast.AST:
        "Check that the condition expression is integral, array, pointer, or function."
        if self.typedef_check: return istmt
        
        last_if = self.last_if
        self.last_if = istmt
        super().generic_visit(istmt)
        self.last_if = last_if
        
        cond_expr_type = GetExpressionType(self.scope, istmt.cond_expr)
        
        if not isinstance(cond_expr_type, (ast.IntType, ast.ArrayType, ast.FuncType)):
            self._fatal(self.L_TYPE_MISMATCH, f"{istmt.lineno, istmt.col_offset} IfStmt expects an integer, array, pointer, or function as conditional expression, got {cond_expr_type.__class__.__name__}")

        return istmt
    
    def visit_IterStmt(self, istmt: ast.IterStmt) -> ast.AST:
        "Check that the condition expression is integral, array, pointer, or function."
        if self.typedef_check: return istmt
        
        last_iter = self.last_iter
        self.last_iter = istmt
        super().generic_visit(istmt)
        self.last_iter = last_iter
        
        cond_expr_type = GetExpressionType(self.scope, istmt.cond_expr)
        
        if not isinstance(cond_expr_type, (ast.IntType, ast.ArrayType, ast.FuncType)):
            self._fatal(self.L_TYPE_MISMATCH, f"{istmt.lineno, istmt.col_offset} IterStmt expects an integer, array, pointer, or function as conditional expression, got {cond_expr_type.__class__.__name__}")

        return istmt
    
    def visit_ContinueStmt(self, cstmt: ast.ContinueStmt) -> ast.AST:
        "Check that if there is a label, it points to a loop."
        if self.typedef_check: return cstmt
        
        super().generic_visit(cstmt)
        
        if cstmt.label != None:
            labelsym = self.scope.get_labelsym(cstmt.label)
            if labelsym == None:
                self._fatal(Checker.L_LABEL_NOT_EXIST, f"{cstmt.lineno, cstmt.col_offset} cannot find label '{cstmt.label}' in symbol table.")
            if not isinstance(labelsym.get_node(), ast.IterStmt):
                self._fatal(Checker.L_LABEL_WRONG_TYPE, f"{cstmt.lineno, cstmt.col_offset} ContinueStmt got label '{cstmt.label}' for non-IterStmt block at {labelsym.get_node().lineno, labelsym.get_node().col_offset}.")
            labelsym._reference()
            cstmt.symref = labelsym.get_node()
        else:
            if not self.last_iter:
                self._fatal(Checker.L_NOT_IN_IF_ITER, f"{cstmt.lineno, cstmt.col_offset} ContinueStmt not in IterStmt")

            cstmt.symref = self.last_iter
        
        return cstmt
    
    def visit_BreakStmt(self, bstmt: ast.BreakStmt) -> ast.AST:
        "Check that if there is a label, it points to the appropriate block."
        if self.typedef_check: return bstmt
        
        if bstmt.breakif: t = ast.IfStmt
        else: t = ast.IterStmt
        
        super().generic_visit(bstmt)
        
        if bstmt.label != None:
            labelsym = self.scope.get_labelsym(bstmt.label)
            if labelsym == None:
                self._fatal(Checker.L_LABEL_NOT_EXIST, f"{bstmt.lineno, bstmt.col_offset} cannot find label '{bstmt.label}' in symbol table.")
            
            if not isinstance(labelsym.get_node(), t):
                self._fatal(Checker.L_LABEL_WRONG_TYPE, f"{bstmt.lineno, bstmt.col_offset} {t.__name__}-type BreakStmt got label '{bstmt.label}' for non-{t.__name__} block at {labelsym.get_node().lineno, labelsym.get_node().col_offset}.")
            labelsym._reference()
            bstmt.symref = labelsym.get_node()
        else:
            last_check = self.last_if if bstmt.breakif else self.last_iter
            
            if not last_check or not isinstance(last_check, t):
                self._fatal(Checker.L_NOT_IN_IF_ITER, f"{bstmt.lineno, bstmt.col_offset} {t.__name__}-type BreakStmt not in {t.__name__}.")
        
            bstmt.symref = last_check
        
        return bstmt
    
    def visit_ReturnStmt(self, rstmt: ast.ReturnStmt) -> ast.AST:
        "Check that the return expression is the same as the function's value, or None if the value returns void."
        if self.typedef_check: return rstmt
        
        super().generic_visit(rstmt)
        
        if isinstance(self.ret_type, ast.VoidType):
            if rstmt.ret_expr != None:
                self._fatal(Checker.L_TYPE_MISMATCH, f"{rstmt.lineno, rstmt.col_offset} enclosing function returns 'void', but ReturnStmt returns expression.")
        else:
            if rstmt.ret_expr == None:
                self._fatal(Checker.L_TYPE_MISMATCH, f"{rstmt.lineno, rstmt.col_offset} enclosing function returns '{self.ret_type.__class__.__name__}', but ReturnStmt does not return an expression.")
            ret_expr_type = GetExpressionType(self.scope, rstmt.ret_expr)
            if not nsst.CompareTypesEquiv(self.scope, self.ret_type, ret_expr_type):
                self._fatal(Checker.L_TYPE_MISMATCH, f"{rstmt.lineno, rstmt.col_offset} function expects a return value of type '{self.ret_type.__class__.__name__}', got different '{ret_expr_type.__class__.__name__}'.")
        
        return rstmt
                
    # Manage declarations
    def __check_Decl(self, decl: ast.VarDecl | ast.ConstDecl) -> ast.AST:
        "Check that the declared type and init expression type match."        
        if decl.value == None: return decl
        
        decl_type = nsst.ExpandType(self.scope, decl.type)
        expr_type = GetExpressionType(self.scope, decl.value)
        
        if not nsst.CompareTypesEquiv(self.scope, decl_type, expr_type):
            self._fatal(Checker.L_TYPE_MISMATCH, f"{decl.lineno, decl.col_offset} declaration expected {decl_type.__class__.__name__}, got different {expr_type.__class__.__name__}.")
        
        if isinstance(decl.value, ast.ComplexExpr) and decl.value.type != "struct" and decl_type.size == None:
            if isinstance(decl.type, ast.ArrayType):
                decl.type.size = ast.IntExpr(
                    type=ast.IntType(is_volatile=False, type="long"),
                    value=len(decl.value.value))
        
        return decl
    
    def visit_VarDecl(self, decl: ast.VarDecl) -> ast.AST:
        "Check that the type of the VarDecl and its init expression match."
        if self.typedef_check: return decl
        
        super().generic_visit(decl)
        
        self.__check_Decl(decl)
        
        # Recheck type in case it was an ArrayType with a new size value.
        self.visit(decl.type)
        
        return self.__check_Decl(decl)
            
    def visit_ConstDecl(self, decl: ast.ConstDecl) -> ast.AST:
        "Check that the type of the ConstDecl and its init expression match."
        if self.typedef_check: return decl
        
        super().generic_visit(decl)
        
        decl_type = nsst.ExpandType(self.scope, decl.type)
        if not isinstance(decl_type, ast.IntType):
            self._fatal(Checker.L_TYPE_MISMATCH, f"{decl.lineno, decl.col_offset} ConstDecl must be of an integral type.")
        
        epchk = ExprPropertyChecker(self.scope)
        props: ExprProperty = epchk.visit(decl.value)
        
        if not props.is_const():
            self._fatal(Checker.L_TYPE_MISMATCH, f"{decl.value.lineno, decl.value.col_offset} ConstDecl initial expression must be constant.")
        
        return self.__check_Decl(decl)
    
    # Manage expressions
    def visit_CallExpr(self, cexpr: ast.CallExpr) -> ast.AST:
        "Check that parameters and arguments match."
        if self.typedef_check: return cexpr
        
        super().generic_visit(cexpr)
        
        func_expr_type = GetExpressionType(self.scope, cexpr.func_expr)
        
        if not isinstance(func_expr_type, ast.FuncType):
            start = cexpr.func_expr.lineno, cexpr.func_expr.col_offset
            end = cexpr.func_expr.end_lineno, cexpr.func_expr.end_col_offset
            self._fatal(self.L_TYPE_MISMATCH, f"expected expression to be FuncType at {start}-{end}")
        
        # Check that the right amount of parameters are being passed.
        nparams = len(func_expr_type.param_types)
        nargs = len(cexpr.args)
        if nargs < nparams or not (func_expr_type.is_variadic or nargs == nparams):
            self._fatal(self.L_TYPE_MISMATCH, f"function call  at {cexpr.lineno, cexpr.col_offset}-{cexpr.end_lineno, cexpr.end_col_offset} expects {nparams} parameters {'or more ' if func_expr_type.is_variadic else ''}but got {nargs}.")
        
        for i, param_type in enumerate(func_expr_type.param_types):
            if not nsst.CompareTypesEquiv(self.scope, param_type, GetExpressionType(self.scope, cexpr.args[i])):
                self._fatal(self.L_TYPE_MISMATCH, f"mismatched type for argument {i} of function call at {start}-{end}")
        
        return cexpr

    def visit_IndexExpr(self, iexpr: ast.IndexExpr) -> ast.AST:
        "Check that the index_expr is integral and array_expr is an array."
        if self.typedef_check: return iexpr
        
        super().generic_visit(iexpr)
        
        array_expr_type = GetExpressionType(self.scope, iexpr.array_expr)
        if not isinstance(array_expr_type, ast.ArrayType):
            start = iexpr.array_expr.lineno, iexpr.array_expr.col_offset
            end = iexpr.array_expr.end_lineno, iexpr.array_expr.end_col_offset
            self._fatal(self.L_TYPE_MISMATCH, f"expected expression to be ArrayType at {start}-{end}")

        if isinstance(array_expr_type.inner_type, ast.VoidType):
            self._fatal(Checker.L_VOIDTYPE_DISALLOWED, f"{iexpr.lineno, iexpr.col_offset} cannot index an array of voids.")

        index_expr_type = GetExpressionType(self.scope, iexpr.index_expr)
        start = iexpr.index_expr.lineno, iexpr.index_expr.col_offset
        end = iexpr.index_expr.end_lineno, iexpr.index_expr.end_col_offset
        if not isinstance(index_expr_type, ast.IntType):
            self._fatal(self.L_TYPE_MISMATCH, f"expected expression to be IntType at {start}-{end}")
        if index_expr_type.type not in ("int", "long"):
            self._fatal(self.L_INT_PRECISION, f"IntType index at {start}-{end} must be int or long")
        return iexpr
    
    def visit_AccessExpr(self, aexpr: ast.AccessExpr) -> ast.AST:
        "Check that the member being accessed exists."
        if self.typedef_check: return aexpr
        
        super().generic_visit(aexpr)
        
        record_expr_type = GetExpressionType(self.scope, aexpr.record_expr)
        if not isinstance(record_expr_type, (ast.StructType, ast.UnionType)):
            start = aexpr.record_expr.lineno, aexpr.record_expr.col_offset
            end = aexpr.record_expr.end_lineno, aexpr.record_expr.end_col_offset
            self._fatal(self.L_TYPE_MISMATCH, f"expected expression to be StructType or UnionType at {start}-{end}")

        for member in record_expr_type.members:
            if member.name == aexpr.member_name: break
        else:
            self._fatal(self.L_MISSING_MEMBER, f"{aexpr.lineno, aexpr.col_offset} record expression does not have a member called '{aexpr.member_name}'.")
        
        return aexpr
    
    def visit_CastExpr(self, cexpr: ast.CastExpr) -> ast.AST:
        "Check that the types are compatible."
        if self.typedef_check: return cexpr
        
        super().generic_visit(cexpr)
        
        inner_expr_type = GetExpressionType(self.scope, cexpr.expr)
        cast_type = nsst.ExpandType(self.scope, cexpr.cast_type)
        
        if cexpr.signed and not isinstance(cast_type, ast.IntType):
            self._fatal(self.L_TYPE_MISMATCH, f"{cexpr.cast_type.lineno, cexpr.cast_type.col_offset} cast type cannot be signed since it is not an integral type.")
        
        can_cast = CanCastTypes(self.scope, inner_expr_type, cast_type)
        
        if can_cast:
            self._fatal(self.L_TYPE_MISMATCH, f"{cexpr.lineno, cexpr.col_offset} "+can_cast)        
        
        return cexpr
    
    def visit_DerefExpr(self, dexpr: ast.DerefExpr) -> ast.AST:
        "Check that the inner expression is ArrayType."
        if self.typedef_check: return dexpr
        
        super().generic_visit(dexpr)
        
        pointer_expr_type = GetExpressionType(self.scope, dexpr.pointer_expr)
        if not isinstance(pointer_expr_type, ast.ArrayType):
            start = dexpr.pointer_expr.lineno, dexpr.pointer_expr.col_offset
            end = dexpr.pointer_expr.end_lineno, dexpr.pointer_expr.end_col_offset
            self._fatal(self.L_TYPE_MISMATCH, f"expected expression to be ArrayType at {start}-{end}")
        
        if isinstance(pointer_expr_type.inner_type, ast.VoidType):
            self._fatal(Checker.L_VOIDTYPE_DISALLOWED, f"{dexpr.lineno, dexpr.col_offset} cannot dereference a void pointer.")
        
        return dexpr
    
    def visit_AddrOfExpr(self, aoexpr: ast.AddrOfExpr) -> ast.AST:
        "Check that the expression is an lvalue."
        if self.typedef_check: return aoexpr
        
        super().generic_visit(aoexpr)
        
        epchk = ExprPropertyChecker(self.scope)
        props: ExprProperty = epchk.visit(aoexpr.expr)
        
        if not props.is_lvalue():
            self._fatal(self.L_TYPE_MISMATCH, f"{aoexpr.lineno, aoexpr.col_offset} operand of AddrOfExpr must be an lvalue.")

        return aoexpr
    
    def visit_UnaryExpr(self, uexpr: ast.UnaryExpr) -> ast.AST:
        "Check that the operand is an integer type."
        if self.typedef_check: return uexpr
        
        super().generic_visit(uexpr)
        
        expr_type = GetExpressionType(self.scope, uexpr.expr)
        if not isinstance(expr_type, ast.IntType):
            self._fatal(self.L_TYPE_MISMATCH, f"{uexpr.lineno, uexpr.col_offset} UnaryOp '{uexpr.op.__class__.__name__}' expects an integral operand, got {expr_type.__class__.__name__}.")

        return uexpr
    
    def visit_UnaryCondExpr(self, uexpr: ast.UnaryCondExpr) -> ast.AST:
        "Check that the operand is an integer, array, pointer, or function type."
        if self.typedef_check: return uexpr
        
        super().generic_visit(uexpr)
        
        expr_type = GetExpressionType(self.scope, uexpr.expr)
        if not isinstance(expr_type, (ast.IntType, ast.ArrayType, ast.FuncType)):
            self._fatal(self.L_TYPE_MISMATCH, f"{uexpr.lineno, uexpr.col_offset} UnaryCOp '{uexpr.op.__class__.__name__}' expects an integral, array, pointer, or function operand, got {expr_type.__class__.__name__}.")

        return uexpr
    
    def visit_BinaryExpr(self, bexpr: ast.BinaryExpr) -> ast.AST:
        "Check that the operands are integers, arrays, pointers, or function type with restrictions."
        if self.typedef_check: return bexpr
        
        super().generic_visit(bexpr)
        
        left_expr_type = GetExpressionType(self.scope, bexpr.left)
        right_expr_type = GetExpressionType(self.scope, bexpr.right)
        
        if not isinstance(left_expr_type, (ast.IntType, ast.ArrayType, ast.FuncType)):
            self._fatal(self.L_TYPE_MISMATCH, f"{bexpr.left.lineno, bexpr.left.col_offset} BinaryExpr expects left operand to be an integer, array, pointer, or function, got {left_expr_type.__class__.__name__}.")
        if not isinstance(right_expr_type, (ast.IntType, ast.ArrayType, ast.FuncType)):
            self._fatal(self.L_TYPE_MISMATCH, f"{bexpr.right.lineno, bexpr.right.col_offset} BinaryExpr expects right operand to be an integer, array, pointer, or function, got {right_expr_type.__class__.__name__}.")
        
        can_cast = CanCastTypes(self.scope, right_expr_type, left_expr_type)
        
        if can_cast != None:
            self._fatal(self.L_TYPE_MISMATCH, f"{bexpr.lineno, bexpr.col_offset} left and right operands are incompatible: "+can_cast)
        
        # Check operation validity with type
        if isinstance(left_expr_type, (ast.ArrayType, ast.FuncType)) or isinstance(right_expr_type, (ast.ArrayType, ast.FuncType)):
            if not isinstance(bexpr.op, (ast.Add, ast.Sub)):
                self._fatal(self.L_TYPE_MISMATCH, f"{bexpr.lineno, bexpr.col_offset} array, pointers, and function expressions only support addition and subtraction for arithmetic.")
        
        # Check for type downgrade
        left_size = right_size = 2
        
        if isinstance(left_expr_type, ast.IntType): left_size = nstypes.CFG.INT_SIZES[left_expr_type.type]
        if isinstance(right_expr_type, ast.IntType): right_size = nstypes.CFG.INT_SIZES[right_expr_type.type]
        
        if left_size < right_size: # Downgrade
            self.logger.warn(f"{bexpr.lineno, bexpr.col_offset} downgrading right side of expression.")
        elif left_size > right_size: # Upgrade
            self.logger.warn(f"{bexpr.lineno, bexpr.col_offset} upgrading right side of expression. default behaviour is unsigned extension.")
        
        # Add conversion if necessary
        if not nsst.CompareTypesEquiv(self.scope, left_expr_type, right_expr_type):
            start = (bexpr.right.lineno, bexpr.right.col_offset)
            end = (bexpr.right.end_lineno, bexpr.right.end_col_offset)
            bexpr.right = ast.CastExpr(
                expr = bexpr.right,
                cast_type = left_expr_type,
                signed = False
            )
            bexpr.right.lineno, bexpr.right.col_offset = start
            bexpr.right.end_lineno, bexpr.right.end_col_offset = end
        
        return bexpr
    
    def visit_BinaryCondExpr(self, bexpr: ast.BinaryCondExpr) -> ast.AST:
        "Check that the operands are integers, arrays, pointers, or function type with restrictions."
        if self.typedef_check: return bexpr
        
        super().generic_visit(bexpr)
        
        left_expr_type = GetExpressionType(self.scope, bexpr.left)
        right_expr_type = GetExpressionType(self.scope, bexpr.right)
        
        if not isinstance(left_expr_type, (ast.IntType, ast.ArrayType, ast.FuncType)):
            self._fatal(self.L_TYPE_MISMATCH, f"{bexpr.left.lineno, bexpr.left.col_offset} BinaryCondExpr expects left operand to be an integer, array, pointer, or function, got {left_expr_type.__class__.__name__}.")
        if not isinstance(right_expr_type, (ast.IntType, ast.ArrayType, ast.FuncType)):
            self._fatal(self.L_TYPE_MISMATCH, f"{bexpr.right.lineno, bexpr.right.col_offset} BinaryCondExpr expects right operand to be an integer, array, pointer, or function, got {right_expr_type.__class__.__name__}.")
        
        can_cast = CanCastTypes(self.scope, right_expr_type, left_expr_type)
        
        if can_cast != None:
            self._fatal(self.L_TYPE_MISMATCH, f"{bexpr.lineno, bexpr.col_offset} left and right operands are incompatible: "+can_cast)
        
        # Check operation validity with type
        if isinstance(left_expr_type, (ast.ArrayType, ast.FuncType)) or isinstance(right_expr_type, (ast.ArrayType, ast.FuncType)):
            if not isinstance(bexpr.op, (ast.LogicalAnd, ast.LogicalOr, ast.Eq, ast.NotEq)):
                self._fatal(self.L_TYPE_MISMATCH, f"{bexpr.lineno, bexpr.col_offset} array, pointers, and function expressions only support equal, not equal, logical and and logical not for conditional operators.")
        
        # Check for type downgrade
        if not isinstance(left_expr_type, (ast.LogicalAnd, ast.LogicalOr)):
            left_size = right_size = 2
            
            if isinstance(left_expr_type, ast.IntType): left_size = nstypes.CFG.INT_SIZES[left_expr_type.type]
            if isinstance(right_expr_type, ast.IntType): right_size = nstypes.CFG.INT_SIZES[right_expr_type.type]
            
            if left_size < right_size: # Downgrade
                self.logger.warn(f"{bexpr.lineno, bexpr.col_offset} downgrading right side of expression.")
            elif left_size > right_size: # Upgrade
                self.logger.warn(f"{bexpr.lineno, bexpr.col_offset} upgrading right side of expression. default behaviour is unsigned extension.")
            
            # Add conversion if necessary
            if not nsst.CompareTypesEquiv(self.scope, left_expr_type, right_expr_type):
                start = (bexpr.right.lineno, bexpr.right.col_offset)
                end = (bexpr.right.end_lineno, bexpr.right.end_col_offset)
                bexpr.right = ast.CastExpr(
                    expr = bexpr.right,
                    cast_type = left_expr_type,
                    signed = False
                )
                bexpr.right.lineno, bexpr.right.col_offset = start
                bexpr.right.end_lineno, bexpr.right.end_col_offset = end
        
        return bexpr
    
    def visit_TernaryExpr(self, texpr: ast.TernaryExpr) -> ast.AST:
        "Check that both expressions are the same types and that the condition expression is integral, array, pointer, or function."
        if self.typedef_check: return texpr
        
        super().generic_visit(texpr)
        
        cond_expr_type = GetExpressionType(self.scope, texpr.cond_expr)
        true_expr_type = GetExpressionType(self.scope, texpr.true_expr)
        false_expr_type = GetExpressionType(self.scope, texpr.false_expr)
        
        if not isinstance(cond_expr_type, (ast.IntType, ast.ArrayType, ast.FuncType)):
            self._fatal(self.L_TYPE_MISMATCH, f"{texpr.lineno, texpr.col_offset} TernaryExpr expects an integer, array, pointer, or function as conditional expression, got {cond_expr_type.__class__.__name__}")
        
        if not nsst.CompareTypesEquiv(self.scope, true_expr_type, false_expr_type):
            self._fatal(self.L_TYPE_MISMATCH, f"{texpr.lineno, texpr.col_offset} true value and false value of TernaryExpr do not have the same type.")

        return texpr
     
    def visit_AssignExpr(self, aexpr: ast.AssignExpr) -> ast.AST:
        """Check that both sides are the same types and that the optional operator is valid for those types.
        
        Like AddrOfExpr, this method does not check that its left-hand side has a location in memory and this must be left to the code generator."""
        if self.typedef_check: return aexpr
        
        super().generic_visit(aexpr)
        
        lhs_expr_type = GetExpressionType(self.scope, aexpr.lhs)
        rhs_expr_type = GetExpressionType(self.scope, aexpr.rhs)
        
        if not nsst.CompareTypesEquiv(self.scope, lhs_expr_type, rhs_expr_type):
            self._fatal(self.L_TYPE_MISMATCH, f"{aexpr.lineno, aexpr.col_offset} left-hand side and right-hand side of AssignExpr do not have the same type.")
        
        # Check lhs is lvalue
        epchk = ExprPropertyChecker(self.scope)
        props: ExprProperty = epchk.visit(aexpr.lhs)
        if not props.is_lvalue():
            self._fatal(Checker.L_TYPE_MISMATCH, f"{aexpr.lineno, aexpr.col_offset} AssignExpr left-hand side must be an lvalue.")
                
        # Check operator if necessary
        if aexpr.op != None:
            if not isinstance(lhs_expr_type, (ast.IntType, ast.ArrayType, ast.FuncType)):
                self._fatal(self.L_TYPE_MISMATCH, f"{aexpr.lineno, aexpr.col_offset} an AssignExpr can only be augmented with an operator if its operands are integers, arrays, pointers, or function, got {lhs_expr_type.__class__.__name__}")
            
            # Check operation validity with type
            if isinstance(lhs_expr_type, (ast.ArrayType, ast.FuncType)):
                if not isinstance(aexpr.op, (ast.Add, ast.Sub)):
                    self._fatal(self.L_TYPE_MISMATCH, f"{aexpr.lineno, aexpr.col_offset} array, pointers, and function expressions only support addition and subtraction for arithmetic in an augmented AssignExpr.")
        
        return aexpr
    
    def visit_ComplexExpr(self, cexpr: ast.ComplexExpr) -> ast.AST:
        "Check that the ComplexExpr is valid."
        if self.typedef_check: return cexpr
        
        super().generic_visit(cexpr)
        
        # str ComplexExpr are always of the same types and struct ComplexExpr are determined by their inner values
        # so we only check that arrays have the same type across all of its members.
        if cexpr.type != "array": return cexpr
        
        inner_type = GetExpressionType(self.scope, cexpr.value[0])
        for i, expr in enumerate(cexpr.value):
            if not nsst.CompareTypesEquiv(self.scope, inner_type, GetExpressionType(self.scope, expr)):
                self._fatal(Checker.L_TYPE_MISMATCH, f"{expr.lineno, expr.col_offset} element {i} of array expression at {cexpr.lineno, cexpr.col_offset} has mismatched type.")
        
        return cexpr
              
    # Manage circular types
    def visit_VoidType(self, vtype: ast.VoidType) -> ast.AST:
        "If we found an unexpected void type then this is problematic so give an error."
        self._fatal(Checker.L_VOIDTYPE_DISALLOWED, f"{vtype.lineno, vtype.col_offset} unexpected void type.")
    
    def visit_TypeDecl(self, tdecl: ast.TypeDecl) -> ast.AST:
        "Check that type declarations are not circular."
        if not self.typedef_check: return tdecl
        
        self.logger.debug(f"{tdecl.lineno, tdecl.col_offset} entering TypeDecl {tdecl.name}.")
        self.logger.increasepad()
        
        self.typenames.append(tdecl.name)
        self.visit(tdecl.type)
        self.typenames.pop()
        
        self.logger.debug(f"exiting TypeDecl {tdecl.name} at {tdecl.lineno, tdecl.col_offset}-{tdecl.end_lineno, tdecl.end_col_offset}.")
        self.logger.decreasepad()
        return tdecl
    
    def visit_RefType(self, rtype: ast.RefType) -> ast.AST:
        "Add additional checks to check a RefType is not circular."
        if not self.typedef_check: return rtype
        
        oldpos = self.refpos
        if rtype.lineno: self.refpos = (rtype.lineno, self.refpos[1])
        if rtype.col_offset: self.refpos = (self.refpos[0], rtype.col_offset)
        
        ttype = self.scope.get_typesym(rtype.ref_type_name)
        if ttype == None:
            self._fatal(Checker.L_TYPENOTEXIST, f"{self.refpos} RefType {rtype.ref_type_name} does not have an entry in the symbol table.")
        
        ttype._reference()
        
        if len(self.typenames) > 0:
            if rtype.ref_type_name in self.typenames:
                self._fatal(self.L_CIRCTYPEDEF, f"{self.refpos} RefType {rtype.ref_type_name} has circular declaration {'>'.join(self.typenames)}>{rtype.ref_type_name}.")
            
            self.typenames.append(rtype.ref_type_name)
            prev_scope = self.scope
            self.scope = ttype.get_table()
            
            self.visit(ttype.get_type())
            self.scope = prev_scope
            self.typenames.pop()
        
        self.refpos = oldpos
        return rtype
    
    def visit_ArrayType(self, atype: ast.ArrayType) -> ast.AST:
        "Allow for VoidType in an ArrayType"
        typenames = self.typenames
        self.typenames = []
        if atype.size != None or not isinstance(atype.inner_type, ast.VoidType):
            self.visit(atype.inner_type)
        if atype.size != None:
            self.visit(atype.size)
            epchk = ExprPropertyChecker(self.scope)
            props: ExprProperty = epchk.visit(atype.size)
            if not props.is_const():
                self._fatal(Checker.L_TYPE_MISMATCH, f"{atype.lineno, atype.col_offset} ArrayType size must be constant.")
        self.typenames = typenames
        return atype
    
    def visit_FuncType(self, ftype: ast.FuncType) -> ast.AST:
        "Allow for VoidType as the return type of a FuncType"
        typenames = self.typenames
        self.typenames = []
        if not isinstance(ftype.return_type, ast.VoidType):
            self.visit(ftype.return_type)
        for param_type in ftype.param_types:
            self.visit(param_type)
        self.typenames = typenames
        return ftype
    
    def visit_MemberData(self, mdata: ast.MemberData) -> ast.AST:
        if not self.typedef_check: return mdata
        super().generic_visit(mdata)
        if mdata.bits != None and not isinstance(nsst.ExpandType(self.scope, mdata.type), ast.IntType):
            self._fatal(Checker.L_INVALIDBITS, f"{(mdata.lineno, mdata.col_offset)} Member {mdata.name} has bits value {mdata.bits} but is not an integral type.")
        return mdata
    
    # Manage scoping
    def visit_FuncDecl(self, fdecl: ast.FuncDecl) -> ast.AST:
        "Enter the scope of a function declaration"
        
        if fdecl.body == None:
            self.logger.debug(f"skipping empty FuncDecl {fdecl.name}.")
            return fdecl
        
        self.logger.debug(f"entering scope of FuncDecl {fdecl.name}.")
        self.logger.increasepad()
        
        self.ret_type = nsst.ExpandType(self.scope, fdecl.type.return_type)
        self.scope = fdecl.symref.get_created_functable()
        super().generic_visit(fdecl)
        self.scope = self.scope.get_parent()
        self.ret_type = None
        
        self.logger.debug(f"exiting scope of FuncDecl {fdecl.name}.")
        self.logger.decreasepad()
        return fdecl
    
    def visit_CompoundStmt(self, cstmt: ast.CompoundStmt) -> ast.AST:
        "Enter the scope of a compound statement"
        
        self.logger.debug(f"entering scope of CompoundStmt.")
        self.logger.increasepad()
        
        self.scope = cstmt.symref
        
        # Check TypeDecls first
        typedecls: list[ast.Decl]
        
        super().generic_visit(cstmt)
        self.scope = self.scope.get_parent()
        
        self.logger.debug(f"exiting scope of CompoundStmt.")
        self.logger.decreasepad()
        return cstmt