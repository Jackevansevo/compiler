import os
from glob import glob
from compiler.compile import make_ast
from compiler.parse import parse_ast
from compiler.tac import build_tac


def fname(f):
    fname, ext = os.path.splitext(f)
    return fname


def test_examples():
    for src in glob('examples/*.cmm'):
        # Check if matching tac file exists
        tac_file_name = fname(src) + '.tac'
        if os.path.isfile(tac_file_name):
            with open(src) as src_file, open(tac_file_name) as tac_file:
                head = parse_ast(make_ast(src_file))
                tac_strings = list(map(str, build_tac(head)))
                expected = [line.strip() for line in tac_file.readlines()]
                assert tac_strings == expected
