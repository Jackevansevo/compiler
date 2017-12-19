from operator import attrgetter
from collections import namedtuple

Param = namedtuple('Param', ['type', 'name'])


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
