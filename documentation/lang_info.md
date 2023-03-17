# High Level Language Draft #

## TYPES ##
The basic types are `int`, `long`, and `quad`.
 
Pointers are represented by a prefixed `*`.

### VOLATILE ###
The volatile keyword preceeds the type it modifies and indicates that the variable in question should not be cached, but instead written to and read from memory every time it is accessed.

### VOID ###
The `void` type represents a type with no value.

Functions can have the `void` return type if they do not return anything.

Pointers pointing to `void` are considered generic.

No expression of type `void` can be used as parts of other expressions and may only be used for its potential side-effect.
(i.e. no `void` function or expression used in arithmetic, no `void` pointer being dereferenced, etc...)

### ARRAYS ###
Arrays are represented by a prefixed `[n]` where `n` is the amount of times to allocate space for the underlying type. These arrays can be casted to and from pointers to the same underlying type.

`n` must be left unspecified if the variable is initialized to a string or other list of expressions.

### STRUCTURES AND BITFIELDS ###
Structures and bitfields are complex types that contain multiple members accessible via the dot operator. The bits
```
struct NAME {
    NAME TYPE (: BITS) ,
    ...
}
```

Structure members are allocated in sequential order. `BITS` is by default the amount of bits `TYPE` will take in memory.

However, for an amount of bits smaller than its maximum, values will be allocated from lowest bit to highest bit. Sequential members of the same `TYPE` will be allocated in the same words until their sum surpasses the size of `TYPE`.

### UNIONS ###
Unions are similar to structures in their shape. However, a union type has the same size as its widest member. All members overlap.

```
union NAME {
    NAME TYPE (: BITS) ,
}
```

## GLOBAL SCOPE ##
Global scope represents the scope outside of functions. It contains only definitions or declarations of global objects.

### Declarations ###
In order for multiple files to be linked together, external declarations of identifiers in other files may be created as such:

```
let  NAME : TYPE ;
func NAME (PARAMS) -> ( TYPE ) ;
```

These declarations can appear as many times as necessary, although the compiler should consider all declarations as one.
If a declared variable or function is left undefined, it will be assumed external.

Constants cannot currently be declared external.

### Definitions ###
By default, every identifier defined in the global scope is considered visible outside of the file. As such, two files with clashing global identifiers cannot be linked together reliably. To avoid this problem, identifiers may be marked as `static` which limits their scope to this file only.

A global identifier can only have one definition which overwrites any previous declaration.

```
(static) let   NAME : TYPE = INIT_EXPR ;
(static) set   NAME : TYPE = EXPR ;
(static) func  NAME ( PARAMS ) -> ( TYPE ) { STMT ... }
inline   func  NAME ( PARAMS ) -> ( TYPE ) { STMT ... }
```

Constants must be of a simple type.

The `inline` keyword forces a function to be inlined where it is called and is automatically static. Inlined functions ignore the nomangle rule as they are not assigned a memory address.

### Variadic Functions ###
If the last parameter of a function signature's parameter list is "...", then

### Type definitions ###
Types can only be defined once. As such, it is recommended to import them only once through a header file with the `#import` preprocessor directive.

```
using  NAME = TYPE ;`
struct NAME { MEMBERS } ;`
union  NAME { MEMBERS } ;`
```

These can also be used within a local scope

## LOCAL SCOPE #
Local scope represents the scope inside of functions and is individual to each one. It contains statements that are executed in order and declarations.

### STATEMENTS ###

#### Definition Statement ####
```
(static) let NAME : TYPE (= INIT_EXPR) ;
```

If an initial value is not provided, the variables will either be left uninitialized (not static) or initialized to 0 (static)

#### Compound Statement ####
```
{ STMT ... }
```

A compound statement is simply a list of statements and definitions enclosed within braces.

Each block has its variable scope.

#### Jump Statement ####
```
continue (label) ;
break (label) ;
return (EXPR) ;
```

Goto statements jump to the specified label. Labels must be in ancestor or sibling scopes of the goto's scope.

Continue statements return to the beginning of a loop.

Break statements skip to the end of a loop.

##### Return #####
Return statements return an expression which much be the same type as the function it is contained in.

For `void` functions, there must be no expression.

If the end of the function is reached before any return statement, one is implicitly executed with value 0 (for non-void) or no value (for void).

#### If Statement ####
```
($ NAME :) if ( EXPR ) STMT
($ NAME :) if ( EXPR ) STMT else STMT
```

#### Iteration Statement ####
```
($ NAME :) while ( EXPR ) STMT
($ NAME :) while ( EXPR ) STMT else STMT
($ NAME :) for ( (EXPR) ; (EXPR) ; (EXPR) ) STMT
($ NAME :) for ( (EXPR) ; (EXPR) ; (EXPR) ) STMT else STMT
```

##### Labeled Control Flow #####
Control flow statements (if-else, while, for) may be preceded by a name which will be registered as its label.
These labels may be used with break (all statements) or continue (loop statements) 

#### Expression Statement and Expressions ####
`EXPR ;`

##### Atoms #####
Expression atoms are expressions that can be parsed without regard to precedence or associativity.
These include:
```
NAME            | Identifier
INT             | Integer or character literal
STR             | String literal
( EXPR )        | Parenthesized expression
szexpr ( EXPR ) | Size of expression type
sztype ( TYPE ) | Size of type
```

##### Casting #####
An unsigned cast can be done with the suffix keyword `as`. Following it by `$` will make a signed cast.

##### Operators #####
```
Left-to-right
(1)  ()           | Function call
     []           | Array indexing
     .            | Member access
     ->           | Member access through pointer
     as as$       | Casting

Right-to-left
(2)  + -          | Unary plus and minus
     ! ~          | Logical and Bitwise NOT
     *            | Dereference
     &            | Address-of

Left-to-right
(3)  * / /$ % %$  | Multiplication, division, signed division, remainder, signed remainder
(4)  + -          | Addition and subtraction
(5)  << >> >>$    | Logical left shift, logical right shift, arithmetic right shift
(6)  < <= <$ <=$  | Unsigned and signed comparison
     > >= >$ >=$
(7)  == !=        | Equal or not equal
(8)  &            | Bitwise AND
(9)  ^            | Bitwise XOR
(10) |            | Bitwise OR
(11) &&           | Logical AND
(12) ||           | Logical OR

Right-to-left
(13) ?:           | Ternary conditional
(14) =            | Assignment
     += -=        | Assignment by sum or different
     *=           | Assignment by multiplication
     /= /$=       | Assignment by unsigned or signed division
     %= %$=       | Assignment by unsigned or signed remainder
     <<= >>= >>$= | Assignment by logical or arithmetic shift
     &= ^= |=     | Assignment by bitwise AND, XOR, OR

Left-to-right
(15) ,            | Comma operator
```

## Function calls ##

The default calling convention supports variadic functions.
- Parameters are pushed from right to left.
- Integral and pointer types are returned through registers.
- Structs and unions are returned by copy through a caller-created space before the return address

The call stack is as such:
```
|-- CALLER FRAME
| ...
| (saved registers)
| p_n - nth parameter
| ...
| p_1 - 2nd parameter
| p_0 - 1st parameter
| (return struct/union space)
| return_address
|-- CALLEE FRAME
| previous frame base pointer
| (local variables)
| ...
```

The four registers used to return integral types are considered volatile (they must be saved by the caller).

In Mercury, these are, from highest to lowest, D, C, B, A (A for Int, BA for Long and Pointers, DCBA for Quad)

All other registers must be saved and restored by the callee.