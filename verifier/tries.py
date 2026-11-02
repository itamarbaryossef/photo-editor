"""try_edits: each try it returns is the picture after those edits, and its distance from the target."""

from .checks import SIDE, differences, pictures_problem, recolors_to, replay, result

MOST_TRIES = 8


def verify_input(value):
    problem = pictures_problem(value)
    if problem:
        return result(False, problem)
    if not 1 <= len(value.tries) <= MOST_TRIES:
        return result(False, f"there must be 1 to {MOST_TRIES} tries, not {len(value.tries)}")
    return result(True, "input is valid")


def _expected(input_value, edits):
    """(result, matches_target, differences, colors_line_up, has a problem) for one try, by the verifier's replay."""
    rows, problem = replay(input_value.picture, edits)
    if problem:
        return [], False, SIDE * SIDE, False, True
    off = len(differences(rows, input_value.target))
    return rows, off == 0, off, recolors_to(rows, input_value.target), False


def verify_output(input_value, output_value, workspace):
    if [tried.edits for tried in output_value.tries] != input_value.tries:
        return result(False, "the tries are not the ones asked for, in their order")
    for number, tried in enumerate(output_value.tries, 1):
        returned = (tried.result, tried.matches_target, tried.differences, tried.colors_line_up, bool(tried.problem))
        expected = _expected(input_value, tried.edits)
        if returned != expected:
            return result(False, f"try {number} is not the picture after its edits", edits=tried.edits)
    return result(True, "the edits are tried", tries=len(output_value.tries))
