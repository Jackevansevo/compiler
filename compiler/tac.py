import sys
from typing import List
from itertools import count, chain
from operator import add, eq, floordiv, ge, gt, le, lt, mod, mul, ne, sub
from compiler.parse import Token


tac_optimizations = []

operators = {
    '+': add, '-': sub, '*': mul, '%': mod, '/': floordiv,
    '==': eq, '!=': ne, '>': gt, '<': lt, '>=': ge, '<=': le
}

mips_operators = {
    '+': 'add', '*': 'mul', '-': 'sub', '%': 'rem', '/': 'div', '==': 'seq',
    '!=': 'sne', '>': 'sgt', '>=': 'sge', '<': 'slt', '<=': 'sle',
}


def optimization(optimization_func):
    tac_optimizations.append(optimization_func)
    return optimization_func


def tokenize(lexeme):
    """Converts a string to a Token"""
    if isinstance(lexeme, Token):
        return lexeme
    if isinstance(lexeme, str):
        return Token(lexeme)
    if isinstance(lexeme, int):
        return Token(str(lexeme))
    return None


class TacInstruction:

    def __setattr__(self, name, value):
        value = tokenize(value)
        super().__setattr__(name, value)

    @property
    def is_assingment(self):
        return self.op.lexeme == '=' and self.lhs.is_identifier

    @property
    def has_branches(self):
        return self.lhs and self.rhs

    @optimization
    def transform_algebra(self):
        if self.lhs.is_identifier:
            # x + 0 -> x
            if self.rhs.val == 0 and self.op.lexeme in {'+', '-'}:
                self.rhs, self.lhs = self.lhs, self.reg
                self.reg, self.op = None, '='
                return True
            # // x * 1 -> x or  x / 1 -> x
            if self.rhs.val == 1 and self.op.lexeme in {'*', '/'}:
                self.rhs, self.lhs = self.lhs, self.reg
                self.reg, self.op = None, '='
                return True
        if self.rhs.is_identifier:
            # // 1 * x -> x
            if self.lhs.val == 1 and self.op.lexeme == '*':
                self.lhs, self.reg, self.op = self.reg, None, '='
                return True
        return False

    @optimization
    def fold_constants(self):
        if self.lhs.is_constant and self.rhs.is_constant:
            if self.op.lexeme in operators.keys():
                lhs, rhs, reg = self.lhs.val, self.rhs.val, self.reg
                result = operators.get(self.op.lexeme)(lhs, rhs)
                if isinstance(result, bool):
                    result = int(result)
                self.lhs, self.rhs, self.reg, self.op = reg, result, None, '='
                return True
        return False

    @optimization
    def strength_reduce(self):
        # x * 2 -> x + x
        if self.lhs.is_identifier and self.rhs.val == 2:
            if self.op.lexeme == "*":
                self.op, self.rhs = '+', self.lhs
                return True
        # 2 * x -> x + x
        if self.rhs.is_identifier and self.lhs.val == 2:
            if self.op.lexeme == '*':
                self.op, self.lhs = '+', self.rhs
                return True
        return False

    def optimize(self):
        if isinstance(self, TacOperation):
            return any(map(lambda func: func(self), tac_optimizations))


class TacStartFunc(TacInstruction):

    def __init__(self, label):
        self.label = label

    def to_mips(self, _) -> List[str]:
        return [
            f"{self.label.lexeme}:",
            # Create a frame
            "li $a0, 48",
            # Load the sbrk syscall
            "li $v0, 9",
            "syscall",
            "sw $fp, 4($v0)",
            # Move old frame pointer to new framepointer
            "move $fp, $v0",
            # Record return address
            "sw $ra, 12($v0)"
        ]

    def __str__(self) -> str:
        return f'func {self.label}'


class TacEndFunc(TacInstruction):

    def __init__(self, label):
        self.label = label

    def to_mips(self, _) -> List[str]:
        return [f'jr $ra']

    def __str__(self) -> str:
        return f'endfunc'


class TacParam(TacInstruction):

    def __init__(self, ptype, pname):
        self.ptype = ptype
        self.pname = pname

    def to_mips(self, _):
        raise NotImplementedError("fucked mate")

    def __str__(self) -> str:
        return f'param {self.ptype} {self.pname}'


class TacCall(TacInstruction):

    def __init__(self, reg, label):
        self.reg = reg
        self.label = label

    def to_mips(self, data):
        temp = data.get_temp()
        data.mappings[self.reg.lexeme] = temp
        return [
            f'jal {self.label}',
            f'lw $fp, 4($fp)',
            f'lw $ra, 12($fp)',
            f'move {temp.to_mips}, $v1'
        ]

    def __str__(self) -> str:
        return f'{self.reg} := call {self.label}'


class TacReturn(TacInstruction):

    def __init__(self, lhs):
        self.lhs = lhs

    def to_mips(self, data):
        if self.lhs.is_constant:
            return [f'li $v1, {self.lhs.to_mips}']
        lhs = data.lookup_mapping(self.lhs)
        return [f'move $v1, {lhs.to_mips}']

    def __str__(self) -> str:
        return f'return {self.lhs}'


class TacLabel(TacInstruction):
    def __init__(self, label):
        self.label = label

    def to_mips(self, _) -> List[str]:
        return [f'{self.label}:']

    def __str__(self) -> str:
        return self.label.lexeme


class TacIfStatement(TacInstruction):

    def __init__(self, pred, label):
        self.pred = pred
        self.label = label

    def to_mips(self, data) -> List[str]:
        lhs = data.lookup_mapping(self.pred)
        return [f"beqz {lhs.to_mips}, {self.label}"]

    def __str__(self) -> str:
        return f'!if {self.pred} goto {self.label}'


