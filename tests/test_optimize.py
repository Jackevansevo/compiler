from shutil import get_terminal_size
from compiler.tac import TacInstruction
from compiler.optimize import eliminate_dead_code


# def test_eliminate_dead_code():
#     """
#     t2 := 5
#     y := t2
#     return y
#     """
#     tac_list = [
#         TacInstruction(None, '=', "t2", "5"),
#         TacInstruction(None, "-", "y", "t2"),
#         TacInstruction(None, "return", "y", None),
#     ]
#     new_list, changed = eliminate_dead_code(tac_list)
#     assert not changed
#     assert new_list == tac_list
