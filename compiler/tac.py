import sys
from compiler.node import Node
from compiler.token import Token
from itertools import count
from operator import add, eq, floordiv, ge, gt, le, lt, mod, mul, ne, sub
from typing import List

from attr import attrib, attrs

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


@attrs
class TacStartFunc(TacInstruction):
    label = attrib()

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


@attrs
class TacParamCount(TacInstruction):
    count = attrib()

    def to_mips(self, _) -> List[str]:
        return [
            '# Increment stack pointer by the number of args',
            f'addi $sp, $sp {self.count.val * 4}'
        ]

    def __str__(self) -> str:
        return f'params {self.count}'


@attrs
class TacEndFunc(TacInstruction):
    label = attrib()

    def to_mips(self, _) -> List[str]:
        return [f'nop']

    def __str__(self) -> str:
        return f'endfunc'


@attrs
class TacParam(TacInstruction):

    ptype = attrib()
    pname = attrib()

    def to_mips(self, env):
        # Assign arguments
        arg = env.get_next_register(env.arguments)
        env[self.pname.lexeme] = arg
        return [
            '# Count down each time',
            'addi $sp, $sp, -4',
            f'lw, {arg.to_mips}, 0($sp)',
        ]

    def __str__(self) -> str:
        return f'param {self.ptype} {self.pname}'


@attrs
class TacCall(TacInstruction):
    reg = attrib()
    label = attrib()

    def to_mips(self, env):
        temp = env.get_next_register(env.temporaries)
        env[self.reg.lexeme] = temp
        return [
            f'jal {self.label}',
            f'lw $fp, 0($fp)',
            f'lw $ra, 4($fp)',
            f'move {temp.to_mips}, $v1'
        ]

    def __str__(self) -> str:
        return f'{self.reg} := call {self.label}'


@attrs
class TacReturn(TacInstruction):
    lhs = attrib()

    def to_mips(self, env):
        if self.lhs.is_constant:
            return [
                f'li $v1, {self.lhs.to_mips}',
                f'jr $ra'
            ]
        lhs = env.allocate_register(self.lhs)
        return [
            f'move $v1, {lhs.to_mips}',
            f'jr $ra'
        ]

    def __str__(self) -> str:
        return f'return {self.lhs}'


@attrs
class TacLabel(TacInstruction):
    label = attrib()

    def to_mips(self, _) -> List[str]:
        return [f'{self.label}:']

    def __str__(self) -> str:
        return self.label.lexeme


@attrs
class TacIfStatement(TacInstruction):
    pred = attrib()
    label = attrib()

    def to_mips(self, env) -> List[str]:
        pred = env.allocate_register(self.pred)
        return [f"beqz {pred.to_mips}, {self.label}"]

    def __str__(self) -> str:
        return f'!if {self.pred} goto {self.label}'


@attrs
class TacPrint(TacInstruction):
    lhs = attrib()

    def to_mips(self, env) -> List[str]:
        reg = env.allocate_register(self.lhs)
        load, *_ = env.mips_assign(Token('$a0'), reg)
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


@attrs
class TacOperation(TacInstruction):
    reg = attrib()
    op = attrib()
    lhs = attrib()
    rhs = attrib()

    def to_mips(self, env) -> List[str]:
        op = mips_operators[self.op.lexeme]
        lhs, lhs_assingment = env.resolve_mapping(self.lhs)
        rhs, rhs_assingment = env.resolve_mapping(self.rhs)
        temp = env.assign_temp(self.reg)
        operation = f'{op} {temp.to_mips}, {lhs.to_mips}, {rhs.to_mips}'
        return list(filter(None, [lhs_assingment, rhs_assingment, operation]))

    def __str__(self) -> str:
        return f'{self.reg} := {self.lhs} {self.op} {self.rhs}'


@attrs
class TacAssingment(TacInstruction):
    lhs = attrib()
    rhs = attrib()

    def to_mips(self, env) -> List[str]:
        return env.mips_assign(
            env.allocate_register(self.lhs),
            env.allocate_register(self.rhs)
        )

    def __str__(self) -> str:
        return f'{self.lhs} := {self.rhs}'


