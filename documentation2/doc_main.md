# New Solar Draft v3 #
This file presents an overview of the documentation and its structure.

Documentation is split into three subcategories.

|Folder|Purpose|
|------|-------|
|Language|Language features, syntax, semantics, etc.|
|Preprocessor|Macros,Conditional Compilation|
|Frontend|Lexer, Parser, Symbol Table, Semcheck, IR Generator|
|Optimizer|IR Optimizer|
|Generator|Assembly Generator, Optimizer|

Version 3 of the New Solar compiler makes use of an improved IR based on basic blocks (no SSA) instead of purely relying on the AST. This was done in an effort to replicate the portability of LLVM in case of future additions to the language without over complicating the scope of this compiler.

## Language ##
New Solar v3 is a C-like toy language made for compilation to the custom Mercury CPU, as well as hopefully some future CPU architectures.

Its goal is to be a low-level systems programming language that can serve as a higher level of abstraction over Mercury assembly. 

Since the systems programming language I am most familiar with is C, New Solar is also an unsafe, strongly and statically typed language which allows for pointer arithmetic.

A program, or module, is made of multiple global objects, like variable, constant, type, and function declarations.

Functions may contain statements and define more variables and types, but may not declare other functions or constants within themselves.

## Preprocessor ##
The preprocessor phase executes before compilation, executes preprocessor directives and detects and expands macro definitions.

## Frontend ##
The front-end is responsible for taking in a source file, parsing it into an AST, simplifying the AST and generating an NSIR file from it.

It translates New Solar into NSIR by segmenting the source code into basic blocks, flattening the symbol table so that it only contains a global/local distinction, and factoring large expressions into simpler ones.

## Optimizer ##
The optimizer's purpose is self-explanatory. It performs as many optimizations on NSIR as I'll bother implementing.

## Backend
The back-end will take an NSIR file and convert it to assembly by translating the few left-over higher-level constructs. It will also perform some peephole optimizations before output the final result.