from re import match


class Token:

    def __init__(self, lexeme):
        self.lexeme = lexeme

    @property
    def val(self):
        if self.lexeme.isdigit():
            return int(self.lexeme)
        return None

    @property
    def is_register(self):
        return bool(match("(a|t|s)\d+", self.lexeme))

    @property
    def is_temporary(self):
        return match("t\d+", self.lexeme)

    @property
    def is_saved(self):
        return match("s\d+", self.lexeme)

    @property
    def is_arg(self):
        return match("a\d+", self.lexeme)

    @property
    def is_identifier(self):
        return self.lexeme.isalpha()

    @property
    def is_constant(self):
        return self.lexeme.isdigit()

    @property
    def to_mips(self):
        if self.is_register:
            return f'${self.lexeme}'
        return str(self)

    def __repr__(self):
        return f'<Token(lexeme={repr(self.lexeme)})>'

    def __str__(self):
        return self.lexeme
