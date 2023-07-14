# Scoping #

A (lexical) scope restricts the reach of a variable to itself, allowing for variable shadowing and lessening the chance of namespace collisions.

# Global Scope #

Every module is assigned a global scope in which every object is considered to exist at the same time. This scope's elements are assigned at compile time and therefore must be compile-time constants.

The global scope may contain global variable declarations/definitions, function declarations/definitions, and global type definitions.

# Block Scope #

Every block statement creates a new anonymous block scope.

Block statements include:
- Compound statement
- If/else statement
- Loop statement

Block scopes can contain local variable definitions and local type definitions.

# Function Scope #

The parameters of a function are contained in their own special local scope right above the block statement of its body.