from re import match
from collections import namedtuple
from itertools import chain, islice, repeat

from operator import attrgetter

Param = namedtuple('Param', ['type', 'name'])


class Token:

    def __init__(self, lexeme):
        self.lexeme = lexeme

    @property
    def val(self):
        if self.lexeme.isdigit():
            return int(self.lexeme)
        return None

    def is_register(self):
        return match("(t|d)\d+", self.lexeme)

    @property
    def is_temporary(self):
        return match("t\d+", self.lexeme)

    @property
    def is_saved(self):
        return match("s\d+", self.lexeme)

    @property
    def is_identifier(self):
        return self.lexeme.isalpha()

    @property
    def is_constant(self):
        return self.lexeme.isdigit()

    @property
    def to_mips(self):
        if self.is_temporary or self.is_saved:
            return f'${self.lexeme}'
        return str(self)

    def __repr__(self):
        return f'<Token(lexeme={repr(self.lexeme)})>'

    def __str__(self):
        return self.lexeme


class Node:

    @property
    def func_params(self):
        if not self.lhs.rhs.rhs:
            return None
        signature = self.lhs.rhs.rhs
        leaf_nodes = filter(attrgetter('is_leaf'), iter(signature))
        param_nodes = [leaf.tok.lexeme for leaf in leaf_nodes]
        return [Param(*p) for p in zip(param_nodes[::2], param_nodes[1::2])]

    @property
    def func_args(self):
        if self.tok.lexeme == ",":
            yield from self.lhs.func_args
            yield from self.rhs.func_args
        else:
            yield self

    @property
    def is_leaf(self):
        return not all([self.lhs, self.rhs])

    def __str__(self):
        return str(self.tok)

    def __repr__(self):
        return f'<Node(tok={self.tok})>'

    def __iter__(self):
        if self.lhs:
            yield from self.lhs
        yield self
        if self.rhs:
            yield from self.rhs


def parse_ast(ast):
    AstLine = namedtuple('AstLine', ['id', 'indent', 'tok'])
    ast_lines = []

    for index, line in enumerate(ast):
        tok = line.lstrip()
        indent = len(line) - len(tok)
        ast_lines.append(AstLine(index, indent, tok))

    return parse(ast_lines)


def get_next_indented(nodes, head):
    next_indent = head.indent + 2
    for node in nodes:
        if node.indent == next_indent:
            yield node


def parse(nodes):

    head, *rest = nodes
    node = Node()

    node.tok = Token(head.tok)

    children = get_next_indented(rest, head)

    lhs, rhs = islice(chain(children, repeat(None)), 2)

    if lhs:
        if rhs:
            node.lhs = parse(rest[:rest.index(rhs)])
        else:
            node.lhs = parse(rest[:len(nodes)])
    else:
        node.lhs = None

    if rhs:
        node.rhs = parse(rest[rest.index(rhs):])
    else:
        node.rhs = None

    return node
