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

### Characters ###
Character literals are surrounded in single quotes (')
It will transform its content into its 8-bit UTF-8 (ASCII-only) codepoint or, if prefixed with `w`/`W`, into its 16-bit UTF-16 (BMP-only) codepoint.

Character literals support escape sequence which can be seen lower.

### String ###
Strings are a sequence of character literals grouped together and enclosed in double-quotes ("). They are considered to be of type `[n]int16` where n is the length of the string plus the null-terminator.

Like character literals, the default encoding is UTF-8, or UTF-16 if prefixed with `w`/`W`. Unlike character literals, Unicode codepoints that don't fit into a single word (UTF-8->ASCII, UTF-16->BMP) will be encoded with multiple words.

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

Octal, Hexadecimal and Unicode sequences may be represented as follows:

|Format|Description|
|----|----|
|`\[0-7]{1,6}`|Represents an arbitrary 16-bit value through octal digit. For 6 digits, the last one must be 0 or 1|
|`\x[0-9a-fA-F]{1,4}`|Represents an arbitrary 16-bit value through hexadecimal digits|
|`\u[0-9a-fA-F]{4}`|Represents a BMP Unicode grapheme through its hexadecimal codepoint|
|`\u[0-9a-fA-F]{6}`|Represents any Unicode grapheme through its hexadecimal codepoint|

For any of these special escape sequences, an initial 0 will terminate parsing.

`'\015'` -> `{0o0}15`
`'\105'` -> `{0o015}`

`\u` can only be used while parsing a wide (UTF-16) character or a string.
`\U` is only allowed for strings.
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