from __future__ import annotations
import internals.astnodes as ast
import internals.nssymtab as nssym
import internals.nsstbuilder as nsst
import internals.nslog as nslog
import internals.nseval as nseval
import internals.asmnodes as asm

"""
Module responsible for translating the higher-level AST-tree into asmnodes and then into assembly files.
"""

def to_assembly(gen: 'Generator') -> list[str]:
    lines = []
    for stmt in gen.assembly:
        lines.append(str(stmt))
    
    return lines

class FunctionContext:
    def __init__(self, func: ast.FuncDecl):
        self.func = func
        self.exit_label: str = ""

class Generator(ast.NodeVisitor):
    L_UNKNOWN = 1
    
    def __init__(self):
        self.scope: nssym.SymbolTable = nsst.GetSymbolTable()
        self.logger = nslog.LoggerFactory.getLogger()
        self.success = True
        
        self.assembly: list[asm.Statement] = list()
        self.strings: dict[str, list[int]] = dict()
        
        self.locals_assigned = 0
        self.idmap: dict[int, nssym.SymbolTable] = dict()
        self.namemap: dict[int, str] = dict()
        
        self.current_context: 'FunctionContext' | None = None
    
    def _get_lname(self, prefix="L") -> str:
        while (name := prefix + str(self.locals_assigned)) in self.namemap.values():
            self.locals_assigned += 1
        self.locals_assigned += 1
        return name
    
    def _get_lcname(self) -> str:
        return self._get_lcname(prefix="LC")
    
    def get_children_of_types(self, node: ast.AST, nodeType: any | tuple[any], recursive: bool = False) -> list[ast.AST]:
        "Walks the descendants or direct children of the specified node and returns all nodes with the corresponding type."
        func = ast.walk if recursive else ast.iter_child_nodes
        
        children: list[ast.AST] = []
        
        for node in func(node):
            if isinstance(node, nodeType):
                children.append(node)
        
        return children
    
    def get_variables(self, node: ast.AST, recursive: bool = False) -> list[ast.VarDecl]:
        "Walks the direct children of the specified node and returns all variables corresponding to their VarDecl in the symbol table."
        nodes: list[ast.VarDecl] = self.get_children_of_types(node, ast.VarDecl, recursive=False)
        
        nodes = list(filter(
            lambda x: self.scope.get_namesym(x.name) is x.symref,
            nodes
        ))
        
        return nodes
    
    def get_functions(self, node: ast.AST, recursive: bool = False) -> list[ast.FuncDecl]:
        "Walks the direct children of the specified node and returns all functions corresponding to their FuncDecl in the symbol table."
        nodes: list[ast.FuncDecl] = self.get_children_of_types(node, ast.FuncDecl, recursive=False)
        
        nodes = list(filter(
            lambda x: self.scope.get_namesym(x.name) is x.symref,
            nodes
        ))
        
        return nodes
    
    def get_min_size_on_stack(self, node: ast.AST) -> int:
        "Returns the minimum number of words needed on stack for local variables in the function."
        
        if not isinstance(node, ast.CompoundStmt): return 0
        
        vars: list[ast.VarDecl] = []
        compounds: list[ast.CompoundStmt] = []
        
        for stmt in node.stmts:
            if isinstance(stmt, ast.DefStmt) and isinstance(stmt.decl, ast.VarDecl) and not stmt.decl.is_static:
                vars.append(stmt.decl)
            if isinstance(stmt, ast.CompoundStmt):
                compounds.append(stmt)
            if isinstance(stmt, ast.IfStmt):
                compounds.append(stmt.body)
            if isinstance(stmt, ast.IterStmt):
                compounds.append(stmt.body)
                if stmt.else_body != None: compounds.append(stmt.else_body)        
        
        size = 0
        
        for var in vars:
            size += nseval.get_type_size(self.scope, var.type, eval_array=True)
        
        children_stmts = [0]
        for compound in compounds:
            children_stmts.append(self.get_min_size_on_stack(compound))
        
        return size + max(children_stmts)
    
    def include_file(self, filename: str) -> None:
        "Includes the specified file."
        self.assembly.append(asm.PreprocDirective(f"#include \"{filename}\""))
    
    def visit_FuncDecl(self, node: ast.FuncDecl) -> ast.FuncDecl:
        # Will ignore inline nodes for now cuz im lazy
        # if node.is_inline: return node
        
        old_scope = self.scope
        self.scope = node.body.symref

        # Add a header string
        func_str = f'{node.name}({", ".join(node.param_names)})'
        
        func_header = asm.Space()
        func_header.comment = "FUNC " + func_str
        self.assembly.append(func_header)
        
        # Register the function name and create function context
        name = self.namemap.get(id(self.scope.get_namesym(node.name))) or f"{self._get_lname()}@{node.name}"
        self.namemap[id(self.scope.get_namesym(node.name))] = name
        
        self.current_context = FunctionContext(node)
        self.current_context.exit_label = f"{self._get_lname()}@{node.name}.exit"
        
        variables: list[ast.VarDecl] = self.get_variables(node, recursive = True)
        
        # Create static data
        static_vars = list(filter(lambda x: (x.is_static), variables))
        # TODO
        
        # Add function label
        self.assembly.append(asm.LabelStatement(name))
        
        # Function setup
            # push callee-saved registers.
        push_uv = asm.OpStatement("push")
        push_uv.operands.append(asm.RegisterOperand("V", is32bit=True))
        self.assembly.append(push_uv)
        set_uv = asm.OpStatement("mov")
        set_uv.operands.extend([
            asm.RegisterOperand("V", is32bit=True),
            asm.RegisterOperand("P", is32bit=True)])
        self.assembly.append(set_uv)
        push_eg = asm.OpStatement("push")
        push_eg.operands.append(asm.RegisterOperand("E", is32bit=True))
        self.assembly.append(push_eg)
        del push_uv, set_uv, push_eg
        
            # allocate stack space for local variables
        stack_words = self.get_min_size_on_stack(node.body)
        
        if stack_words > 0:
            stackalloc = asm.OpStatement("add")
            stackalloc.operands.append(asm.RegisterOperand("P"))
            stackalloc.operands.append(asm.ImmOperand(stack_words))
            self.assembly.append(stackalloc)
            del stackalloc
            
        # Code generation
        # Very much TODO
        
        # Create default return
        self.assembly.append(asm.LabelStatement(self.current_context.exit_label))
            # reset stack space
        stackdealloc = asm.OpStatement("mov")
        stackdealloc.operands.append(asm.RegisterOperand("P", is32bit=True))
        stackdealloc.operands.append(asm.RegisterOperand("V", is32bit=True))
        self.assembly.append(stackdealloc)
        del stackdealloc
        
            # pop callee-saved registers.
        pop_eg = asm.OpStatement("pop")
        pop_eg.operands.append(asm.RegisterOperand("E", is32bit=True))
        self.assembly.append(pop_eg)
        pop_uv = asm.OpStatement("pop")
        pop_uv.operands.append(asm.RegisterOperand("V", is32bit=True))
        self.assembly.append(pop_uv)
        
            # add return statement
        self.assembly.append(asm.OpStatement("ret"))
        
        # Add a footer string
        func_footer = asm.Space()
        func_footer.comment = "\tENDFUNC " + func_str
        self.assembly.append(func_footer)
        self.assembly.append(asm.Space())
        
        self.current_context = None
        
        self.scope = old_scope
    
    def visit_Module(self, node: ast.Module) -> ast.Module:
        "Create the data and text sections, populate them."
        self.include_file("std\libns.s")
        self.assembly.append(asm.Space())
        
        variables: list[ast.VarDecl] = self.get_variables(node)
        constants: list[ast.ConstDecl] = self.get_children_of_types(node, ast.ConstDecl)
        functions: list[ast.FuncDecl] = self.get_functions(node)
        
        global_vars = [x for x in variables if not x.is_static and x.value]
        extern_vars = [x for x in variables if not x.is_static and not x.value]
        global_funcs = [x for x in functions if not x.is_static and x.body]
        extern_funcs = [x for x in functions if not x.is_static and not x.body]
        
        if len(global_vars) > 0:
            glbl = asm.Directive(".global")
            for global_var in global_vars:
                label = asm.LabelOperand(global_var.name)
                glbl.operands.append(label)
                self.namemap[id(self.scope.get_namesym(global_var.name))] = global_var.name
            self.assembly.append(glbl)
        
        if len(global_funcs) > 0:
            glbl = asm.Directive(".global")
            for global_func in global_funcs:
                label = asm.LabelOperand(global_func.name)
                glbl.operands.append(label)
                self.namemap[id(self.scope.get_namesym(global_func.name))] = global_func.name
            self.assembly.append(glbl)
        
        if len(extern_vars) > 0:
            extern = asm.Directive(".extern")
            for extern_var in extern_vars:
                label = asm.LabelOperand(extern_var.name)
                extern.operands.append(label)
                self.namemap[id(self.scope.get_namesym(extern_var.name))] = extern_var.name
            self.assembly.append(extern)
        
        if len(extern_funcs) > 0:
            extern = asm.Directive(".extern")
            for extern_func in extern_funcs:
                label = asm.LabelOperand(extern_func.name)
                extern.operands.append(label)
                self.namemap[id(self.scope.get_namesym(extern_func.name))] = extern_func.name
            self.assembly.append(extern)
        
        self.assembly.append(asm.Space())
        
        # generate data
        self.assembly.append(asm.Directive(".data"))
        
        # constants
        for constant in constants:
            self.visit(constant)
        self.assembly.append(asm.Space())
        
        # variables
        for variable in variables:
            if variable in extern_vars: continue
            self.visit(variable)
        self.assembly.append(asm.Space())
        
        # generate code
        self.assembly.append(asm.Directive(".text"))
        for function in functions:
            if function in extern_funcs: continue
            self.visit(function)
            
        if len(self.strings) != 0:
            section_dir = asm.Directive(".section")
            section_dir.operands.extend([
                asm.LabelOperand("strings")
            ])
            self.assembly.append(section_dir)
            
            for name, string in self.strings.items():
                self.assembly.append(asm.LabelStatement(name))
                str_stmt = asm.Directive(".string")
                str_stmt.operands.append(asm.StrOperand(string))
                self.assembly.append(str_stmt)