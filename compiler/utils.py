from graphviz import Digraph


def line_count(f):
    """Returns the number of lines in a file"""
    for i, l in enumerate(f):
        pass
    return i + 1


def draw_graph(head):
    dot = Digraph(comment='AST')
    dot = build_graph(dot, head)
    dot.render('graph/ast.gv', view=True)


def build_graph(graph, node):
    node_id = str(id(node))
    graph.node(node_id, node.tok.lexeme)
    if node.lhs:
        graph = build_graph(graph, node.lhs)
        graph.edge(node_id, str(id(node.lhs)))
    if node.rhs:
        graph = build_graph(graph, node.rhs)
        graph.edge(node_id, str(id(node.rhs)))
    return graph
