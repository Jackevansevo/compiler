import re
from compiler.compile import make_ast
from compiler.mips import build_mips
from compiler.parse import parse_ast
from compiler.tac import build_tac
from glob import glob
from subprocess import PIPE, run
from tempfile import NamedTemporaryFile

import pytest

HEADER_REGEX = re.compile(r"\/\*\s*(Answer|Error):\s*(.*)\s*\*\/")


def check_mips(fname, expected, instructions):

    __tracebackhide__ = True

    with NamedTemporaryFile() as temp:

        # Write the mips instructions to a temporary file
        temp.write("\n".join(instructions).encode('utf-8'))

        # Reset file pointer (for reading)
        temp.seek(0)

        # Execute the temporary machine instructions
        cmd = f"spim load {temp.name}"
        out = run(cmd, shell=True, stdout=PIPE, stderr=PIPE, check=True)

        # Fail if stderr has been written to
        if out.stderr:
            stderr = out.stderr.decode('utf-8').strip()
            pytest.fail(f'{fname} Error: \n{stderr}')

        # Else check if the content of stdout is correct
        program_output = out.stdout.decode('utf-8').strip().splitlines()
        result = program_output[-1]
        if result != expected.strip():
            pytest.fail(f'{fname}\nExpected: {expected}\nGot: {result}')


def test_examples():
    for src in glob('examples/*.cmm'):
        with open(src) as src_file:
            head = src_file.readline().strip()
            match = HEADER_REGEX.match(head)
            if match:
                src_file.seek(0)
                category, expected = match.groups()
                mips = build_mips(build_tac(parse_ast(make_ast(src_file))))
                check_mips(src_file.name, expected, mips)
