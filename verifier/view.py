"""view_pictures: the view it returns is the one it saved, and it is the input's picture, target and colors."""

import json
from pathlib import Path

from .checks import COLORS, result, verify_pictures

QUESTION = "Which edits turn the picture into the target?"
NAMES = dict(zip(COLORS, ["black", "white", "red", "green", "blue", "yellow", "orange", "purple"], strict=True))


def verify_input(value):
    return verify_pictures(value)


def verify_output(input_value, output_value, workspace):
    returned = {
        "picture": output_value.picture,
        "target": output_value.target,
        "colors": output_value.colors,
        "question": output_value.question,
    }
    path = Path(workspace) / output_value.path
    if not path.is_file() or json.loads(path.read_text(encoding="utf-8")) != returned:
        return result(False, "the returned view is not the one saved in the workspace", path=output_value.path)
    if output_value.question != QUESTION:
        return result(False, "the question is not the task's", question=output_value.question)
    if (output_value.picture, output_value.target) != (input_value.picture, input_value.target):
        return result(False, "the view's pictures are not the input's")
    used = [letter for letter in COLORS if letter in "".join(input_value.picture + input_value.target)]
    if output_value.colors != [f"{letter} {NAMES[letter]}" for letter in used]:
        return result(False, "the view's colors are not the ones the pictures use", colors=output_value.colors)
    return result(True, "the pictures are viewed", path=output_value.path, colors=len(used))
