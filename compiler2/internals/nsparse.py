import internals.astnodes as ast
import internals.nslog as nslog
import internals.nstypes as nstypes
from internals.nslex import Token, TokenType

"""
New Solar language syntax
-------------

module := [global_decl] EOF ;

global_decl := func_decl
             | const_decl
             | decl
             ;

decl := var_decl
      | type_decl
      ;

func_decl := {COMMENT} {"static" | "inline"} "func" NAME '(' param_list ')' '->' '(' type ')' (';' | cmp_stmt) ;
const_decl := {"static"} "set" NAME ':' type ':=' expr ';' {COMMENT} ;
var_decl := {"static"} "let" NAME ':' type {':=' init_expr} ';' {COMMENT} ;
type_decl := "using" NAME ':=' type ';' {COMMENT}
           | "struct" NAME record_def ';' {COMMENT}
           | "union" NAME record_def ';' {COMMENT}
           ;

type := "int" | "long" | "quad" | "void"
      | "volatile" type
      | '*' type
      | '[' (s_expr) ']' type
      | "func" '(' type_list ')' '->' '(' type ')'
      | "struct" record_def
      | "union" record_def
      | NAME
      ;

record_def := '{' member_decl {COMMENT} [',' member_decl {COMMENT}] {','}'}' ;
member_decl := NAME ':' type {':' INT} ;

stmt := ';'
      | '{' [stmt] '}'
      | "continue" {NAME} ';'
      | "break" {NAME} ';'
      | "breakif" {NAME} ';'
      | "return" {expr} ';'
      | {NAME ':'} "if" '(' expr ')' stmt {"else" stmt}
      | {NAME ':'} "while" '(' expr ')' stmt {"else" stmt}
      | {NAME ':'} "for" '(' {expr} ';' {expr} ';' {expr} ')' stmt {"else" stmt}
      | decl
      | expr ';'
      ;

init_expr := STR
           | '{' init_expr_list '}'
           | struct '{' n_init_expr_list '}'
           | a_expr
           ;

-- Review lang_info.md for precedence and associativity
expr := a_expr_list ; -- Comma expression
a_expr := expr assign_op expr
        | s_expr
        ;
        
s_expr := expr '?' expr ':' expr
         | expr bin_op expr
         | expr bcond_op expr
         | un_op expr
         | ucond_op expr
         | '&' expr
         | '*' expr
         | expr "as" {'$'} type
         | expr '->' NAME
         | expr '.' NAME
         | expr '[' expr ']'
         | expr '(' a_expr_list ')'
         | atom
         ;

atom := "szexpr" '(' expr ')'
      | "sztype" '(' type ')'
      | '(' expr ')'
      | STR | INT | NAME
      
-- Lists

param_list := NAME ':' type [',' NAME ':' type] {',' '...'} ;
type_list := type [',' type] {',' '...'} ;
a_expr_list := a_expr [',' a_expr] ;
init_expr_list := init_expr [',' init_expr ] ;
n_init_expr_list := NAME ':' init_expr [',' NAME ':' init_expr] ;
"""
class Parser:
    L_UNKNOWN = 1
    L_EATWRONGTYPE = 2
    L_EATWRONGVALUE = 3
    L_FAILEDCHECK = 4
    L_WRONGTOKEN = 5
    L_MISSINGVALUE = 10
    L_EMPTYRECORDDEF = 11
    L_INVALID_MODIFIER = 20
    L_INVALID_OPERATOR = 30
    L_EMPTY_COMPLEX = 40
    L_COMPLEX_REPEAT_KEY = 41
    L_EOF = 99
    
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0
        self.logger = nslog.LoggerFactory.getLogger()
        self.success = True
        
    def _snapshot(self) -> tuple[int, int]:
        "Returns the starting position of the current token."
        return self._peek().start_pos
    
    def _error(self, code: int, error: str):
        "Throw an error and mark parse as unsuccessful but continue parsing."
        self.logger.error(f"{{P{code:02}}} {error}")
        self.success = False
    
    def _fatal(self, code: int, error: str):
        "Throw a fatal error which marks parse as unsuccessful and aborts."
        self.logger.fatal(f"{{P{code:02}}} {error}")
        self.success = False
        raise Exception("nsparse encountered a fatal error.")
    
    def _peek(self, ahead=0, skip_comment = True) -> Token | None:
        """
        Peeks a token starting `ahead` tokens off from the current position. `ahead` can be negative to look behind.
        
        Comments will be ignored if `skip_comment` is True, which is the default
        
        Will return EOF token if start of file or EOF is met.
        """
        if ahead < 0:
            tokens = self.tokens[:self.pos]
        else:
            tokens = self.tokens[self.pos:]
        if skip_comment:
            tokens = list(filter(lambda token: not token.iscomment(), tokens))
        token = tokens[ahead:]
        if len(token) < 1:
            return Token(
                TokenType.EOF,
                None,
                self.tokens[0 if self.pos+ahead<0 else -1].start_pos,
                self.tokens[0 if self.pos+ahead<0 else -1].start_pos
            )
        return token[0]
    
    def _eat(self, token_type: TokenType | None = None, token_value: any = None, skip_comment = True) -> Token:
        """
        Eats the current token if it matches the specified criteria and updates position.
        
        Comments will be ignored if `skip_comment` is True, which is the default.
        
        Returns the read token.
        """
        cur = self._peek(skip_comment = skip_comment)
        pos = cur.start_pos
        if token_type and not cur.istype(token_type):
            self._fatal(Parser.L_EATWRONGTYPE, f"{pos}: expected type '{token_type.name}', got '{cur.type.name}'")
        if token_value and cur.value != token_value:
            self._fatal(Parser.L_EATWRONGVALUE, f"{pos}: expected value '{token_value}', got '{cur.value}'")
        while self._peek(skip_comment=False) != cur: # Skip over passed comments
            self.pos += 1
        self.pos += 1
        return cur
    
    def parse_module(self) -> ast.Module:
        "Parses an entire module (program file)."
        start_loc = end_loc = self._snapshot()
        decls = []
        while self._peek(skip_comment=False).iscomment():
            self._eat(skip_comment=False)
        while not self._peek().iseof():
            decls.append(self.parse_global_decl())
            end_loc = decls[-1].end_lineno, decls[-1].end_col_offset
        
        modl = ast.Module(decls=decls)
        modl.lineno, modl.col_offset = start_loc
        modl.end_lineno, modl.end_col_offset = end_loc
        return modl
    
    # DECLARATION PARSING #
    def can_parse_global_decl(self) -> bool:
        "Returns true if the next few tokens allow for parsing a global declaration"
        if self.can_parse_func_decl(): return True
        if self.can_parse_const_decl(): return True
        return self.can_parse_decl()
    
    def parse_global_decl(self) -> ast.Decl:
        "Parses a top-level declaration."
        if self.can_parse_func_decl(): return self.parse_func_decl()
        if self.can_parse_const_decl(): return self.parse_const_decl()
        if self.can_parse_decl(): return self.parse_decl()
        self._fatal(Parser.L_FAILEDCHECK, f"{self._snapshot()}: expected global declaration but could not match pattern.")
            
    def can_parse_decl(self) -> bool:
        "Returns true if the next few tokens allow for parsing a normal declaration"
        if self.can_parse_var_decl(): return True
        return self.can_parse_type_decl()
    
    def parse_decl(self) -> ast.Decl:
        "Parses a normal declaration."
        if self.can_parse_var_decl(): return self.parse_var_decl()
        if self.can_parse_type_decl(): return self.parse_type_decl()
        self._fatal(Parser.L_FAILEDCHECK, f"{self._snapshot()}: expected declaration but could not match pattern.")
    
    def can_parse_func_decl(self) -> bool:
        "Returns true if the next few tokens allow for parsing a function declaration"
        token = self._peek()
        if token.iskeyword(("static", "inline")): token = self._peek(1)
        return token.iskeyword("func")
    
    def parse_func_decl(self) -> ast.FuncDecl:
        "Parses a function declaration."
        
        start_pos = self._snapshot()
        self.logger.debug(f"{start_pos} began parsing FuncDecl node.")
        self.logger.increasepad()
        
        # Get comment
        comment = None
        if (c := self._peek(-1, skip_comment=False)).iscomment():
            comment = c.value
        
        # Get function modifiers
        is_static = self._peek().iskeyword(("static", "inline"))
        is_inline = self._peek().iskeyword("inline")
        if is_static: self._eat()
        
        # Get function name
        self._eat(TokenType.KEYWORD, "func")
        name: str = self._eat(TokenType.NAME).value
        
        # Get parameters
        param_names: list[str] = []
        param_types: list[ast.Type] = []
        is_variadic = False
        self._eat(TokenType.PUNC, "(")
        if not self._peek().ispunc(")"):
            param_names, param_types, is_variadic = self.parse_param_list()
        self._eat(TokenType.PUNC, ")")
        
        # Get return type
        self._eat(TokenType.PUNC, "->")
        self._eat(TokenType.PUNC, "(")
        ret_type = self.parse_type()
        self._eat(TokenType.PUNC, ")")
        
        # Get signature
        signature = ast.FuncType(is_volatile=False, return_type=ret_type, param_types=param_types, is_variadic=is_variadic)
        
        # Get body and comment
        if self._peek().ispunc(";"): # No body, header only
            self._eat()
            body = None
        elif self._peek().ispunc("{"): # Has body
            body = self.parse_stmt()
        else:
            self._fatal(Parser.L_WRONGTOKEN, f"{self._snapshot()}: expected ';' or function body, but got token type '{self._peek().type.name}('{self._peek().value}')' in function declaration at {start_pos}.")
        end_pos = self._peek(-1).end_pos

        # Create FuncDecl node
        self.logger.debug(f"created FuncDecl '{name}' node at {start_pos}-{end_pos}.")
        self.logger.decreasepad()
        node = ast.FuncDecl(name=name, type=signature, description=comment, param_names=param_names, body=body, is_static=is_static, is_inline=is_inline)
        node.lineno, node.col_offset = start_pos[0], start_pos[1]
        node.end_lineno, node.end_col_offset = end_pos[0], end_pos[1]
        
        return node
    
    def can_parse_const_decl(self) -> bool:
        "Returns true if the next few tokens allow for parsing a constant declaration"
        token = self._peek()
        if token.iskeyword("static"): token = self._peek(1)
        return token.iskeyword("set")
    
    def parse_const_decl(self) -> ast.ConstDecl:
        "Parses a constant declaration."
        
        start_pos = self._snapshot()
        self.logger.debug(f"{start_pos} began parsing ConstDecl node.")
        self.logger.increasepad()
        
        # Get const modifiers
        is_static = self._peek().iskeyword("static")
        if is_static: self._eat()
        
        # Get constant name and type
        self._eat(TokenType.KEYWORD, "set")
        name: str = self._eat(TokenType.NAME).value
        self._eat(TokenType.PUNC, ":")
        type = self.parse_type()
        
        # Get value
        if not self._peek().ispunc(":="):
            self._fatal(Parser.L_MISSINGVALUE, f"{self._snapshot()} expected defined value for constant declaration at {start_pos}, got token '{self._peek().type.name}('{self._peek().value}')'")
        self._eat(TokenType.PUNC, ":=")
        value = self.parse_expr()
        self._eat(TokenType.PUNC, ";")
        
        # Get comment
        comment = None
        if (c := self._peek(skip_comment=False)).iscomment():
            comment = c.value
            self._eat(skip_comment=False)
            
        end_pos = self._peek(-1).end_pos
        
        # Create ConstDecl node
        self.logger.debug(f"created ConstDecl '{name}' node at {start_pos}-{end_pos}.")
        self.logger.decreasepad()
        node = ast.ConstDecl(name=name, type=type, description=comment, value=value, is_static=is_static)
        node.lineno, node.col_offset = start_pos[0], start_pos[1]
        node.end_lineno, node.end_col_offset = end_pos[0], end_pos[1]
        
        return node
        
    def can_parse_var_decl(self) -> bool:
        "Returns true if the next few tokens allow for parsing a variable declaration"
        token = self._peek()
        if token.iskeyword("static"): token = self._peek(1)
        return token.iskeyword("let")
    
    def parse_var_decl(self) -> ast.VarDecl:
        "Parses a variable declaration."
        
        start_pos = self._snapshot()
        self.logger.debug(f"{start_pos} began parsing VarDecl node.")
        self.logger.increasepad()
        
        # Get var modifiers
        is_static = self._peek().iskeyword("static")
        if is_static: self._eat()
        
        # Get constant name and type
        self._eat(TokenType.KEYWORD, "let")
        name: str = self._eat(TokenType.NAME).value
        self._eat(TokenType.PUNC, ":")
        type = self.parse_type()
        
        # Get value if there is any
        value = None
        if self._peek().ispunc(":="):
            self._eat(TokenType.PUNC, ":=")
            value = self.parse_init_expr()
        self._eat(TokenType.PUNC, ";")
        
        # Get comment
        comment = None
        if (c := self._peek(skip_comment=False)).iscomment():
            comment = c.value
            self._eat(skip_comment=False)
            
        end_pos = self._peek(-1).end_pos
        
        # Create VarDecl node
        self.logger.debug(f"created VarDecl '{name}' node at {start_pos}-{end_pos}.")
        self.logger.decreasepad()
        node = ast.VarDecl(name=name, type=type, description=comment, value=value, is_static=is_static)
        node.lineno, node.col_offset = start_pos[0], start_pos[1]
        node.end_lineno, node.end_col_offset = end_pos[0], end_pos[1]
        
        return node
        
    def can_parse_type_decl(self) -> bool:
        "Returns true if the next few tokens allow for parsing a type declaration"
        return self._peek().iskeyword(("using", "struct", "union"))
    
    def parse_type_decl(self) -> ast.TypeDecl:
        "Parses a type reference declaration."
        
        start_pos = self._snapshot()
        self.logger.debug(f"{start_pos} began parsing TypeDecl node")
        self.logger.increasepad()
        
        # Figure out which type of type declaration it is
        keyword = self._eat(TokenType.KEYWORD)
        if   keyword.iskeyword("using"):
            self.logger.debug(f"TypeDecl is with 'using'.")
            name = self._eat(TokenType.NAME).value
            self._eat(TokenType.PUNC, ":=")
            type = self.parse_type()
        elif keyword.iskeyword(("struct", "union")):
            self.logger.debug(f"TypeDecl is with '{keyword.value}'.")
            name = self._eat(TokenType.NAME).value
            members = self._parse_record_def()
            if keyword.iskeyword("struct"):
                type = ast.StructType(is_volatile=False, members=members)
            else:
                type = ast.UnionType(is_volatile=False, members=members)
        else:
            self._fatal(Parser.L_WRONGTOKEN, f"{start_pos} expected keywords 'using', 'struct', or 'union' in type declaration, got '{self._peek().type.name}('{self._peek().value}')'")
        
        self._eat(TokenType.PUNC, ";")
        
        # Get comment
        comment = None
        if (c := self._peek(skip_comment=False)).iscomment():
            comment = c.value
            self._eat(skip_comment=False)
            
        end_pos = self._peek(-1).end_pos
        
        # Create TypeDecl node
        self.logger.debug(f"created TypeDecl '{name}' node at {start_pos}-{end_pos}.")
        self.logger.decreasepad()
        node = ast.TypeDecl(name=name, type=type, description=comment)
        node.lineno, node.col_offset = start_pos[0], start_pos[1]
        node.end_lineno, node.end_col_offset = end_pos[0], end_pos[1]
        
        return node
    
    # TYPE PARSING #
    def can_parse_type(self) -> bool:
        "Returns true if the next few tokens allow for parsing a type"
        token = self._peek()
        if token.iskeyword(("void", "int", "long", "quad", "func", "struct", "union")): return True
        if token.ispunc(('*', '[')): return True
        if token.isname(): return True
        if token.iskeyword("volatile") and not self._peek().iskeyword("volatile"): return True
        return False
    
    def parse_type(self) -> ast.Type:
        "Parses a type."
        
        start_pos = self._snapshot()
        self.logger.debug(f"{start_pos} began parsing Type node")
        self.logger.increasepad()
        
        # Check for modifiers
        is_volatile = self._peek().iskeyword("volatile")
        if is_volatile: self._eat()
        
        # Figure out the type of Type
        if not self.can_parse_type():
            self._fatal(Parser.L_WRONGTOKEN, f"{start_pos} expected type literal but could not match pattern")
        token = self._eat()
        if   token.iskeyword("void"): # VoidType
            self.logger.debug("found VoidType")
            if is_volatile:
                self._error(Parser.L_INVALID_MODIFIER, f"{start_pos}: type 'void' cannot take the 'volatile' modifier.")
            node = ast.VoidType(False)
        elif token.iskeyword(("int", "long", "quad")): # IntType
            self.logger.debug(f"found IntType of size '{token.value}'")
            node = ast.IntType(is_volatile=is_volatile, type=token.value)
        elif token.iskeyword("func"): # FuncType
            self.logger.debug("found FuncType")
            # Parse function parameter types
            self._eat(TokenType.PUNC, "(")
            param_types: list[ast.Type] = []
            is_variadic = False
            if not self._peek().ispunc(")"):
                param_types, is_variadic = self.parse_type_list()
            self._eat(TokenType.PUNC, ")")
            
            # Parse function return type
            self._eat(TokenType.PUNC, "->")
            self._eat(TokenType.PUNC, "(")
            ret_type = self.parse_type()
            self._eat(TokenType.PUNC, ")")
            
            node = ast.FuncType(is_volatile=is_volatile, return_type=ret_type, param_types=param_types, is_variadic=is_variadic)
            del param_types, is_variadic, ret_type
        elif token.iskeyword(("struct", "union")): # StructType, UnionType
            self.logger.debug(f"found record type of category '{token.value}'")
            members = self._parse_record_def()
            if token.iskeyword("struct"):
                node = ast.StructType(is_volatile=is_volatile, members=members)
            else:
                node = ast.UnionType(is_volatile=is_volatile, members=members)
            del members
        elif token.ispunc("*"):
            self.logger.debug("found ArrayType of category 'pointer'")
            inner_type = self.parse_type()
            node = ast.ArrayType(is_volatile=is_volatile, inner_type=inner_type, size=None)
            del inner_type
        elif token.ispunc("["):
            self.logger.debug("found ArrayType of category 'array'")
            if self._peek().ispunc("]"):
                self.logger.debug("array has no specified size. it will be interpreted as 'pointer'")
                size = None
            elif self.can_parse_s_expr():
                size = self.parse_s_expr()
            else:
                self._fatal(Parser.L_WRONGTOKEN, f"{self._snapshot()} expected an expression but got unexpected token '{self._peek().type.name}('{self._peek().value}')'")
            self._eat(TokenType.PUNC, "]")
            inner_type = self.parse_type()
            node = ast.ArrayType(is_volatile=is_volatile, inner_type=inner_type, size=size)
            del size, inner_type
        elif token.isname():
            self.logger.debug("found a Name. it will be interpreted as RefType")
            node = ast.RefType(is_volatile=is_volatile, ref_type_name=token.value)
        else:
            self._fatal(Parser.L_WRONGTOKEN, f"{self._snapshot()} expected a type but got unexpected token '{self._peek().type.name}('{self._peek().value}'")
        end_pos = self._peek(-1).end_pos
        
        # Create Type node
        self.logger.debug(f"created Type node of type '{node.__class__.__name__}' at {start_pos}-{end_pos}.")
        self.logger.decreasepad()
        node.lineno, node.col_offset = start_pos[0], start_pos[1]
        node.end_lineno, node.end_col_offset = end_pos[0], end_pos[1]
        
        return node
    
    def _parse_record_def(self) -> list[ast.MemberData]:
        "Parses the members of a record type."
        start_pos = self._snapshot()
        self.logger.debug(f"{start_pos} began parsing record member definitions.")
        self.logger.increasepad()
        
        # Get members
        members: list[ast.MemberData] = []
        self._eat(TokenType.PUNC, "{")
        while not self._peek().ispunc("}"):
            members.append(self._parse_member_decl())
            if not self._peek().ispunc(","): break
            self._eat(TokenType.PUNC, ",")
        self._eat(TokenType.PUNC, "}")
            
        # Reject empty records
        if len(members) < 1:
            self._error(Parser.L_EMPTYRECORDDEF, f"{start_pos} record type cannot have no members.")
        
        self.logger.debug(f"{self._peek(-1).end_pos} finished parsing record member definitions.")
        self.logger.decreasepad()
        
        return members
    
    def _parse_member_decl(self) -> ast.MemberData:
        "Parses a member declaration of a record type."
        
        start_pos = self._snapshot()
        self.logger.debug(f"{start_pos} began parsing MemberData node.")
        self.logger.increasepad()
        
        # Fetch name and type
        name = self._eat(TokenType.NAME).value
        self._eat(TokenType.PUNC, ":")
        type = self.parse_type()
        
        # Fetch bits if available
        bits = None
        if self._peek().ispunc(":"):
            self._eat()
            bits = self._eat(TokenType.INTEGER).value[0]
        
        end_pos = self._peek(-1).end_pos
        
        # Create MemberData node
        self.logger.debug(f"created MemberData '{name}' node at {start_pos}-{end_pos}.")
        self.logger.decreasepad()
        node = ast.MemberData(name=name, type=type, bits=bits)
        node.lineno, node.col_offset = start_pos[0], start_pos[1]
        node.end_lineno, node.end_col_offset = end_pos[0], end_pos[1]
        
        return node
        
    # STATEMENT PARSING #
    def can_parse_stmt(self) -> bool:
        "Returns true if the next few tokens allow for parsing a statement"
        token = self._peek()
        if token.iskeyword(("continue", "break", "breakif", "return", "if", "while", "for")): return True
        if token.ispunc((";", "{")): return True
        if token.isname() and self._peek(1).ispunc(":"): return True
        if self.can_parse_decl(): return True
        if self.can_parse_expr(): return True
        return False
    
    def parse_stmt(self) -> ast.Stmt:
        "Parses a statement."
        
        start_pos = self._snapshot()
        self.logger.debug(f"{start_pos} began parsing Stmt node")
        self.logger.increasepad()
        
        # Figure out the type of Stmt
        if not self.can_parse_stmt():
            self._fatal(Parser.L_WRONGTOKEN, f"{start_pos} expected statement but could not match pattern")
        token = self._peek()
        if   token.ispunc(";"):
            self.logger.debug("found EmptyStmt")
            self._eat()
            node = ast.EmptyStmt()
        elif token.ispunc("{"):
            self.logger.debug("found CompoundStmt")
            self.logger.increasepad()
            self._eat()
            stmts: list[ast.Stmt] = []
            while not self._peek().ispunc("}"):
                stmts.append(self.parse_stmt())
                token = self._peek()
            self._eat(TokenType.PUNC, "}")
            node = ast.CompoundStmt(stmts=stmts)
            self.logger.decreasepad()
            del stmts
        elif token.iskeyword("continue"):
            self.logger.debug("found ContinueStmt")
            self._eat()
            if self._peek().isname():
                label = self._eat().value
            else:
                label = None
            self._eat(TokenType.PUNC, ";")
            node = ast.ContinueStmt(label=label)
            del label
        elif token.iskeyword(("break", "breakif")):
            self.logger.debug("found BreakStmt")
            self._eat()
            breakif = token.iskeyword("breakif")
            if self._peek().isname():
                label = self._eat().value
            else:
                label = None
            self._eat(TokenType.PUNC, ";")
            node = ast.BreakStmt(breakif=breakif, label=label)
            del breakif, label
        elif token.iskeyword("return"):
            self.logger.debug("found ReturnStmt")
            self._eat()
            if self.can_parse_expr():
                ret_expr = self.parse_expr()
            else:
                ret_expr = None
            self._eat(TokenType.PUNC, ";")
            node = ast.ReturnStmt(ret_expr=ret_expr)
            del ret_expr
        elif token.iskeyword(("if", "while", "for")) or (token.isname() and self._peek(1).ispunc(":")):
            self._eat()
            # Try parsing label
            if token.iskeyword():
                label = None
            else:
                label = token.value
                self._eat(TokenType.PUNC, ":")
                token = self._eat()
            
            # Figure out the type of control statement
            if   token.iskeyword("if"):
                self.logger.debug("found IfStmt")
                self.logger.increasepad()
                
                # Parse condition
                self._eat(TokenType.PUNC, "(")
                cond_expr = self.parse_expr()
                self._eat(TokenType.PUNC, ")")
                
                # Parse body
                body = self.parse_stmt()
                node = ast.IfStmt(cond_expr=cond_expr, body=body, else_body=None, label=label)
                del cond_expr, body
            elif token.iskeyword("while"):
                self.logger.debug("found IterStmt (while)")
                self.logger.increasepad()
                
                # Parse condition
                self._eat(TokenType.PUNC, "(")
                cond_expr = self.parse_expr()
                self._eat(TokenType.PUNC, ")")
                
                # Parse body
                body = self.parse_stmt()
                node = ast.IterStmt(init_expr=None, cond_expr=cond_expr, inc_expr=None, body=body, else_body=None, label=label)
                del cond_expr, body
            elif token.iskeyword("for"):
                self.logger.debug("found IterStmt (for)")
                self.logger.increasepad()
                
                init_expr = None
                cond_expr = ast.IntExpr("int", 1)
                inc_expr = None
                
                # Parse condition
                self._eat(TokenType.PUNC, "(")
                if not self._peek().ispunc(";"): init_expr = self.parse_expr()
                self._eat(TokenType.PUNC, ";")
                if not self._peek().ispunc(";"): cond_expr = self.parse_expr()
                else:
                    pos = self._snapshot()
                    cond_expr.lineno = cond_expr.end_lineno = pos[0]
                    cond_expr.col_offset = cond_expr.end_col_offset = pos[1]
                self._eat(TokenType.PUNC, ";")
                if not self._peek().ispunc(")"): inc_expr = self.parse_expr()
                self._eat(TokenType.PUNC, ")")
                
                # Parse body
                body = self.parse_stmt()
                node = ast.IterStmt(init_expr=init_expr, cond_expr=cond_expr, inc_expr=inc_expr, body=body, else_body=None, label=label)
                del init_expr, cond_expr, inc_expr, body
            else:
                self._fatal(Parser.L_WRONGTOKEN, f"{token.start_pos} expected 'if', 'while', or 'for' but got token '{token.type.name}('{token.value}')'")
            
            # Check for an else_body
            if self._peek().iskeyword("else"):
                self._eat()
                node.else_body = self.parse_stmt()
            del label
            self.logger.decreasepad()
        elif self.can_parse_decl():
            self.logger.debug("found DefStmt")
            decl = self.parse_decl()
            node = ast.DefStmt(decl=decl)
            del decl
        elif self.can_parse_expr():
            self.logger.debug("found ExprStmt")
            expr = self.parse_expr()
            node = ast.ExprStmt(expr=expr)
            self._eat(TokenType.PUNC, ";")
            del expr
            
        end_pos = self._peek(-1).end_pos
        
        # Create Type node
        self.logger.debug(f"created Stmt node of type '{node.__class__.__name__}' at {start_pos}-{end_pos}.")
        self.logger.decreasepad()
        node.lineno, node.col_offset = start_pos[0], start_pos[1]
        node.end_lineno, node.end_col_offset = end_pos[0], end_pos[1]
        
        return node
            
    
    # EXPRESSION PARSING #
    def can_parse_init_expr(self) -> bool:
        "Returns true if the next few tokens allow for parsing a init expression"
        token = self._peek()
        if token.isstring(): return True
        if token.ispunc("{"): return True
        if token.iskeyword("struct"): return True
        if self.can_parse_a_expr(): return True
        return False
    
    def parse_init_expr(self) -> ast.ComplexExpr | ast.Expr:
        "Parses an init expression."
        
        start_pos = self._snapshot()
        self.logger.debug(f"{start_pos} began parsing ComplexExpr")
        self.logger.increasepad()
        
        if self._peek().isstring():
            self.logger.debug("found string")
            node = ast.ComplexExpr("str", self._peek().value)
            self._eat()
        elif self._peek().ispunc("{"):
            self.logger.debug("found array")
            self.logger.increasepad()
            self._eat()
            if self._peek().ispunc("}"):
                self._fatal(Parser.L_EMPTY_COMPLEX, f"{start_pos} ComplexExpr cannot have no elements")
            else:
                init_exprs = self.parse_init_expr_list()
            self._eat(TokenType.PUNC, "}")
            node = ast.ComplexExpr("array", init_exprs)
            del init_exprs
            self.logger.decreasepad()
        elif self._peek().iskeyword("struct"):
            self.logger.debug("found struct")
            self.logger.increasepad()
            self._eat()
            self._eat(TokenType.PUNC, "{")
            if self._peek().ispunc("}"):
                self._fatal(Parser.L_EMPTY_COMPLEX, f"{start_pos} ComplexExpr cannot have no elements")
            else:
                init_exprs_dict = self.parse_n_init_expr_list()
            self._eat(TokenType.PUNC, "}")
            node = ast.ComplexExpr("struct", init_exprs_dict)
            del init_exprs_dict
            self.logger.decreasepad()
        elif self.can_parse_a_expr():
            node = self.parse_a_expr()
        else:
            self._fatal(Parser.L_WRONGTOKEN, f"{start_pos} expected statement but could not match pattern")
        
        end_pos = self._peek(-1).end_pos
        
        # Create Expr node
        self.logger.debug(f"created Expr node of type '{node.__class__.__name__}' at {start_pos}-{end_pos}.")
        self.logger.decreasepad()
        node.lineno, node.col_offset = start_pos[0], start_pos[1]
        node.end_lineno, node.end_col_offset = end_pos[0], end_pos[1]
        
        return node        
    
    def can_parse_expr(self) -> bool:
        "Returns true if the next few tokens allow for parsing an expression of any precedence"
        return self.can_parse_a_expr()
        
    def parse_expr(self) -> ast.Expr:
        "Parses any type of expression of any precedence."
        
        start_pos = self._snapshot()
        self.logger.debug(f"{start_pos} began parsing CommaExpr")
        self.logger.increasepad()
        
        exprs = self.parse_a_expr_list()
        if len(exprs) == 1:
            self.logger.debug(f"found {exprs[0].__class__.__name__} instead of CommaExpr")
            self.logger.decreasepad()
            return exprs[0]
        
        end_pos = (exprs[-1].lineno, exprs[-1].col_offset)
        
        # Create Expr node
        self.logger.debug(f"created CommaExpr node of type  at {start_pos}-{end_pos}.")
        self.logger.decreasepad()
        node = ast.CommaExpr(exprs)
        node.lineno, node.col_offset = start_pos[0], start_pos[1]
        node.end_lineno, node.end_col_offset = end_pos[0], end_pos[1]
        
        return node
    
    def can_parse_a_expr(self) -> bool:
        "Returns true if the next few tokens allow for parsing an expression of assignment precedence or higher"
        return self.can_parse_s_expr()
    
    def parse_a_expr(self) -> ast.Expr:
        "Parses an expression of assignment precedence or higher (comma expr must be in parentheses)."
        return self.__parse_expr_inner(1)
    
    def can_parse_s_expr(self) -> bool:
        "Returns true if the next few tokens allow for parsing an expression of ternary precedence or higher"
        token = self._peek()
        if self.can_parse_atom(): return True
        if token.ispunc():
            if is_op_unary(token.value): return True
            if is_op_ucond(token.value): return True
            if token.ispunc(("*", "&")): return True
        return False
        
    def parse_s_expr(self) -> ast.Expr:
        "Parses an expression of ternary precedence or higher (comma or assignment expr must be in parentheses)."
        return self.__parse_expr_inner(3)
    
    def can_parse_atom(self) -> bool:
        "Returns true if the next few tokens allow for parsing an expression atom"
        token = self._peek()
        if token.iskeyword(("szexpr", "sztype")): return True
        if token.ispunc("("): return True
        if token.isstring(): return True
        if token.isint(): return True
        if token.isname(): return True
        return False
    
    def parse_atom(self) -> ast.Expr:
        "Parses an atomic expression."
        
        start_pos = self._snapshot()
        self.logger.debug(f"{start_pos} began parsing expression atom")
        self.logger.increasepad()
        
        # Figure out the type of Stmt
        if not self.can_parse_atom():
            self._fatal(Parser.L_WRONGTOKEN, f"{start_pos} expected statement but could not match pattern")
        token = self._peek()
        if token.iskeyword("szexpr"):
            self.logger.debug("found szexpr()")
            self._eat()
            self._eat(TokenType.PUNC, "(")
            expr = self.__parse_expr_inner(0)
            self._eat(TokenType.PUNC, ")")
            node = ast.SzexprExpr(expr=expr)
        elif token.iskeyword("sztype"):
            self.logger.debug("found sztype()")
            self._eat()
            self._eat(TokenType.PUNC, "(")
            type = self.parse_type()
            self._eat(TokenType.PUNC, ")")
            node = ast.SztypeExpr(type=type)
        elif token.ispunc("("):
            self.logger.debug("found parenthesis atom")
            self._eat()
            expr = self.__parse_expr_inner(0)
            self._eat(TokenType.PUNC, ")")
            node = expr
        elif token.isstring():
            self.logger.debug("found string literal")
            node = ast.StrExpr(utf8=self._eat().value)
        elif token.isint():
            self.logger.debug("found integer literal")
            value, type = self._eat().value
            node = ast.IntExpr(type=type, value=value)
        elif token.isname():
            self.logger.debug("found name")
            node = ast.NameExpr(name=self._eat().value)
        
        end_pos = self._peek(-1).end_pos
        
        # Set location data of node
        self.logger.debug(f"created atom expression node of type '{node.__class__.__name__}' at {start_pos}-{end_pos}.")
        self.logger.decreasepad()
        node.lineno, node.col_offset = start_pos[0], start_pos[1]
        node.end_lineno, node.end_col_offset = end_pos[0], end_pos[1]
        
        return node  
        
    def __parse_expr_inner(self, min_prec) -> ast.Expr:
        "Inner function that actually does the parsing"
        
        start_pos = self._snapshot()
        self.logger.debug(f"{start_pos} began parsing expression of prec {min_prec}")
        self.logger.increasepad()
        
        lhs: ast.Expr = None
        
        if self.__get_prefix_prec(self._peek().value) != None:
            lhs = self.__read_prefix_expr()
        else:
            lhs = self.parse_atom()
            
        while True:
            if (postfix_prec := self.__get_postfix_prec(self._peek().value)) != None:
                if postfix_prec < min_prec: break
                lhs = self.__read_postfix_expr(lhs)
                continue
            
            l_prec, r_prec = self.__get_infix_prec(self._peek().value)
            if l_prec == None or r_prec == None:
                break
            
            if l_prec < min_prec:
                break
            
            lhs = self.__read_infix_expr(lhs)
                
        self.logger.debug(f"created expression node of type '{lhs.__class__.__name__}'.")
        self.logger.decreasepad()
        
        return lhs
    
    def __read_prefix_expr(self) -> ast.Expr:
        "Inner function that returns a node with the current prefix operator and expression"
        
        op = self._eat(TokenType.PUNC)
        prefix_prec = self.__get_prefix_prec(op.value)
        self.logger.debug(f"{op.start_pos} began parsing prefix expression with '{op.value}'")
        self.logger.increasepad()
        if prefix_prec == None:
            self._fatal(f"{op.start_pos} expected prefix operator, got another punctuator.")
        
        # Figure which prefix operator it is
        opstr = op.value
        opnode = None
        rhs = self.__parse_expr_inner(prefix_prec)
        if opstr == "&":
            self.logger.debug(f"found AddrOfExpr")
            node = ast.AddrOfExpr(expr=rhs)
        elif opstr == "*":
            self.logger.debug(f"found DerefOfExpr")
            node = ast.DerefExpr(pointer_expr=rhs)
        elif (unarycls := is_op_unary(opstr)) != None:
            self.logger.debug(f"found UnaryOp")
            opnode = unarycls()
            node= ast.UnaryExpr(op=opnode, expr=rhs)
        elif (ucondcls := is_op_ucond(opstr)) != None:
            self.logger.debug(f"found UnaryCOp")
            opnode = ucondcls()
            node= ast.UnaryCondExpr(op=opnode, expr=rhs)
        
        # Set location data
        self.logger.debug(f"created Expr node of type '{node.__class__.__name__}'.")
        self.logger.decreasepad()
        if opnode != None:
            opnode.lineno, opnode.col_offset = op.start_pos
            opnode.end_lineno, opnode.end_col_offset = op.end_pos
        node.lineno, node.col_offset = op.start_pos
        node.end_lineno, node.end_col_offset = rhs.end_lineno, rhs.end_col_offset
        
        return node
    
    def __read_postfix_expr(self, lhs: ast.Expr) -> ast.Expr:
        "Inner function that returns a node with the current postfix operator and expression"
        
        op = self._eat(TokenType.PUNC)
        postfix_prec = self.__get_postfix_prec(op.value)
        self.logger.debug(f"{op.start_pos} began parsing postfix expression with '{op.value}'")
        self.logger.increasepad()
        if postfix_prec == None:
            self._fatal(f"{op.start_pos} expected postfix operator, got another punctuator.")
        
        # Figure which prefix operator it is
        opstr = op.value
        if opstr == "as":
            self.logger.debug("found CastExpr")
            signed = self._peek().ispunc("$")
            if signed: self._eat()
            cast_type = self.parse_type()
            node = ast.CastExpr(expr=lhs, cast_type=cast_type, signed=signed)
            del signed, cast_type
        elif opstr in ("->", "."):
            self.logger.debug(f"found MemberExpr with '{opstr}'")
            if opstr == ".":
                derefnode = lhs
            else:
                derefnode = ast.DerefExpr(pointer_expr=lhs)
                derefnode.lineno, derefnode.col_offset = lhs.lineno, lhs.col_offset
                derefnode.end_lineno, derefnode.end_col_offset = op.end_pos
            node = ast.AccessExpr(record_expr = derefnode, member_name=self._eat(TokenType.NAME).value)
            del derefnode
        elif opstr == "[":
            self.logger.debug("found IndexExpr")
            index_expr = self.parse_expr()
            self._eat(TokenType.PUNC, "]")
            node = ast.IndexExpr(array_expr=lhs, index_expr=index_expr)
            del index_expr
        elif opstr == "(":
            self.logger.debug("found CallExpr")
            args = []
            if not self._peek().ispunc(")"):
                args = self.parse_a_expr_list()
            self._eat(TokenType.PUNC, ")")
            node = ast.CallExpr(func_expr=lhs, args=args)
            del args
        
        # Set location data
        self.logger.debug(f"created Expr node of type '{node.__class__.__name__}'.")
        self.logger.decreasepad()
        node.lineno, node.col_offset = lhs.lineno, lhs.col_offset
        node.end_lineno, node.end_col_offset = self._peek(-1).end_pos
        
        return node
        
    def __read_infix_expr(self, lhs: ast.Expr) -> ast.Expr:
        "Inner function that returns a node with the current postfix operator and expression"
        
        op = self._eat(TokenType.PUNC)
        l_prec, r_prec = self.__get_infix_prec(op.value)
        self.logger.debug(f"{op.start_pos} began parsing rhs of infix expression with '{op.value}'")
        self.logger.increasepad()
        if l_prec == None or r_prec == None:
            self._fatal(f"{op.start_pos} expected infix operator, got another punctuator.")
        
        # Figure which prefix operator it is
        opstr = op.value
        opnode = None
        if is_op_assign(opstr):
            self.logger.debug(f"found AssignExpr")
            augop = None
            if get_assign_aug(opstr) != None:
                augop = get_assign_aug(opstr)()
            node = ast.AssignExpr(lhs=lhs, rhs=self.__parse_expr_inner(r_prec), op=augop)
            del augop
        elif opstr == "?":
            self.logger.debug(f"found TernaryExpr")
            true_expr = self.parse_expr()
            self._eat(TokenType.PUNC, ":")
            false_expr = self.__parse_expr_inner(r_prec)
            node = ast.TernaryExpr(cond_expr=lhs, true_expr=true_expr, false_expr=false_expr)
            del true_expr, false_expr
        elif (bincls := is_op_binary(opstr)) != None:
            self.logger.debug(f"found BinaryExpr")
            opnode = bincls()
            node= ast.BinaryExpr(left=lhs, op=opnode, right=self.__parse_expr_inner(r_prec))
        elif (bcondcls := is_op_bcond(opstr)) != None:
            self.logger.debug(f"found BinaryCondExpr")
            opnode = bcondcls()
            node= ast.BinaryCondExpr(left=lhs, op=opnode, right=self.__parse_expr_inner(r_prec))
        
        # Set location data
        self.logger.debug(f"created Expr node of type '{node.__class__.__name__}'.")
        self.logger.decreasepad()
        if opnode != None:
            opnode.lineno, opnode.col_offset = op.start_pos
            opnode.end_lineno, opnode.end_col_offset = op.end_pos
        node.lineno, node.col_offset = lhs.lineno, lhs.col_offset
        node.end_lineno, node.end_col_offset = self._peek(-1).end_pos
        
        return node
        
    def __get_postfix_prec(self, op: str) -> int | None:
        "Inner function that returns the precedence of the postfix operator passed or None"
        if op in ["as", "->", ".", "[", "("]: return 27
        return None
    
    def __get_prefix_prec(self, op: str) -> int | None:
        "Inner function that returns the precedence of the prefix operator passed or None"
        if op in ["&", "*", "!", "~", "+", "-"]: return 25
        return None
    
    def __get_infix_prec(self, op: str) -> tuple[int | None, int | None] | None:
        "Inner function that returns the precedence of the infix operator passed or None"
        
        if is_op_assign(op): return (2, 1)
        if op == "?": return (4, 3)
        if op == "||": return (5, 6)
        if op == "&&": return (7, 8)
        if op == "|": return (9, 10)
        if op == "^": return (11, 12)
        if op == "&": return (13, 14)
        if op in ["==", "!="]: return (15, 16)
        if op in ["<", "<=", "<$", "<=$", ">", ">=", ">$", ">=$"]: return (17, 18)
        if op in ["<<", ">>", ">>$"]: return (19, 20)
        if op in ["+", "-"]: return (21, 22)
        if op in ["*", "/", "/$", "%", "%$"]: return (23, 24)
        return None, None
    
    # LIST PARSING #
    def parse_param_list(self) -> tuple[ list[str], list[ast.Type], bool]:
        """
        Parses a comma-separated list of parameters of the form '<name>: <type>'.
        
        Returns a list of parameter names, a list of parameter types, and whether or not the parameter list is variadic (... as the last parameter).
        """
        
        start_pos = self._snapshot()
        self.logger.debug(f"{start_pos} began parsing list of parameters")
        self.logger.increasepad()
        
        param_names: list[str] = []
        param_types: list[ast.Type] = []
        is_variadic = False
        while True:
            param_names.append(self._eat(TokenType.NAME).value)
            self._eat(TokenType.PUNC, ":")
            param_types.append(self.parse_type())
            if not self._peek().ispunc(","): break
            self._eat(TokenType.PUNC, ",")
            if self._peek().ispunc("..."):
                is_variadic = True
                self._eat()
                if self._peek().ispunc(","):
                    self._fatal(Parser.L_INVALID_OPERATOR, f"{start_pos} '...' cannot be followed by another parameter definition.")
                break
        
        self.logger.decreasepad()
        
        return param_names, param_types, is_variadic
    
    def parse_type_list(self) -> tuple[list[ast.Type], bool]:
        """
        Parses a comma-separated list of types.
        
        Returns a list of parameter types, and whether or not the type list is variadic (... as the last type).
        """
        
        start_pos = self._snapshot()
        self.logger.debug(f"{start_pos} began parsing list of types")
        self.logger.increasepad()
        
        types: list[ast.Type] = []
        is_variadic = False
        while True:
            types.append(self.parse_type())
            if not self._peek().ispunc(","): break
            self._eat(TokenType.PUNC, ",")
            if self._peek().ispunc("..."):
                is_variadic = True
                self._eat()
                if self._peek().ispunc(","):
                    self._fatal(Parser.L_INVALID_OPERATOR, f"{start_pos} '...' cannot be followed by another parameter definition.")
                break
        
        self.logger.decreasepad()
        
        return types, is_variadic
    
    def parse_a_expr_list(self) -> list[ast.Expr]:
        "Parses a comma-separated list of expressions with assignment-precedence or higher."
        
        start_pos = self._snapshot()
        self.logger.debug(f"{start_pos} began parsing list of a_expr")
        self.logger.increasepad()
        
        a_expr_list: list[ast.Expr] = []
        while True:
            a_expr_list.append(self.parse_a_expr())
            if not self._peek().ispunc(","): break
            self._eat(TokenType.PUNC, ",")
        
        self.logger.decreasepad()
        
        return a_expr_list
    
    def parse_init_expr_list(self) -> list[ast.ComplexExpr | ast.Expr]:
        "Parses a comma-separated list of init expressions"
        
        start_pos = self._snapshot()
        self.logger.debug(f"{start_pos} began parsing list of init_expr")
        self.logger.increasepad()
        
        init_expr_list: list[ast.ComplexExpr | ast.Expr] = []
        while True:
            init_expr_list.append(self.parse_init_expr())
            if not self._peek().ispunc(","): break
            self._eat(TokenType.PUNC, ",")
        
        self.logger.decreasepad()
        
        return init_expr_list
        
    def parse_n_init_expr_list(self) -> dict[str, ast.ComplexExpr | ast.Expr]:
        "Parses a comma-separated list of named init expressions"
        
        start_pos = self._snapshot()
        self.logger.debug(f"{start_pos} began parsing list of named init_expr")
        self.logger.increasepad()
        
        elts: dict[str, ast.ComplexExpr | ast.Expr] = dict()
        while True:
            name = self._eat(TokenType.NAME)
            if name in elts:
                self._fatal(Parser.L_COMPLEX_REPEAT_KEY, f"{self._peek(-1).start_pos} cannot have repeated key '{name}' in init expression")
            self._eat(TokenType.PUNC, ":")
            elts[name] = self.parse_init_expr()
            if not self._peek().ispunc(","): break
            self._eat(TokenType.PUNC, ",")
        
        self.logger.decreasepad()
        
        return elts
        
