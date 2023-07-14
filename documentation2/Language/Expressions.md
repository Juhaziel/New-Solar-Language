# Expressions #
Expressions are constructs in New Solar which have an inherent type and value.

Scalar expressions can be used everywhere, but complex (aggregate) expressions can only be used as initializers for variables of the appropriate type.

## Scalar Expressions ##

### Atoms ###
The most basic expression is an atom. These can be recognized without regard to precedence or associativity.

The atoms are:
```
NAME            | Identifier
INT             | Integer or character literal
STR             | String literal
( EXPR )        | Parenthesized expression
sizeof ( TYPE ) | Size of type
```

### Operators ###
Other scalar expressions are built up from atoms and other expressions with operators. These operators have associativity and precedence.

The operators are:
```
Left-to-right
(1)  ()           | Function call
     []           | Array subscript
     .            | Member access
     ->           | Member access through pointer
     ~~ ~$ ~!     | Unsigned cast, signed cast, bitcast

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
     > >= >$ >=$  |
(7)  == !=        | Equal or not equal
(8)  &            | Bitwise AND
(9)  ^            | Bitwise XOR
(10) |            | Bitwise OR
(11) && &$        | Logical AND (short-circuit and non-short-circuit)
(12) || |$        | Logical OR (short-cirucit and non-short-circuit)
(13) :>           | Piping operator

Right-to-left
(14) ?:           | Ternary conditional
(15) :=           | Assignment
     += -=        | Assignment by sum or difference
     *=           | Assignment by multiplication
     /= /$=       | Assignment by unsigned or signed division
     %= %$=       | Assignment by unsigned or signed remainder
     <<= >>= >>$= | Assignment by logical or arithmetic shift
     &= ^= |=     | Assignment by bitwise AND, XOR, OR

Left-to-right
(15) ,            | Comma operator
```

## Aggregate Expressions ##

Aggregate expressions are only usable in a variable initializer.

There are three such types:
- Arrays
- Structures
- Unions

#### Arrays ####
are initialized with a comma-separated list of values enclosed in braces.

```
{ VALUE (, VALUE)* }
```

All values in an array must be castable to the declared type.

If fewer values are provided in an array initializer, the rest will be initialized to zero.

If more values are provided, this is an error.

#### Structures ####
are initialized with a comma-separated list of key-values pairs for the members, enclosed in braces preceded by the `struct` keyword.

```
struct { KEY := VALUE (, KEY := VALUE)* }
```

Unspecified members will be initialized to zero.

If keys for non-members are provided, this is an error.

#### Unions ####
are initialized with a single key-value pair for one of the members, enclosed in braces preceded by the "union" keyword.

```
union { KEY := VALUE }
```

If a non-member key or more than one key-value pair is provided, this is an error.