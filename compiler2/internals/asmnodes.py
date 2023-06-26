from __future__ import annotations

"""
Implementation of the nodes use to represent a program just above assembly level.
"""

REGISTERS = "ABCDEGMLXYSPUVFZ"
FLAGS = "NCOI-TSZ"

###################

class Statement:
    def __init__(self):
        self.comment = ""
        
    def add_comment(self, text: str):
        if len(self.comment.strip()) == 0:
            return text
        
        if len(text.strip()) == 0:
            return "\t\t; " + self.comment
        
        return text + " ; " + self.comment
        
class Operand: pass

###################

class LabelStatement(Statement):
    def __init__(self, label: str):
        super().__init__()
        self.label = label
        
    def __str__(self):
        same_line = ""
        if len(self.comment.strip()) > 0: same_line = "\n"
        if len(self.label) > 2: same_line = "\n"
        
        return self.add_comment(self.label + ":") + same_line

class OpStatement(Statement):
    def __init__(self, opcode: str):
        super().__init__()
        self.opcode = opcode
        self.operands: list['Operand'] = []
        
    def __str__(self):
        return self.add_comment("\t" + self.opcode + " " + ", ".join([str(x) for x in self.operands])) + "\n"

class PreprocDirective(Statement):
    def __init__(self, directive: str):
        super().__init__()
        self.directive = directive
        
    def __str__(self):
        return self.directive + "\n"

class Directive(Statement):
    def __init__(self, directive: str):
        super().__init__()
        self.directive = directive
        self.operands: list['Operand'] = []
        
    def __str__(self):
        return self.add_comment("\t" + self.directive + " " + ", ".join([str(x) for x in self.operands])) + "\n"

class LabelOperand(Operand):
    def __init__(self, label: str):
        self.label = label
    
    def __str__(self):
        return self.label

class ImmOperand(Operand):
    def __init__(self, num: int, is32bit: bool = False):
        self.num = num
        self.is32bit = is32bit
        
    def __str__(self):
        num = self.num & (0xFFFFFFFF if self.is32bit else 0xFFFF)
        return f"{num:X}h"

class StrOperand(Operand):
    def __init__(self, bytes: list[int] = []):
        self.bytes = list(bytes)
    
    def __str__(self):
        return '"' + "".join([chr(x) for x in self.bytes]) + '"'

class RegisterOperand(Operand):
    def __init__(self, register: str = "Z", is32bit: bool = False):
        self.register = register
        self.is32bit = is32bit
    
    def __str__(self):
        REG_LO = self.register
        REG_HI = REGISTERS[REGISTERS.find(self.register) ^ 1]
        reg = REG_HI + REG_LO if self.is32bit else REG_LO
        return "%" + reg

class MemoryOperand(Operand):
    def __init__(self, reg: 'RegisterOperand', imm: 'ImmOperand | LabelOperand | None'):
        self.reg = reg
        self.imm = imm
        
    def __str__(self):
        if self.imm:
            return f"$({self.reg}+{self.imm})"
        else:
            return f"$({self.reg})"

class Space(Statement):
    def __str__(self):
        return self.add_comment("\t") + "\n"