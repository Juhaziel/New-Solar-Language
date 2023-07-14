# Types #

New Solar v3 currently supports the following types:

**Scalar Types**
- Integers
- Pointers

**Aggregate Types**
- Arrays
- Structures
- Unions

**Special Types**
- Functions
- Void

## Qualifiers ##

All types (except Void) can take the `volatile` qualifier. This will inform the compiler that the object of the specified type may be changed and therefore must be stored to and loaded from memory each time it is accessed.

All declarations are **non-volatile** by default, except for the **type of the value pointed to by a pointer or the values contained in an array**.

This exception can be disabled for pointers by qualifying it with the `lone` qualifier.

## Scalar Types ##

These types are the basic blocks directly accessible via registers in assembly.

By default these values are considered base-10, but the followed prefixes can be used:

|Prefix|Base|
|------|----|
|`0b, 0B`|2|
|`0o, 0O`|8|
|`0x, 0X`|16|

### Integers ###
are the numbers a basic CPU can operate on.

New Solar for Mercury has support of two integer widths, `int16` and `int32`.

These two types take no suffix and an `l` suffix on integer constants, respectively.

### Pointers ###
represent an address in RAM.

Pointer literal constants must be suffixed by `p` and are of type `*void`.

## Aggregate Types ##

These types contain multiple other values and cannot be stored directly into registers.

### Arrays ###
represent a contiguous and indexable set of values of a same type.

Arrays of size **n** and inner type **TYPE** are declared with the syntax `[n]TYPE`.

The size of the array can be left undefined when its value is defined in a declaration. It will implicitly be of the size of its initializer.

### Structures ###
represent a record of multiple types as one unit.

The elements of a structure are guaranteed to be allocated sequentially and to be packed.

### Unions ###
represent a variant type with the same size as its widest members. All of its element overlap in memory.

## Special Types ##

### Functions ###
store the return type and parameter types as well as whether or not the function is variadic.

### Voids ###
indicate a lack of value.

`void` can be used as:
- the return type of a function with no return value
- the inner type of a generic pointer
- a cast target to mark explicit disregard for an expression's value

## Type Definitions ##

New Solar allows aliasing of types via the `using` keyword.

```
using NAME := TYPE;
```

Type names exist in a separate namespace and must be assigned to defined types (no arrays of undefined size.)

## The `typeof` keyword ##

The `typeof` keyword evaluates to the type of the expression that is passed to it and can be used wherever types are allowed.