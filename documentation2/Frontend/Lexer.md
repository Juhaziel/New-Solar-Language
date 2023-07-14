# Lexer #

The Lexer component's task is to split the source code into Tokens for use in the Parser.

## Token Types ##
The tokens of the Lexer fall into 6 broad categories, those being:

|Type Name|Description|
|----|----|
|**TkKeyword**|Any language keyword|
|**TkName**|An identifier, be it for a type or variable|
|**TkInt**|An integer or character|
|**TkStr**|A string of characters|
|**TkPunc**|Any punctuator or operator|
|**TkEof**|End of file, added by the Lexer|

### Keywords ###
|Keyword|Description|
|----|----|
|`declare`|Indicates a declaration instead of a definition|
|`static`|Storage qualifier|
|`var` `fun`|Declaration or definition|
|`struct` `union` `using`|Used to define record types or type aliases|
|`volatile` `lone`|Type qualifier|
|`int16` `int32`|Basic integral types|
|`void`|Special void type|
|`typeof`|Evaluates to the type of the expression passed to it|
|`if` `else` `while` `for`|Conditional control flow|
|`continue` `break` `breakif` `return`|Unconditional control flow|

### Names ###
Names, or identifiers, are strings of character used to identify entities.

A name can be made from the alphanumerical characters and an underscore.

A name cannot begin with a number.

Names beginning with an underscore followed by a capital letter are reserved for library code. The Lexer will throw an error unless `allow_reserved=true` is specified.

### Integers ###
Integer tokens are formed either from integer literals, character literals, or pointer literals.

Integer literals are 16-bit by default, and 32-bit if suffixed with `l`.

Character literals are strictly 16-bits.

Pointer literals are strictly 32-bits.

### String ###
Strings are a sequence of character literals grouped together. They are considered to be of type `[n]int16` where n is the length of the string plus the null-terminator.

#### Escape Sequences ####
A character can be escaped by putting a backslash (`\`) in front of it.

The basic escape characters are:

|Code|Value|Description|
|----|----|
|`\0`|0x00|Null|
|`\a`|0x07|Bell|
|`\b`|0x08|Backspace|
|`\t`|0x09|Horizontal tab|
|`\n`|0x0A|Line feed|
|`\v`|0x0B|Vertical tab|
|`\f`|0x0C|Form feed|
|`\r`|0x0D|Carriage return|
|`\e`|0x1B|Escape|
|`\d`|0x7F|Delete|
|`\\`|\ |Escaped backslash|
|`\'`|'|Escaped single quote|
|`\"`|"|Escaped double quote|

Hexadecimal and Unicode sequences may be represented as follows:

|Format|Description|
|----|----|
|`\x[0-9a-fA-F]{1,4}`|Represents an arbitrary 16-bit value through hexadecimal digits|
|`\u[0-9a-fA-F]{1,4}`|Represents a BMP Unicode grapheme through its hexadecimal codepoint|
|`\u[0-9a-fA-F]{1,6}`|Represents any Unicode grapheme through its hexadecimal codepoint|

Please note that `\U` can only be used while parsing a string.

Characters and Strings are encoded using UTF-16, unlike previous versions that used UTF-8.

If the backslash is followed by an unrecognised character, then only that character will be kept.

### Punctuators ###
All other symbols in New Solar fall under the category of punctuators.

|Punctuator|Purpose|
|----|----|
|`(` `)` `{` `}` `[` `]`| Parentheses, braces, brackets|
|`.` `,` `->` `?` `:` `;`|Miscelleanous|
|`...`|Variadic marker|
|`sizeof`|Get the size in words of the expression|
|`~~` `~$` `~!`|Casting operators|
|`+` `-` `*` `/` `/$` `%` `%$`|Arithmetic, dereference, unary plus and minus|
|`<<` `>>` `>>=`|Shifting operators|
|`==` `!=` `<` `>` `<=` `>=` `<$` `>$` `<=$` `>=$` |Equality and comparison operators|
|`!` `&&` `&$` `||` `|$`|Logical operators|
|`~` `&` `|` `^`|Bitwise operators|
|`:>`|Function input piping|
|`:=` `+=` `-=` `*=` `/=` `/$=` `%=` `%$=` `<<=` `>>=` `>>$=` `&=` `^=` `|=`|Assignment operators|

The Lexer will provide methods for differentiating the different punctuators.