# OPERATOR MAPPINGS #
def is_op_unary(op) -> ast.UnaryOp | None:
    "Checks if `op` is a unary operator and returns the class, or None if it isn't"
    if op == "+": return ast.UnaryPlus
    if op == "-": return ast.UnaryMinus
    if op == "~": return ast.BitNot
    return None

def is_op_ucond(op) -> ast.UnaryCOp | None:
    "Checks if `op` is a unary conditional operator and returns the class, or None if it isn't"
    if op == "!": return ast.LogicalNot
    return None

def is_op_binary(op) -> ast.BinOp | None:
    "Checks if `op` is a binary operator and returns the class, or None if it isn't"
    if op == "+": return ast.Add
    if op == "-": return ast.Sub
    if op == "*": return ast.Mult
    if op == "/": return ast.UDiv
    if op == "/$": return ast.SDiv
    if op == "%": return ast.UMod
    if op == "%$": return ast.SMod
    if op == "<<": return ast.ShLogLeft
    if op == ">>": return ast.ShLogRight
    if op == ">>$": return ast.ShArRight
    if op == "&": return ast.BitAnd
    if op == "^": return ast.BitXor
    if op == "|": return ast.BitOr
    return None

def is_op_bcond(op) -> ast.BinCOp | None:
    "Checks if `op` is a binary conditional operator and returns the class, or None if it isn't"
    if op == "&&": return ast.LogicalAnd
    if op == "||": return ast.LogicalOr
    if op == "==": return ast.Eq
    if op == "!=": return ast.NotEq
    if op == "<": return ast.ULt
    if op == "<=": return ast.ULtE
    if op == "<$": return ast.SLt
    if op == "<=$": return ast.SLtE
    if op == ">": return ast.ULt
    if op == ">=": return ast.ULtE
    if op == ">$": return ast.SLt
    if op == ">=$": return ast.SLtE
    return None
    
def is_op_assign(op) -> bool:
    "Checks if `op` is an assignment operator."
    if op[-1] != "=": return False
    if op == ":=": return True
    if get_assign_aug(op): return True
    return False

def get_assign_aug(op) -> ast.BinCOp | None:
    "Returns the binary operator augmenting this assignment operator, or None if there isn't one."
    return is_op_binary(op[:-1])