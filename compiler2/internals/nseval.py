from __future__ import annotations
import internals.astnodes as ast
import internals.nssymtab as nssym
import internals.nsstbuilder as nsst
import internals.nschk as nschk
import internals.nslog as nslog
import internals.nstypes as nstypes

"""
Module that evaluates and simplifies expression trees passed to it.
"""

def get_type_size(scope: nssym.SymbolTable, type: ast.Type, eval_array: bool = False):
    if isinstance(type, ast.RefType):
        return get_type_size(scope, nsst.ExpandType(scope, type), eval_array=eval_array)
    
    elif isinstance(type, ast.IntType):
        return nstypes.CFG.INT_SIZES[type.type]
    
    elif isinstance(type, ast.ArrayType):
        if not eval_array or type.size == None:
            return nstypes.CFG.PTR_SIZE
        
        simplifier = ExprSimplifier(scope)
        expr = simplifier.visit(type.size)
        if not isinstance(expr, ast.IntExpr):
            raise Exception(f"nschk failed, ArrayType at {type.lineno, type.col_offset} size expected an IntExpr but got {expr.__class__.__name__}")
        return expr.value * get_type_size(scope, type.inner_type, eval_array=True)
        
    elif isinstance(type, ast.FuncType):
        return nstypes.CFG.PTR_SIZE
    
    elif isinstance(type, ast.StructType):
        # A struct type is the accumulation of all its other types when accounting for integer bits
        full_size = 0 # Full size of the struct
        int_max = 0 # Maximum size in current integer
        int_bits = 0 # Building of bits
        for member in type.members:
            if isinstance(member.type, ast.IntType) and member.bits not in [None, -1]:
                # Get current integer size
                cur_int_max = nstypes.CFG.BITS_PER_WORD * nstypes.CFG.INT_SIZES[member.type.type]
                
                # If the previous member wasn't the same integer size, we reset it.
                if int_max != cur_int_max:
                    full_size += int_max // nstypes.CFG.BITS_PER_WORD
                    int_max = cur_int_max
                    int_bits = 0
                
                # Now we add the wanted bits to int_bits if there is enough space
                if int_bits + member.bits > int_max:
                    full_size += int_max // nstypes.CFG.BITS_PER_WORD
                    int_bits = 0
                int_bits += member.bits
            else:
                int_max = 0
                int_bits = 0
                full_size += get_type_size(scope, member.type, eval_array=eval_array)
        # Clear any left over integers
        if int_bits != 0:
            full_size += int_max // nstypes.CFG.BITS_PER_WORD
            
        return full_size
    
    elif isinstance(type, ast.UnionType):
        # A union type is as big as its largest member.
        return max(map(lambda x: get_type_size(x.type, eval_array=eval_array), type.members))
    
    raise Exception(f"Expected a Type here, got {type.__class__.__name__}")

class ExprSimplifier(ast.NodeTransformer):
    def __init__(self, scope: nssym.SymbolTable):
        self.scope = scope
        
    # TODO: Check and simplify expressions.