class TacPrint(TacInstruction):
    def __init__(self, lhs):
        self.lhs = lhs

    def mips_print(self, reg):
        return [
            "# Load print integer syscall",
            "li $v0, 1",
            f"# Move {reg.to_mips} into $a0 (print integer argument)",
            f"move $a0, {reg.to_mips}",
            "syscall",
            "# Print a newline",
            "addi $a0, $0, 0xA",
            "addi $v0, $0, 0xB",
            "syscall",
        ]

    def to_mips(self, data) -> List[str]:
        temp, instruction = data.alloc_temp(self.lhs)
        return list(chain(instruction, self.mips_print(temp)))

    def __str__(self) -> str:
        return f'print {self.lhs}'


class TacOperation(TacInstruction):
    def __init__(self, reg, op, lhs, rhs):
        self.reg = reg
        self.op = op
        self.lhs = lhs
        self.rhs = rhs

    def to_mips(self, data) -> List[str]:
        instruction = mips_operators[self.op.lexeme]
        lhs, lhs_instruction = data.alloc_temp(self.lhs)
        rhs, rhs_instruction = data.alloc_temp(self.rhs)
        # Put the result in a new temporary
        temp = data.get_temp()
        data.mappings[self.reg.lexeme] = temp
        return list(chain(
            lhs_instruction,
            rhs_instruction,
            [f"{instruction} {temp.to_mips}, {lhs.to_mips}, {rhs.to_mips}"]
        ))

    def __str__(self) -> str:
        return f'{self.reg} = {self.lhs} {self.op} {self.rhs}'


class TacAssingment(TacInstruction):
    def __init__(self, lhs, rhs):
        self.lhs = lhs
        self.rhs = rhs

    def to_mips(self, data) -> List[str]:
        # [TODO] Correctly handle identifiers
        # if self.lhs.is_identifier:
        #     register = data.get_saved()
        #     data.mappings[self.lhs.lexeme] = register
        #     if self.rhs.is_constant:
        #         return [
        #             f"li {register.to_mips}, {self.rhs.to_mips}"
        #         ]
        #     lhs = data.mappings[self.rhs.lexeme]
        #     return [f"move {register.to_mips}, {lhs.to_mips}"]
        # else:
        temp = data.get_temp()
        data.mappings[self.lhs.lexeme] = temp
        if self.rhs.is_constant:
            return [
                f"li {temp.to_mips}, {self.rhs.to_mips}"
            ]
        lhs = data.mappings[self.rhs.lexeme]
        return [f"move {temp.to_mips}, {lhs.to_mips}"]

    def __str__(self) -> str:
        return f'{self.lhs} := {self.rhs}'


class TacArg(TacInstruction):
    def __init__(self, arg):
        self.arg = arg

    def to_mips(self, _):
        pass

    def __str__(self) -> str:
        return f'arg {self.arg}'


class TacData:

    def __init__(self):
        self.temporaries = (Token(f't{x}') for x in count(0))
        self.labels = (Token(f'L{x}') for x in count(0))
        self.tac_list = []  # type: list

    def get_temp(self):
        try:
            register = next(iter(self.temporaries))
        except StopIteration:
            sys.exit("Ran out of temporaries")
        else:
            return register


def build_tac(node):
    data = TacData()
    recursive_build_tac(node, data)
    return data.tac_list


def recursive_build_tac(node, data):

    if node.tok.lexeme == "return":
        lhs = recursive_build_tac(node.lhs, data)
        data.tac_list.append(TacReturn(lhs))
        return lhs

    elif node.tok.lexeme in operators.keys():
        temp = data.get_temp()
        rhs = recursive_build_tac(node.rhs, data)
        lhs = recursive_build_tac(node.lhs, data)
        data.tac_list.append(TacOperation(temp, node.tok, lhs, rhs))
        return temp

    elif node.tok.lexeme == "D":
        func_name = node.lhs.rhs.lhs.tok.lexeme
        data.tac_list.append(TacStartFunc(func_name))

        params = node.func_params
        if params:
            for param in params:
                data.tac_list.append(TacParam(param.type, param.name))

        recursive_build_tac(node.lhs, data)
        rhs = recursive_build_tac(node.rhs, data)
        data.tac_list.append(TacEndFunc(func_name))
        return rhs

    elif node.tok.lexeme == "apply":
        if node.lhs.tok.lexeme == "print":
            rhs = recursive_build_tac(node.rhs, data)
            data.tac_list.append(TacPrint(rhs))
            return rhs
        else:
            if node.rhs is not None:
                func_args = list(node.rhs.func_args)
                for arg in func_args:
                    data.tac_list.append(TacArg(arg.tok.lexeme))
            temp = data.get_temp()
            func_name = node.lhs.tok.lexeme
            data.tac_list.append(TacCall(temp, func_name))
            return temp

    elif node.tok.lexeme == "if":

        # [TODO] Implement if else statements

        label = next(data.labels)
        pred = recursive_build_tac(node.lhs, data)
        data.tac_list.append(TacIfStatement(pred.lexeme, label))

        recursive_build_tac(node.rhs, data)

        instruction = TacLabel(label)
        data.tac_list.append(instruction)
        temp = data.get_temp()
        return temp

    elif node.tok.lexeme == "=":
        rhs = recursive_build_tac(node.rhs, data)
        data.tac_list.append(TacAssingment(node.lhs.tok, rhs))
        return rhs

    elif node.tok.lexeme == "d":
        recursive_build_tac(node.rhs, data)
        temp = data.get_temp()
        return temp

    elif node.is_leaf:
        return node.tok
    else:
        recursive_build_tac(node.lhs, data)
        recursive_build_tac(node.rhs, data)
        temp = data.get_temp()
        return temp
