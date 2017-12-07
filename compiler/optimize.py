from operator import add, mod, mul, sub, truediv

from shutil import get_terminal_size

operators = {'+': add, '-': sub, '*': mul, '%': mod, '/': truediv}


def has_reads(target, tac_list):
    for index, tac in enumerate(tac_list):
        # If the next instruction is an assigment, as prior writes can be
        # eliminated
        if tac.is_assingment and tac.lhs.lexeme == target.lexeme:
            return False
        # Check if variable is read by subsequent instructions
        if tac.lhs and tac.lhs.lexeme == target.lexeme:
            return True
        if tac.rhs and tac.rhs.lexeme == target.lexeme:
            return True
    return False


def eliminate_dead_code(tac_list):
    """
    Given an instruction a := 5
    removes instruction if no subsequent reads can be found in tac_list

    Returns True if changes were made
    """
    # Mark indexes of lines for deletion
    marked = set()
    changed = False
    for index, tac in enumerate(tac_list[:-1], 1):
        if tac.op.lexeme == '=':
            if tac.lhs.is_temporary or tac.lhs.is_identifier:
                if not has_reads(tac.lhs, tac_list[index:]):
                    changed = True
                    marked.add(index)
    new_list = [t for i, t in enumerate(tac_list, 1) if i not in marked]
    return (new_list, changed)


def find_usages_until(target, until, tac_list):
    """
    Finds usages of a target variable until a subsequent write to another
    specified target
    """
    occurances = []
    for index, tac in enumerate(tac_list):
        if tac.is_assingment and tac.lhs.lexeme == until.lexeme:
            return occurances
        if tac.lhs and target.lexeme == tac.lhs.lexeme:
            occurances.append([index, 'lhs'])
        if tac.rhs and target.lexeme == tac.rhs.lexeme:
            occurances.append([index, 'rhs'])
    return occurances


def propagate_copies(tac_list):
    """
    Given: a := b
    replaces all subsequent occurrences of a with b until
    there is a write to b

    Returns True if changes were made
    """
    changed = False
    for index, instruction in enumerate(tac_list, 1):
        # Check if the instruction is a basic assignment
        if instruction.has_branches:
            # Check for subsequent usages in the TAC
            var, until = instruction.lhs, instruction.rhs
            usages = find_usages_until(var, until, tac_list[index:])
            for offset, use_type in usages:
                use = tac_list[index + offset]
                setattr(use, use_type, instruction.rhs)
                changed = True
    return changed


def debug_print(header, tac_list):
    print("-" * get_terminal_size().columns)
    print(header)
    print("-" * get_terminal_size().columns)
    for instruction in tac_list:
        print(instruction)


def optimize_tac(tac_list, debug=False):

    changed = True

    while changed:

        changed = any([instruction.optimize() for instruction in tac_list])

        if changed and debug:
            debug_print("Optimize instructions", tac_list)

        tac_list, changed = eliminate_dead_code(tac_list)

        if changed and debug:
            debug_print("Eliminate Dead Code", tac_list)

        changed = propagate_copies(tac_list)

        if changed and debug:
            debug_print("Propagate Copies", tac_list)

    return tac_list
