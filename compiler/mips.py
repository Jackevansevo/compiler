import sys
from compiler.parse import Token
from typing import List, Union

# [TODO]
# Reset the stack pointer at the end of a function
# Evaluate arguments before passing to functions
# Generic move register function


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
        return self._mappings[key]

    def get_next_register(self, pool) -> Token:
        try:
            register = next(iter(pool))
        except StopIteration:
            sys.exit("Ran out of registers")
        else:
            return register

    def get_temp(self) -> Token:
        return self.get_next_register(self.temporaries)

    def get_saved(self) -> Token:
        return self.get_next_register(self.saved)

    def get_arg(self) -> Token:
        return self.get_next_register(self.arguments)

    def lookup_mapping(self, tok) -> Token:
        if tok.is_constant:
            return tok
        return self.mappings.get(tok.lexeme)

    def allocate_register(self, tok) -> Token:
        if tok.is_identifier:
            return self.get_saved()
        else:
            return self.get_temp()

    def alloc_temp(self, tok) -> Union[Token, str]:
        val = self.lookup_mapping(tok)
        if val.is_register:
            return val, []
        else:
            temp = self.get_temp()
            self[val.lexeme] = temp
            return temp, [
                '# Fucking memes',
                f'li {temp.to_mips}, {val.to_mips}'
            ]


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
