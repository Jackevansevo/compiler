import sys
from compiler.parse import Token
from typing import List, Union


class MipsData:

    def __init__(self):
        self.temporaries = (Token(f't{x}') for x in range(9))
        self.saved = (Token(f's{x}') for x in range(7))
        self.mappings = {}

    def allocate_register(self, tok):
        pass

    def get_temp(self):
        try:
            register = next(iter(self.temporaries))
        except StopIteration:
            sys.exit("Ran out of temporaries")
        else:
            return register

    def lookup_mapping(self, tok) -> Token:
        if tok.is_constant:
            return tok
        reg = self.mappings.get(tok.lexeme)
        if reg:
            return reg
        else:
            sys.exit(f'{tok.lexeme} Undefined')

    def get_saved(self):
        try:
            register = next(iter(self.saved))
        except StopIteration:
            sys.exit("Ran out of temporaries")
        else:
            return register

    def alloc_temp(self, tok) -> Union[Token, str]:
        reg = self.lookup_mapping(tok)
        if reg:
            # Token is already a temporary
            if reg.is_temporary:
                return reg, []
            else:
                temp = self.get_temp()
                self.mappings[reg.lexeme] = temp
                return temp, [f'li {temp.to_mips}, {reg.to_mips}']
        else:
            sys.exit(f'{tok.lexeme} Undefined')


def build_mips(tac_list) -> List[str]:

    prog_data = MipsData()
    instructions = []

    instructions.extend([
        "li $fp, 0",
        "jal main",
        "j end",
    ])

    for index, tac in enumerate(tac_list, 1):
        instructions.extend(tac.to_mips(prog_data))

    instructions.extend([
        "end:",
        "# Exit the program",
        "li $v0, 10",
        "syscall"
    ])

    return instructions
