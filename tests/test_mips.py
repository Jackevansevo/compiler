from glob import glob
from compiler.compile import make_ast
from compiler.parse import parse_ast
from compiler.tac import build_tac
from compiler.mips import build_mips


# def test_examples():
#     for src in glob('examples/*.cmm'):
#         with open(src) as src_file:
#             head = parse_ast(make_ast(src_file))
#             tac_list = []
#             build_tac(head, tac_list)
#             mips = build_mips(tac_list)
#             # [TODO] Actually call mips
