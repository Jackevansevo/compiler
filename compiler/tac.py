import sys
from compiler.parse import Token
from itertools import count
from operator import add, eq, floordiv, ge, gt, le, lt, mod, mul, ne, sub
from typing import List

# [TODO] Fix for the factorial example
# [TODO] Implement if else statements

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
    elif isinstance(lexeme, str):
        return Token(lexeme)
    elif isinstance(lexeme, int):
        return Token(str(lexeme))


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
        elif self.rhs.is_identifier:
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
        elif self.rhs.is_identifier and self.lhs.val == 2:
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
            # Create a frame of fixed size
            "li $a0, 48",
            # Load the sbrk syscall
            "li $v0, 9",
            "syscall",
            "sw $fp, 0($v0)",
            # Move old frame pointer to new framepointer
            "move $fp, $v0",
            # Record return address
            "sw $ra, 4($v0)"
        ]

    def __str__(self) -> str:
        return f'func {self.label}'


class TacParamCount(TacInstruction):

    def __init__(self, count):
        self.count = count

    def to_mips(self, _) -> List[str]:
        return [
            '# Increment stack pointer by the number of args',
            f'addi $sp, $sp {self.count.val * 4}'
        ]

    def __str__(self) -> str:
        return f'params {self.count}'


class TacEndFunc(TacInstruction):

    def __init__(self, label):
        self.label = label

    def to_mips(self, _) -> List[str]:
        return [f'nop']

    def __str__(self) -> str:
        return f'endfunc'


class TacParam(TacInstruction):

    def __init__(self, ptype, pname):
        self.ptype = ptype
        self.pname = pname

    def to_mips(self, data):
        # Assign arguments
        arg = data.get_next_register(data.arguments)
        data[self.pname.lexeme] = arg
        return [
            '# Count down each time',
            'addi $sp, $sp, -4',
            f'lw, {arg.to_mips}, 0($sp)',
        ]

    def __str__(self) -> str:
        return f'param {self.ptype} {self.pname}'


class TacCall(TacInstruction):

    def __init__(self, reg, label):
        self.reg = reg
        self.label = label

    def to_mips(self, data):
        temp = data.get_next_register(data.temporaries)
        data[self.reg.lexeme] = temp
        return [
            f'jal {self.label}',
            f'lw $fp, 0($fp)',
            f'lw $ra, 4($fp)',
            f'move {temp.to_mips}, $v1'
        ]

    def __str__(self) -> str:
        return f'{self.reg} := call {self.label}'


class TacReturn(TacInstruction):

    def __init__(self, lhs):
        self.lhs = lhs

    def to_mips(self, data):
        if self.lhs.is_constant:
            return [
                f'li $v1, {self.lhs.to_mips}',
                f'jr $ra'
            ]
        lhs = data.allocate_register(self.lhs)
        return [
            f'move $v1, {lhs.to_mips}',
            f'jr $ra'
        ]

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
        lhs = data.allocate_register(self.pred)
        return [f"beqz {lhs.to_mips}, {self.label}"]

    def __str__(self) -> str:
        return f'!if {self.pred} goto {self.label}'


class TacPrint(TacInstruction):

    def __init__(self, lhs):
        self.lhs = lhs

    def to_mips(self, data) -> List[str]:
        reg = data.allocate_register(self.lhs)
        load, *_ = data.mips_assign(Token('$a0'), reg)
        return [
            load,
            "li $v0, 1",
            "syscall",
            "addi $a0, $0, 0xA",
            "addi $v0, $0, 0xB",
            "syscall",
        ]

    def __str__(self) -> str:
        return f'print {self.lhs}'


class TacOperation(TacInstruction):

    def __init__(self, reg, op, lhs, rhs):
        self.reg = reg
        self.op = op
        self.lhs = lhs
        self.rhs = rhs

    def to_mips(self, data) -> List[str]:
        op = mips_operators[self.op.lexeme]
        lhs, lhs_assingment = data.resolve_mapping(self.lhs)
        rhs, rhs_assingment = data.resolve_mapping(self.rhs)
        temp = data.assign_temp(self.reg)
        operation = f'{op} {temp.to_mips}, {lhs.to_mips}, {rhs.to_mips}'
        return list(filter(None, [lhs_assingment, rhs_assingment, operation]))

    def __str__(self) -> str:
        return f'{self.reg} = {self.lhs} {self.op} {self.rhs}'


