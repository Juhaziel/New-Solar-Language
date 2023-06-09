# High Level Language Draft #

## TYPES ##
The basic types are `int`, `long`, and `quad`.
 
Pointers are represented by a prefixed `*`.

### VOLATILE ###
The `volatile` keyword preceeds the type it modifies and indicates that the variable in question should not be cached, but instead written to and read from memory every time it is accessed.

### VOID ###
The `void` type represents a type with no value.

Functions can have the `void` return type if they do not return anything.

Pointers pointing to `void` are considered generic.

No expression of type `void` can be used as parts of other expressions and may only be used for its potential side-effect.
(i.e. no `void` function or expression used in arithmetic, no `void` pointer being dereferenced, etc...)

### ARRAYS ###
Arrays are represented by a prefixed `[n]` where `n` is the amount of times to allocate space for the underlying type. These arrays can be casted to and from pointers to the same underlying type.

`n` must be left unspecified if the variable is initialized to a string or other list of expressions. In this case, the size will automatically be detected unless the type of the declaration is an alias.

### STRUCTURES AND BITFIELDS ###
Structures and bitfields are complex types that contain multiple members accessible via the dot operator.
```
struct {
    NAME : TYPE (: BITS) ,
    ...
}
```

Structure members are allocated in sequential order. `BITS` is by default the amount of bits `TYPE` will take in memory and must be an integer (expressions are not allowed).

However, for an amount of bits smaller than its maximum, values will be allocated from lowest bit to highest bit. Sequential members of the same `TYPE` will be allocated in the same words until their sum surpasses the size of `TYPE`.

### UNIONS ###
Unions are similar to structures in their shape. However, a union type has the same size as its widest member. All members overlap.

```
union {
    NAME : TYPE (: BITS) ,
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
(static) let   NAME : TYPE := INIT_EXPR ;
(static) set   NAME : TYPE := EXPR ;
(static) func  NAME ( PARAMS ) -> ( TYPE ) { STMT ... }
inline   func  NAME ( PARAMS ) -> ( TYPE ) { STMT ... }
```

Constants must be of a simple integral type.

Static variable and functions can only be declared once and must immediately be given a value/body.

The `inline` keyword forces a function to be inlined where it is called and is automatically static. Inlined functions ignore the nomangle rule as they are not assigned a memory address.

### Variadic Functions ###
If the last parameter of a function signature's parameter list is "...", then

### Type definitions ###
Types can only be defined once per scope. As such, it is recommended to import them only once through a header file with the `#import` preprocessor directive.

```
using  NAME = TYPE ;`
struct NAME { MEMBERS } ;`
union  NAME { MEMBERS } ;`
```

These can also be used within a local scope where they can be used before or after declaration.

## LOCAL SCOPE #
Local scope represents the scope inside of functions and is individual to each one. It contains statements that are executed in order and declarations.

### STATEMENTS ###

#### Definition Statement ####
```
(static) let NAME : TYPE := INIT_EXPR ;
```

An initial value must be given for function-local variables.

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
breakif (label) ;
return (EXPR) ;
```

##### Continue #####
Continue statements skip to the next iteration of a loop that contains it.

If a label is specified, it will restart in the loop specified by the label.

##### Break and Breakif #####
Break statements immediately exit the loop (break) or the if-else (breakif) statement that contains it.
If a label is specified, it will exit the if-else or loop specified by the label.

##### Return #####
Return statements return an expression which much be the same type as the function it is contained in.

For `void` functions, there must be no expression.

If the end of a non-`void` function is reached before any return statement, behaviour is undefined. If instead an expression of a different type is returned, this is an error.

#### If Statement ####
```
(NAME :) if ( EXPR ) STMT
(NAME :) if ( EXPR ) STMT else STMT
```

#### Iteration Statement ####
```
(NAME :) while ( EXPR ) STMT
(NAME :) while ( EXPR ) STMT else STMT
(NAME :) for ( (EXPR) ; (EXPR) ; (EXPR) ) STMT
(NAME :) for ( (EXPR) ; (EXPR) ; (EXPR) ) STMT else STMT
```

##### Labeled Control Flow #####
Control flow statements (if-else, while, for) may be preceded by a name which will be registered as its label.
These labels may be used with break (loop statements), breakif (if statements), or continue (loop statements) 

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
An unsigned cast can be done with the suffix keyword `as`. Following it by `$` will make a signed cast, but doing this on non-integral types is an error.

Integers, arrays, pointers, and function can all be casted to one another.

Structures and unions may only be casted to each other if they are equivalent (same members with the same names).

Non-logical binary expressions automatically cast their right operand to the same type as their left operand.

If any pointer or array type is present in a binary expression, the only operations supported are addition, subtraction, equal, not equal, logical AND, logical OR.

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
(14) :=           | Assignment
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
- Integral and pointer types are returned through registers A and B (A for int, BA for long).
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

In Mercury, the first four general purpose registers (A, B, C, D) are considered volatile (they must be saved by the caller).

All other registers must be saved and restored by the callee.