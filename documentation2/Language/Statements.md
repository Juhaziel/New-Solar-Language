# Statements #

Statements are instructions to be executed by a function. Statements are divided into multiple types.

## Definition Statements ##

```
(static) var NAME : TYPE (:= VALUE) ;
```

A definition statement is the analogue to global definition statements. It creates a new variable in the current lexical scope.

All variable names must be unique within the scope they are declared within and may be used within that scope or in inner scopes.

However, variables can shadow a variable with the same name if that variable is defined in an outer scope. In an expression using a shadowed variable, the definition in the innermost scope will be used.

Non-static variables may be left uninitialized.

### Static Local Variables ###

A variable marked as static behaves like a global variable, and therefore must be initialized to a compile-time constant, but will only be visible in the scope it is declared in and that scope's inner scopes.

Unlike a non-static variable, an uninitialized static variable will be initialized to its zero-value.

## Compound Statements ##

```
{ STMT ... }
```

Compound statements simply represent a grouping of statements executed sequentially.

## Expression Statements ##

```
EXPR ;
```

An expression statement executes the expression that it specifies, with all side-effects.

## Control Flow Statements ##
```
(NAME :) if ( EXPR ) STMT (else STMT)
(NAME :) while ( EXPR ) STMT (else STMT)
(NAME :) for ( (EXPR) ; (EXPR) ; (EXPR) ) STMT (else STMT)

continue (NAME) ;
break (NAME) ;
breakif (NAME) ;
return (EXPR) ;
```

Control flow statements allow the flow of execution to be changed from the default sequential execution.

### The `for` loop ###
The `for` loop is syntactic sugar over the while loop.

Its header consists of three optional expressions.

The **first** expression, also known as the **init expression**, will execute once before entering the loop's body.

The **second** expression, known as the **condition**, will be tested each time the loop restart. If it is not present, the condition is assumed to be true.

The **third** expression, known as the **footer expression**, will execute at the end of a loop or after a `continue` statement.

### The `else` clause ###
The if and loop statements both allow for an else clause. The statement it specified will execute if the condition of these conditional structures evaluates to false.

It will not be executed if a `break` or `breakif` statement is executed.

### Labels and unconditional flow ###
The if and loop statements can be preceded by labels which are only addressable by the `continue`, `break`, and `breakif` statement.

#### `continue` ####
The `continue` keyword will immediately return to the beginning of the innermost loop it is contained in, or if called with a label, to the beginning of the loop with such a label. The condition of the loop is rechecked before restarting the loop and the footer expression is executed if one has been defined.

#### `break` ####
The `break` keyword will immediately terminate the innermost loop, or if called with a label, the loop with such a label. The else clause of the loop will also be ignored.

#### `breakif` ####
The `breakif` keyword will exit from the innermost `if` or `else` statement, or if called with a label, the `if` or `else` statement with such a label.

### The `return` statement ###
The `return` statement may be used anywhere within a function.

If the function has a return type, then the return statement must have an expression of the exact same type.

If the function has no return type, then the return statement should not have such an expression.