import argparse
import stat
import sys
from compiler.mips import build_mips
from compiler.optimize import optimize_tac
from compiler.parse import parse_ast
from compiler.tac import build_tac
from compiler.utils import draw_graph, line_count
from os import chmod
from shutil import get_terminal_size
from subprocess import PIPE, STDOUT, run


def parse_args():
    parser = argparse.ArgumentParser(description='Interprets a script.')
    parser.add_argument('file', type=argparse.FileType('r'))
    parser.add_argument('-o', '--out', default="prog.out")
    parser.add_argument('--debug', action='store_true')
    parser.add_argument('--graph', action='store_true')
    parser.add_argument('--ast', action='store_true')
    parser.add_argument('--optimize', action='store_true')
    parser.add_argument('--tac-only', action='store_true')
    args = parser.parse_args()
    return args


def make_ast(f):

    cmd = f"./mycc < {f.name}"

    out = run(cmd, shell=True, check=True, stdout=PIPE, stderr=STDOUT)

    output = out.stdout.decode('utf-8')
    outlines = output.splitlines()

    if outlines[-1] == 'syntax error':
        # Exit if syntax error encountered
        sys.stdout.write(output)
        sys.exit(1)

    ast = outlines[line_count(f):]

    return ast


def main():

    args = parse_args()

    ast = make_ast(args.file)

    if args.ast:
        for line in ast:
            print(line)
        print("─" * get_terminal_size().columns)

    head = parse_ast(ast)

    if args.graph:
        draw_graph(head)

    tac_list = build_tac(head)

    if args.debug:
        print("─" * get_terminal_size().columns)
        print("TAC")
        print("─" * get_terminal_size().columns)
        for instruction in tac_list:
            print(instruction)

    if args.optimize:
        tac_list = optimize_tac(tac_list, args.debug)

    if args.debug:
        print("─" * get_terminal_size().columns)
        print("MIPS")
        print("─" * get_terminal_size().columns)

    if args.tac_only:
        sys.exit()

    mips = build_mips(tac_list)

    leftcol = len(str(len(mips)))

    if args.debug:
        for lineno, instruction in enumerate(mips, 1):
            if ":" in instruction:
                print(str(lineno).ljust(leftcol), "│", instruction)
            else:
                print(str(lineno).ljust(leftcol), "│",  "\t", instruction)

    # Builds an executable file from mips instructions
    with open('templates/header.sh') as f:
        header = f.readlines()

    with open(args.out, 'w') as f:
        f.writelines(header)
        for line in mips:
            f.write(line + "\n")

    # Make the script executable
    chmod(args.out, stat.S_IRWXU)


if __name__ == '__main__':
    main()
