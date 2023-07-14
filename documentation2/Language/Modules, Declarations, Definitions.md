# Modules, Declarations, Definitions #

"Module" is the name used to refer to a source file after all macros have been resolved by the Preprocessor.

A Module consists of global definitions which must be constantly initialized at compile time.

There are three types of global definitions

1. Global variable declaration/definition
2. Function declaration/definition
3. Global type definition

## Static Qualifier ##
Global variables and functions can take on the `static` modifier. This will mark the global object as being **module-local** and it will not be exported to other modules during linking.

A **static** global object can only appear once and must be constantly initialized at that time.

## Variable and Function Declarations ##
Unlike constants and type definitions, a global variable or function may be left uninitialized if it is preceded with `declare`, and it can appear multiple times.

If it is not defined in the module, the variable/function is declared **external**. If it is defined later in the module, it is declared **global** (or **module-local** if **static**).

Therefore, it is recommended to put such declarations into header files that both the users and implementor can include during the preprocessor stage.

**Note:** The parameter names of a function declaration need not match the parameter names of its definition. The parameter names may also be omitted from the declaration, but the types must match for all appearances of the function.

## Global Variables ##
Global variables can be of any type as long as its initializer can be constantly evaluated at compile time.

```
declare (static) var NAME : TYPE ;
(static) var NAME : TYPE := VALUE ;
```

## Functions ##
Functions have a return type and parameter types. It contains a list of statements to be executed in sequence and may be called by statements in itself or other functions.

```
declare (static) fun NAME ( (PARAMS) ) -> TYPE ;
(static) fun NAME ( (PARAMS) ) -> TYPE { STMTS }
```

`PARAMS` is a comma-separated list of parameter types and names (for definitions). It may also be followed by `...` to indicate a variadic function.

Variadic functions must have at least one named parameter.

## Global Types ##
Global types include definitions of structures and unions or aliasing of other types through the `using` keyword.

```
using NAME := TYPE ;
struct NAME { MEMBERS } ;
union NAME { MEMBERS } ;
```

The `MEMBERS` field is simply a list of declarations of shape `NAME : TYPE ;`
