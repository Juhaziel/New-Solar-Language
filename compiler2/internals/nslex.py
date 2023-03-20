from enum import Enum
import re
import internals.nslog as nslog
import internals.nstypes as nstypes

class TokenType(Enum):
    KEYWORD = "Keyword" # For keywords, value is keyword_name
    NAME = "Name" # For declared values, value is name
    INTEGER = "Int" # For integer literals, value is (value, type)
    STRING = "String" # For string literals, value is utf8 array
    PUNC = "Punctuator" # For punctuation, delimiters, and operators, value is punctuator
    COMMENT = "Comment" # For comments, value is comment without comment delimiters
    EOF = "EOF" # For the end of file

Keywords = (
    "set", "let", # Value definitions
    "func", # Function definitions
    "struct", "union", # Record definitions
    "using", # Type reference definition
    "static", # Access modifier
    "inline", # Function modifier
    "void", "int", "long", "quad", # Basic types
    "volatile", # Type modifier
    "if", "else", "for", "while", # Conditional control flow
    "break", "breakif", "continue", # Jump statements
)

Punctuators = (
    "(", ")", "{", "}", "[", "]", # Parentheses, braces, brackets
    ".", ",", "->", ":", ";", # Punctuation gang
    "?", # Lonely ternary
    "as", # Casting
    "$", # Label marker, when alone
    "...", # variadic
    "szexpr", "sztype", # The sizing siblings
    "+", "-", "*", "/", "/$", "%", "%$", # Normal arithmetic, also dereference and unary plus/minus
    "<<", ">>", ">>$", # Shift gang
    "==", "!=", "<", ">", "<=", ">=", "<$", ">$", "<=$", ">=$", # Comparators
    "!", "&&", "||", # Logicals
    "~", "&", "|", "^", # Bitwise
    ":=", "+=", "-=", "*=", "/=", "/%=", "%$=", "%$=", "<<=", ">>=", ">>$=", "&=", "|=", "^=", # Assignments
)

class Token:
    def __init__(self, type: TokenType, value: any, start_pos: tuple[int, int], end_pos: tuple[int, int]):
        """
        type:
            The TokenType type of the token
            
        value:
            The relevant value for the token
            
        start_pos:
            The starting position of the token as a tuple (line, column)
            
        end_pos:
            The ending position of the token as a tuple (line, column)
        """
        self.type = type
        self.value = value
        self.start_pos = start_pos
        self.end_pos = end_pos
    
    def istype(self, type: TokenType, value: any = None) -> bool:
        if self.type != type: return False
        if value:
            if isinstance(value, tuple): return self.value in value
            return self.value == value
        return True
    
    def iskeyword(self, keyword: any = None) -> bool:
        return self.istype(TokenType.KEYWORD, keyword)
    
    def isname(self, name: any = None) -> bool:
        return self.istype(TokenType.NAME, name)
    
    def isint(self) -> bool:
        return self.istype(TokenType.INTEGER)
    
    def isstring(self) -> bool:
        return self.istype(TokenType.STRING)
    
    def ispunc(self, punctuator: any = None) -> bool:
        return self.istype(TokenType.PUNC, punctuator)
    
    def iscomment(self) -> bool:
        return self.istype(TokenType.COMMENT)
    
    def iseof(self) -> bool:
        return self.istype(TokenType.EOF)

