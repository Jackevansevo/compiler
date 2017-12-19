import sys
from compiler.token import Token
from typing import List, Union
from compiler.tac import TacInstruction


class MipsData:

    def __init__(self):
        self.temporaries = (Token(f't{x}') for x in range(9))
        self.saved = (Token(f's{x}') for x in range(7))
        self.arguments = (Token(f'a{x}') for x in range(4))
        self._mappings = {}

    @property
    def mappings(self):
        return self._mappings

    def get(self, value):
        return self._mappings.get(value)

    def __setitem__(self, key, val) -> None:
        self._mappings[key] = val

    def __getitem__(self, key) -> Token:
        try:
            val = self._mappings[key]
        except KeyError as val:
            sys.exit(f'Value {val} undefined')
        else:
            return val

    def get_next_register(self, pool) -> Token:
        try:
            register = next(iter(pool))
        except StopIteration:
            sys.exit('Ran out of registers')
        else:
            return register

    def mips_assign(self, dest, src) -> List[str]:
        cmd = 'li' if src.is_constant else 'move'
        return [f'{cmd} {dest.to_mips}, {src.to_mips}']

    def assign_temp(self, tok):
        temp = self.get_next_register(self.temporaries)
        self[tok.lexeme] = temp
        return temp

    def lookup_mapping(self, tok) -> Token:
        if tok.is_constant:
            return tok
        return self.get(tok.lexeme)

    def resolve_mapping(self, tok) -> Union[Token, str]:
        mapping = self.lookup_mapping(tok)
        if not mapping.is_register:
            temp = self.assign_temp(mapping)
            assingment, *_ = self.mips_assign(temp, tok)
            return temp, assingment
        return mapping, None

    def allocate_register(self, tok) -> Token:
        if tok.is_constant:
            return tok
        mapping = self.get(tok.lexeme)
        if mapping:
            return mapping
        elif tok.is_identifier:
            reg = self.get_next_register(self.saved)
        else:
            reg = self.get_next_register(self.temporaries)
        self._mappings[tok.lexeme] = reg
        return reg


def build_mips(tac_list: List[TacInstruction]) -> List[str]:

    prog_data = MipsData()
    instructions = []

    # Jump to main
    instructions.extend([
        "li $fp, 0",
        "jal main",
        "j end",
    ])

    # Convert all the tac instructions to MIPS
    for index, tac in enumerate(tac_list, 1):
        instructions.extend(tac.to_mips(prog_data))

    # Load and call the exit syscall
    instructions.extend([
        "end:",
        "# Exit the program",
        "li $v0, 10",
        "syscall"
    ])

    return instructions
