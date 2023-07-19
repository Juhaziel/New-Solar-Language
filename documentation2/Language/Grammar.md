# Grammar #

Below is a rough grammar of New Solar.

```
#-- GLOBAL, DECLARATIONS, DEFINITIONS --#
<MODULE>          := {<GLOBAL_DECLDEF>} <eof> ;

<GLOBAL_DECLDEF>  := <FUNC_DECL>
                   | <VAR_DECL>
                   | <FUNC_DEF>
                   | <SCOPED_DEF>
                   ;

<SCOPED_DEF>      := <VAR_DEF>
                   | <USING_DEF>
                   ;

<FUNC_DECL>       := "declare" ["static"] "fun" <name> '(' [<PARAM_DECL_LIST>] ')' '->' <TYPE> ';' ;

<VAR_DECL>        := "declare" ["static"] "var" <name> ':' <TYPE> ';' ;

<FUNC_DEF>        := ["static"] "fun" <name> '(' [<PARAM_LIST>] ')' '->' <TYPE> <COMPOUND_STMT> ;

<VAR_DEF>         := ["static"] "var" <name> ':' <TYPE> [':=' <INIT>] ';' ;

<USING_DEF>       := "using" <name> '=' <TYPE> ';'
                   | "struct" <name> <RECORD_LIST> ';'
                   | "union" <name> <RECORD_LIST> ';'
                   ;

<PARAM_OR_FIELD>  := <name> ':' <TYPE> ;

<PARAM_DECL>      := [<name> ':'] <TYPE> ;

#-- TYPES --#
<TYPE>            := ["volatile"] <NVTYPE>
                   | "void"
                   ;

<NVTYPE>          := "int16" | "int32"
                   | {"lone"} '*' <NVTYPE>
                   | '[' [<COMMA_EXPR>] ']' <NVTYPE>
                   | "fun" '(' {<PARAM_TYPE_LIST>} ')' '->' <TYPE>
                   | "struct" <RECORD_LIST>
                   | "union" <RECORD_LIST>
                   | <name>
                   | "typeof" '(' <COMMA_EXPR> ')'
                   ;

#-- EXPRESSIONS --#
-- Review Expressions.md for precedence and associativity

<INIT>            := '{' <INIT_LIST> '}'
                   | "struct" '{' <FIELD_INIT_LIST> '}'
                   | "union" { <FIELD_INIT> }
                   | <COMMA_EXPR>
                   ;

<FIELD_INIT>      := <name> ':' <INIT> ;

<COMMA_EXPR>      := <AEXPR_LIST>
                   | <ASSIGN_EXPR>
                   ;

<ASSIGN_EXPR>     := <ASSIGN_EXPR> <assignop> <EXPR>
                   | <EXPR>
                   ;

<EXPR>            := <EXPR> '?' <EXPR> ':' <EXPR>
                   | <EXPR> ':>' <EXPR>
                   | <EXPR> <binop> <EXPR>
                   | <EXPR> <bcondop> <EXPR>
                   | <unop> <EXPR>
                   | <uncondop> <EXPR>
                   | '&' <EXPR>
                   | '*' <EXPR>
                   | <EXPR> <castop> <TYPE>
                   | <EXPR> '->' <name>
                   | <EXPR> '.' <name>
                   | <EXPR> '[' <COMMA_EXPR> ']'
                   | <EXPR> '(' <AEXPR_LIST> ')'
                   | <ATOM>
                   ;

<ATOM>            := "sizeof" '(' <TYPE> ')'
                   | '(' <COMMA_EXPR> ')'
                   | <string>
                   | <wstring>
                   | <int>
                   | <char>
                   | <wchar>
                   | <name>
                   ;

#-- STATEMENTS --#
<STMT>            := ';'
                   | <SCOPED_DEF>
                   | <COMPOUND_STMT>
                   | <COMMA_EXPR> ';'
                   | [<name> ':'] "if" '(' <COMMA_EXPR> ')' <STMT> ["else" <STMT>]
                   | [<name> ':'] "while" '(' <COMMA_EXPR> ')' <STMT> ["else" <STMT>]
                   | [<name> ':'] "for" '(' [<COMMA_EXPR>] ';' [<COMMA_EXPR>] ';' [<COMMA_EXPR>] ')' <STMT> ["else" <STMT>]
                   | continue [<name>] ';'
                   | break [<name>] ';'
                   | breakif [<name>] ';'
                   | return [<COMMA_EXPR>] ';'
                   ;

<COMPOUND_STMT>   := '{' {<STMT>} '}' ;

#-- LISTS --#
<PARAM_LIST>      := <PARAM_OR_FIELD> {',' <PARAM_OR_FIELD>} [',' '...'] ;

<PARAM_DECL_LIST> := <PARAM_DECL> {',' <PARAM_DECL>} [',' '...'] ;

<PARAM_TYPE_LIST> := <TYPE> {',' <TYPE>} [',' '...'] ;

<RECORD_LIST>     := '{' <PARAM_OR_FIELD> {',' <PARAM_OR_FIELD>} [','] '}' ;

<INIT_LIST>       := <INIT> {',' <INIT>} ;

<FIELD_INIT_LIST> := <FIELD_INIT> {',' <FIELD_INIT>} ;

<AEXPR_LIST>      := <ASSIGN_EXPR> {',' <ASSIGN_EXPR>} ;
```