@attrs
class TacArg(TacInstruction):
    arg = attrib()

    def to_mips(self, env):
        if self.arg.lexeme in env._mappings:
            reg = env[self.arg.lexeme]
            return [
                'addi $sp, $sp, -4',
                f'sw {reg.to_mips}, 0($sp)'
            ]
        else:
            reg = env.assign_temp(self.arg)
            return [
                f'li {reg.to_mips}, {self.arg.to_mips}',
                'addi $sp, $sp, -4',
                f'sw ${reg}, 0($sp)'
            ]

    def __str__(self) -> str:
        return f'arg {self.arg}'


class TacEnv:

    def __init__(self):
        self.temporaries = (Token(f't{x}') for x in count(0))
        self.labels = (Token(f'L{x}') for x in count(0))
        self.tac_list = []  # type: list


def build_tac(node):
    environment = TacEnv()
    recursive_build_tac(node, environment)
    return environment.tac_list


def check_if_defined(tac_list, func_name, tac_type):
    # Find matching Tac instructions
    matches = (t for t in tac_list if isinstance(t, tac_type))
    if tac_type == TacStartFunc:
        fn_names = (fn.label.lexeme for fn in matches)
        return func_name in fn_names


def interpret_operator(node, env):
    lhs = recursive_build_tac(node.lhs, env)
    rhs = recursive_build_tac(node.rhs, env)
    temp = next(env.temporaries)
    env.tac_list.append(TacOperation(temp, node.tok, lhs, rhs))
    return temp


def interpret_function(node, env):
    func_name = node.lhs.rhs.lhs.tok.lexeme
    env.tac_list.append(TacStartFunc(func_name))

    params = node.func_params

    if params:
        env.tac_list.append(TacParamCount(len(params)))
        for param in params:
            env.tac_list.append(TacParam(param.type, param.name))

    recursive_build_tac(node.lhs, env)
    recursive_build_tac(node.rhs, env)
    env.tac_list.append(TacEndFunc(func_name))


def interpret_apply(node, env):
    if node.lhs.tok.lexeme == "print":
        rhs = recursive_build_tac(node.rhs, env)
        env.tac_list.append(TacPrint(rhs))
        return rhs
    else:
        if node.rhs is not None:
            func_args = list(node.rhs.func_args)
            for arg in func_args:
                val = recursive_build_tac(arg, env)
                env.tac_list.append(TacArg(val))
        temp = next(env.temporaries)
        func_name = node.lhs.tok.lexeme
        # Check if the function is undefined
        if not check_if_defined(env.tac_list, func_name, TacStartFunc):
            sys.exit(f"Error: Function '{func_name}' undefined")
        env.tac_list.append(TacCall(temp, func_name))
        return temp


def interpret_if(node, env):
    label = next(env.labels)
    pred = recursive_build_tac(node.lhs, env)
    env.tac_list.append(TacIfStatement(pred.lexeme, label))

    recursive_build_tac(node.rhs, env)

    instruction = TacLabel(label)
    env.tac_list.append(instruction)
    temp = next(env.temporaries)
    return temp


def interpret_assignment(node, env):
    rhs = recursive_build_tac(node.rhs, env)
    env.tac_list.append(TacAssingment(node.lhs.tok, rhs))
    return rhs


def interpret_return(node, env):
    lhs = recursive_build_tac(node.lhs, env)
    env.tac_list.append(TacReturn(lhs))
    return lhs


cases = {
    'return': interpret_return,
    'D': interpret_function,
    'apply': interpret_apply,
    'if': interpret_if,
    '=': interpret_assignment,
}


def recursive_build_tac(node: Node, env: TacEnv):
    interpret_case = cases.get(node.tok.lexeme)
    if interpret_case:
        return interpret_case(node, env)
    elif node.tok.lexeme in operators.keys():
        return interpret_operator(node, env)
    elif node.is_leaf:
        return node.tok
    else:
        recursive_build_tac(node.lhs, env)
        recursive_build_tac(node.rhs, env)
        temp = next(env.temporaries)
        return temp
