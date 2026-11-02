"""find_edits, the task's reference, and the task itself: the agent's edits, replayed on the picture."""

from .checks import (
    arrangements,
    differences,
    pictures_problem,
    recolors_to,
    replay,
    result,
    verify_pictures,
)


def verify_input(value):
    return verify_pictures(value)


def _makes_target(pictures, edits):
    rows, problem = replay(pictures.picture, edits)
    return problem is None and rows == pictures.target


def verify_output(input_value, output_value, workspace):
    problem = pictures_problem(input_value)
    if problem:
        return result(False, f"the pictures are unusable: {problem}")
    if not _makes_target(input_value, output_value.edits):
        return result(False, "the edits do not make the target", edits=output_value.edits)
    return result(True, "the edits make the target", edits=output_value.edits)


def verify_task(arguments, output, reference, workspace):
    problem = pictures_problem(arguments)
    if problem:
        return result(False, f"the pictures are unusable: {problem}")
    if reference is None:
        return result(False, "there are no pinned edits to check against")
    if not _makes_target(arguments, reference.edits):
        return result(False, "the pinned edits do not make the target", reference=reference.edits)
    given, one_answer = output.edits, reference.edits
    if not given:
        return result(False, "the answer has no edits", given=given, one_answer=one_answer)
    rows, problem = replay(arguments.picture, given)
    if problem:
        return result(False, problem, given=given, one_answer=one_answer)
    off = differences(rows, arguments.target)
    if off:
        (row, column), *_ = off
        return result(
            False,
            f"the result differs from the target in {len(off)} pixel{'s' * (len(off) != 1)}",
            given=given,
            one_answer=one_answer,
            result=rows,
            first_difference={
                "row": row,
                "column": column,
                "result": rows[row][column],
                "target": arguments.target[row][column],
            },
            only_colors_wrong=recolors_to(rows, arguments.target),
            only_turn_or_flip_wrong=arguments.target in arrangements(rows),
        )
    return result(True, "the edits make the target", given=given, one_answer=one_answer)
