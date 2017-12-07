import re
from compiler.compile import make_ast
from compiler.mips import build_mips
from compiler.parse import parse_ast
from compiler.tac import build_tac
from glob import glob
from subprocess import PIPE, run
from tempfile import NamedTemporaryFile

HEADER_REGEX = re.compile(r"\/\*\s*(Answer|Error):\s*(.*)\s*\*\/")


def check_mips(expected, instructions):
    with NamedTemporaryFile() as temp:
        temp.write("\n".join(instructions).encode('utf-8'))
        cmd = f"spim load {temp.name}"
        out = run(cmd, shell=True, stdout=PIPE, stderr=PIPE)
        if out.stderr:
            raise Exception(out.stderr.decode('utf-8').strip())
        else:
            output = out.stdout.decode('utf-8').strip()
            assert output.splitlines()[-1] == expected.strip()


def test_examples():
    for src in glob('examples/*.cmm'):
        with open(src) as src_file:
            head = src_file.readline().strip()
            match = HEADER_REGEX.match(head)
            if match:
                src_file.seek(0)
                category, expected = match.groups()
                mips = build_mips(build_tac(parse_ast(make_ast(src_file))))
                check_mips(expected, mips)
