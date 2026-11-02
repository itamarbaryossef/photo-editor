"""try_edits: the result it returns is the picture after the edits, and its distance from the target."""

from .checks import differences, pictures_problem, replay, result


def verify_input(value):
    problem = pictures_problem(value)
    if problem:
        return result(False, problem)
    _, problem = replay(value.picture, value.edits)
    if problem:
        return result(False, problem)
    return result(True, "input is valid")


def verify_output(input_value, output_value, workspace):
    rows, problem = replay(input_value.picture, input_value.edits)
    if problem:
        return result(False, problem)
    if output_value.result != rows:
        return result(False, "the result is not the picture after the edits", result=output_value.result, expected=rows)
    off = len(differences(rows, input_value.target))
    if (output_value.differences, output_value.matches_target) != (off, off == 0):
        return result(
            False,
            "the result's distance from the target is wrong",
            differences=output_value.differences,
            expected=off,
        )
    return result(True, "the edits are tried", differences=off)