class TacAssingment(TacInstruction):

    def __init__(self, lhs, rhs):
        self.lhs = lhs
        self.rhs = rhs

    def to_mips(self, data) -> List[str]:
        return data.mips_assign(
            data.allocate_register(self.lhs),
            data.allocate_register(self.rhs)
        )

    def __str__(self) -> str:
        return f'{self.lhs} := {self.rhs}'


class TacArg(TacInstruction):

    def __init__(self, arg):
        self.arg = arg

    def to_mips(self, data):
        if self.arg.lexeme in data._mappings:
            reg = data[self.arg.lexeme]
            return [
                'addi $sp, $sp, -4',
                f'sw {reg.to_mips}, 0($sp)'
            ]
        else:
            reg = data.allocate_register(self.arg)
            return [
                f'li ${reg}, {self.arg.to_mips}',
                'addi $sp, $sp, -4',
                f'sw ${reg}, 0($sp)'
            ]

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


def check_if_defined(tac_list, func_name, tac_type):
    # Find matching Tac instructions
    matches = (t for t in tac_list if isinstance(t, tac_type))
    if tac_type == TacStartFunc:
        fn_names = (fn.label.lexeme for fn in matches)
        return func_name in fn_names


def interpret_operator(node, data):
    temp = data.get_temp()
    rhs = recursive_build_tac(node.rhs, data)
    lhs = recursive_build_tac(node.lhs, data)
    data.tac_list.append(TacOperation(temp, node.tok, lhs, rhs))
    return temp


def interpret_function(node, data):
    func_name = node.lhs.rhs.lhs.tok.lexeme
    data.tac_list.append(TacStartFunc(func_name))

    params = node.func_params

    if params:
        data.tac_list.append(TacParamCount(len(params)))
        for param in params:
            data.tac_list.append(TacParam(param.type, param.name))

    recursive_build_tac(node.lhs, data)
    rhs = recursive_build_tac(node.rhs, data)
    data.tac_list.append(TacEndFunc(func_name))
    return rhs


def interpret_apply(node, data):
    if node.lhs.tok.lexeme == "print":
        rhs = recursive_build_tac(node.rhs, data)
        data.tac_list.append(TacPrint(rhs))
        return rhs
    else:
        if node.rhs is not None:
            func_args = list(node.rhs.func_args)
            for arg in func_args:
                val = recursive_build_tac(arg, data)
                data.tac_list.append(TacArg(val))
        temp = data.get_temp()
        func_name = node.lhs.tok.lexeme
        # Check if the function is undefined
        if not check_if_defined(data.tac_list, func_name, TacStartFunc):
            sys.exit(f"Error: Function '{func_name}' undefined")
        data.tac_list.append(TacCall(temp, func_name))
        return temp


def interpret_if(node, data):
    label = next(data.labels)
    pred = recursive_build_tac(node.lhs, data)
    data.tac_list.append(TacIfStatement(pred.lexeme, label))

    recursive_build_tac(node.rhs, data)

    instruction = TacLabel(label)
    data.tac_list.append(instruction)
    temp = data.get_temp()
    return temp


def interpret_assignment(node, data):
    rhs = recursive_build_tac(node.rhs, data)
    data.tac_list.append(TacAssingment(node.lhs.tok, rhs))
    return rhs


def recursive_build_tac(node, data):

    if node.tok.lexeme == "return":
        lhs = recursive_build_tac(node.lhs, data)
        data.tac_list.append(TacReturn(lhs))
        return lhs

    elif node.tok.lexeme in operators.keys():
        return interpret_operator(node, data)

    elif node.tok.lexeme == "D":
        return interpret_function(node, data)

    elif node.tok.lexeme == "apply":
        return interpret_apply(node, data)

    elif node.tok.lexeme == "if":
        return interpret_if(node, data)

    elif node.tok.lexeme == "=":
        return interpret_assignment(node, data)

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