class Lexer:
    L_UNKNOWN = 1
    L_INVALIDINTPREFIX = 10
    L_INVALIDINTSUFFIX = 11
    L_CANNOTTRUNCATE = 12
    L_ALPHAAFTERNUM = 13
    L_MISSINGQUOTE = 20
    L_INVALIDUNICODECHAR = 21
    L_INVALIDSTRINGCHAR = 22
    L_EOF = 99
    
    def __init__(self, source):
        self.source = source
        self.srcpos = 0
        self.curln = 1
        self.curcol = 0
        self.success = True
        self.logger = nslog.LoggerFactory.getLogger()
    
    def _snapshot(self) -> tuple[int, int]:
        "Returns a snapshot of the current position, (curln, curcol)"
        return (self.curln, self.curcol)

    def _error(self, code: int, error: str):
        "Throw an error and mark lex as unsuccessful but continue lexing."
        self.logger.error(f"{{L{code:02}}} {error}")
        self.success = False
    
    def _fatal(self, code: int, error: str):
        "Throw a fatal error which marks lex as unsuccessful and aborts."
        self.logger.fatal(f"{{L{code:02}}} - {error}")
        self.success = False
        raise Exception("nslex encountered a fatal error.")
    
    def _peek(self, num=1, ahead=0) -> str:
        """
        Peeks `num` characters starting `ahead` characters off from the current position.
        
        Truncates the result if EOF was met.
        """
        text = self.source[self.srcpos+ahead:self.srcpos+ahead+num]
        return text
    
    def _advance(self, num=1) -> bool:
        """
        Advances the current character by num and updates position.
        
        Returns False if EOF was met, True otherwise.
        """
        while num > 0 and self.srcpos < len(self.source):
            num -= 1
            self.curcol += 1
            if self._peek() == "\n":
                self.curln += 1
                self.curcol = 0
            self.srcpos += 1
        return num == 0
    
    def _skipws(self):
        """
        Advances through all the consecutive whitespace characters it can find.
        """
        while (peek := self._peek()) != None and peek.isspace():
            self._advance()
            
    def lex_all(self) -> list[Token]:
        """
        Lex all tokens in source.
        """
        tokens = []
        while True:
            token = self.next_token()
            tokens.append(token)
            value_str = str(token.value).replace("\n", "\\n")
            start_pos_str = f"({token.start_pos[0]:>3}, {token.start_pos[1]:>3})"
            end_pos_str = f"({token.end_pos[0]:>3}, {token.end_pos[1]:>3})"
            if len(value_str) > 30:
                value_str = value_str[:30] + "..."
            self.logger.debug(f"lexed token {start_pos_str} - {end_pos_str}:   type= {token.type.name:>7},   value= '{value_str}'")
            if token.type == TokenType.EOF:
                return tokens
    
    def next_token(self) -> Token:
        """
        Get the next token in source.
        
        Returns EOF token if EOF was met.
        """
        while self._peek() != "":
            # Ignore whitespace
            if self._peek().isspace():
                self._skipws()
                continue
            
            # Tokenize comments
            if self._peek(2) == "/*":
                self._advance(2)
                value = ""
                start_pos = self._snapshot()
                while self._peek(2) != "*/":
                    end_pos = self._snapshot()
                    value += self._peek()
                    if not self._advance():
                        self._fatal(Lexer.L_EOF, f"{end_pos}: unexpected EOF in comment at {start_pos}")
                self._advance(2)
                return Token(TokenType.COMMENT, value, start_pos, end_pos)
            
            # Parse an integer
            if self._peek().isdigit():
                return self._readInt()
            
            # Parse a character
            if self._peek() == "'":
                start_pos = self._snapshot()
                
                # Discard the opening quote
                self._advance()
                
                char_int, can_truncate = self._readCharAsInt()
                
                # Check and discard closing quote
                if self._peek() != "'":
                    self._fatal(Lexer.L_MISSINGQUOTE, f"{self._snapshot()}: expected a single-quote to close character literal at {start_pos}")
                end_pos = self._snapshot()
                self._advance()
                
                # Test for integer literal suffix
                int_type, maximum, new_end_pos = self._readIntSuffix()
                if new_end_pos: end_pos = new_end_pos
                
                if (peek := self._peek()) and (peek.isalpha() or peek=="_"):
                    self._error(Lexer.L_ALPHAAFTERNUM, f"{self._snapshot()}: alphabetic characters cannot immediately follow a character literal. did you forget a space?")
                
                if char_int != (char_int & maximum-1):
                    if not can_truncate:
                        self._fatal(Lexer.L_CANNOTTRUNCATE, f"{start_pos}: character literal value '{char_int}' ({hex(char_int).upper()}) cannot be truncated to fit into integer type '{int_type}')")
                    self.logger.warn(f"{start_pos}: character literal value '{char_int}' ({hex(char_int).upper()}) was truncated to fit into integer type '{int_type}'")
                    self.logger.warn(f"new value is '{char_int & maximum-1}' ({hex(char_int & maximum-1).upper()})")
                char_int &= maximum-1
                
                return Token(TokenType.INTEGER, (char_int, int_type), start_pos, end_pos)
            
            # Parse a string as utf-8, 1 byte per word
            if self._peek() == '"':
                return self._readString()
            
            # Parse a punctuator
            if (punc := self._tryReadPunc()):
                return punc
            
            # Parse a keyword or name
            if (name := self._tryReadKeywordOrName()):
                return name
            
            self._fatal(Lexer.L_UNKNOWN, f"{self._snapshot()}: unexpected character '{self._peek()}'.")
        
        return Token(TokenType.EOF, None, self._snapshot(), self._snapshot())
                
    def _readInt(self) -> Token:
        """
        Read an integer literal.
        
        Accepts the prefixes 0b, 0o, 0x.
        """
        start_pos = self._snapshot()
        base = 10 # Assume decimal
        
        if self._peek() == '0':
            if (peek := self._peek(ahead=1).lower()) and peek.isalpha():
                self._advance()
                if   peek == "b": base = 2
                elif peek == "o": base = 8
                elif peek == "x": base = 16
                else: self._fatal(Lexer.L_INVALIDINTPREFIX, f"{start_pos}: invalid integer literal base prefix '0{peek}'")
                self._advance()
        
        chars = "0123456789ABCDEF"[0:base]
        num_string = ""
        while (peek := self._peek()) and (peek.upper() in chars):
            num_string += peek
            end_pos = self._snapshot()
            self._advance()
            while self._peek() == "_":
                end_pos = self._snapshot()
                self._advance()
        
        if num_string == "":
            self._fatal(Lexer.L_EOF, f"{self._snapshot()}: expected number, got EOF.")
        
        # Test for integer literal suffix
        int_type, maximum, new_end_pos = self._readIntSuffix()
        if new_end_pos: end_pos = new_end_pos
        
        if (peek := self._peek()) and (peek.isalpha() or peek=="_"):
            self._error(Lexer.L_ALPHAAFTERNUM, f"{self._snapshot()}: alphabetic characters cannot immediately follow an integer literal. did you forget a space?")
        
        int_value = int(num_string, base=base)
        if int_value != (int_value & maximum-1):
            self.logger.warn(f"{start_pos}: integer literal value '{int_value}' was truncated to fit into integer type '{int_type}'")
            self.logger.warn(f"new value is '{int_value & maximum-1}'")
        int_value &= maximum-1
        
        return Token(TokenType.INTEGER, (int_value, int_type), start_pos, end_pos)
    
    def _readCharAsInt(self) -> tuple[int, bool]:
        "Reads a character or escape sequence and returns its numerical value (may exceed 255 because unicode and hex is supported.)"
        char = self._peek()
        if char == "": self._fatal(Lexer.L_EOF, f"{self._snapshot()}: expected character, got EOF.")
        if char == "\\":
            pos = self._snapshot()
            self._advance()
            if char == "": self._fatal(Lexer.L_EOF, f"{self._snapshot()}: expected character, got EOF.")
            char = self._peek()
            large_peek = self._peek(10)
            self._advance()
            if   char == "a": return ord('\a'), True
            elif char == "b": return ord('\b'), True
            elif char == "f": return ord("\f"), True
            elif char == "n": return ord("\n"), True
            elif char == "r": return ord("\r"), True
            elif char == "t": return ord("\t"), True
            elif char == "v": return ord("\v"), True
            elif char == "\\": return ord('\\'), True
            elif char == "'": return ord("'"), True
            elif char == '"': return ord('"'), True
            elif char == "0": return 0, True
            elif (m := re.match(r"^([0-7]{1,3})", large_peek)):
                self._advance(len(m.group())-1)
                return int(m.group(1), base=8) % 0x100, True
            elif (m := re.match(r"^x([0-9a-fA-F]{1,8})", large_peek)):
                self._advance(len(m.group())-1)
                if re.match(r"[0-9A-Za-f]", self._peek()):
                    self.logger.warn(f"{pos}: hexadecimal escape sequence '\\{m.group()}' read successfully, but is followed by more hexadecimal characters over the 8 character limit at {self._snapshot()}.")
                return int(m.group(1), base=16), True
            elif (m := re.match(r"^u([0-9a-fA-F]{4})", large_peek)):
                self._advance(len(m.group())-1)
                val = int(m.group(1), base=16)
                try:
                    val = int.from_bytes(bytes(chr(val), encoding="utf8"), "big")
                except ValueError:
                    self._fatal(Lexer.L_INVALIDUNICODECHAR, f"{pos}: invalid unicode literal '\\{m.group()}'")
                return val, False
            elif (m := re.match(r"^u([0-9a-fA-F]{8})", self._peek(9))):
                self._advance(len(m.group())-1)
                val = int(m.group(1), base=16)
                try:
                    val = int.from_bytes(bytes(chr(val), encoding="utf8"), "big")
                except ValueError:
                    self._fatal(Lexer.L_INVALIDUNICODECHAR, f"{pos}: invalid unicode literal '\\{m.group()}'")
                return val, False
            else:
                self.logger.warn(f"{pos}: escape character '\\' used in literal has no effect and only '{char}' will remain. did you mean to escape the backslash?")
        else:
            self._advance()
        return int.from_bytes(bytes(char, encoding="utf8"), "big"), False
    
    def _readIntSuffix(self) -> tuple[str, int, tuple[int, int] | None]:
        """
        Reads a numeric literal's base suffix.
        
        Accepts i, l, q.
        """
        pos = None
        int_type = "int"
        if (peek := self._peek()) and peek.isalpha():
            peek = peek.lower()
            if   peek == "i": int_type = "int"
            elif peek == "l": int_type = "long"
            elif peek == "q": int_type = "quad"
            else: self._fatal(Lexer.L_INVALIDINTSUFFIX, f"{pos}: invalid numeric literal base suffix '{peek}'")
            pos = self._snapshot()
            self._advance()
        maximum = 1 << nstypes.CFG.INT_SIZES[int_type] * nstypes.CFG.BITS_PER_WORD
        return int_type, maximum, pos
    
    def _readString(self) -> Token:
        """
        Reads a string from source.
        
        Adjacent strings are concatenated and a null-terminator is added at the end.
        """
        start_pos = end_pos = self._snapshot()
        
        if self._peek() != '"':
            self._fatal(Lexer.L_UNKNOWN, f"{start_pos}: expected start of string, but did not get opening double quote.")
        
        def int_to_smallest_bytes(val: int) -> bytes:
            from math import ceil, log
            length = ceil(log(val)/log(256))
            return val.to_bytes(length, "big")
        
        string = []
        while self._peek() == '"':
            # Discard opening double quote
            self._advance()
            
            while self._peek() != '"':
                char_pos = self._snapshot()
                char_int, not_unicode = self._readCharAsInt()
                if not_unicode and char_int > 127:
                    self._fatal(Lexer.L_INVALIDSTRINGCHAR, f"{char_pos}: non UTF-8 character in string has value '{char_int}' which is outside the allowed non-unicode range (0-127).")
                string.extend(int_to_smallest_bytes(char_int))
            
            end_pos = self._snapshot()
            
            # Discard closing double quote
            self._advance()
            
            # Skip whitespace between adjacent quotes for concatenation
            self._skipws()
        
        # Add null terminator
        string.append(0)
        
        return Token(TokenType.STRING, string, start_pos, end_pos)
    
    def _tryReadPunc(self) -> Token | None:
        start_pos = self._snapshot()
        
        # Try matching any punctuator
        punct_matches = []
        for punct in Punctuators:
            if punct == self._peek(len(punct)):
                punct_matches.append(punct)
        
        # Return None if no punctuators matched
        if len(punct_matches) == 0: return None
        
        # Sort to get the biggest matching operator greedily
        list.sort(punct_matches, key = lambda punct: len(punct), reverse=True)
        punct = punct_matches[0]
        
        # Read through punctuator
        self._advance(len(punct)-1)
        end_pos = self._snapshot()
        self._advance()
        
        return Token(TokenType.PUNC, punct, start_pos, end_pos)
    
    def _tryReadKeywordOrName(self) -> Token | None:
        start_pos = self._snapshot()
        
        # Return None if name does not start with an underscore or ASCII letter
        if (peek := self._peek()) and not (peek == "_" or peek.isalpha() and peek.isascii()):
            return None
        
        # Read name
        name = ""
        while (peek := self._peek()) and (peek == "_" or peek.isalnum() and peek.isascii()):
            name += peek
            end_pos = self._snapshot()
            self._advance()
        
        # Check for keyword
        if name in Keywords:
            return Token(TokenType.KEYWORD, name, start_pos, end_pos)
        else:
            return Token(TokenType.NAME, name, start_pos, end_pos)