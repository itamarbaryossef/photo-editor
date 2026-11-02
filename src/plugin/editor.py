from __future__ import annotations

import json
import re
from pathlib import Path

from slimconfig import plain_output

from contract import EditsOutput, PicturesInput, Tried, TryInput, TryOutput, ViewOutput

QUESTION = "Which edits turn the picture into the target?"
COLORS = {
    "K": "black",
    "W": "white",
    "R": "red",
    "G": "green",
    "B": "blue",
    "Y": "yellow",
    "O": "orange",
    "P": "purple",
}
SIDE = 6  # rows, and pixels in a row, of every picture
MOST_EDITS = 4
MOST_TRIES = 8  # enough for every turn and flip in one call
ANGLES = {"90": 1, "180": 2, "270": 3}  # degrees -> clockwise quarter turns
DIRECTIONS = ("horizontal", "vertical")
# Every rotate and flip adds up to one of these 8; a recolor after it makes any reachable target.
MOVES = [
    [],
    ["rotate 90"],
    ["rotate 180"],
    ["rotate 270"],
    ["flip horizontal"],
    ["flip vertical"],
    ["rotate 90", "flip horizontal"],
    ["rotate 90", "flip vertical"],
]
VIEW_FILE = "pictures.json"


def rotate(rows: list[str], turns: int) -> list[str]:
    """``rows`` turned clockwise a quarter, ``turns`` times: each new row is a column read bottom to top."""
    for _ in range(turns):
        rows = ["".join(column) for column in zip(*reversed(rows), strict=True)]
    return rows


def flip(rows: list[str], direction: str) -> list[str]:
    """``rows`` mirrored: horizontal swaps left and right, vertical swaps top and bottom."""
    return [row[::-1] for row in rows] if direction == "horizontal" else rows[::-1]


def recolor(rows: list[str], changes: dict[str, str]) -> list[str]:
    """``rows`` with every color in ``changes`` replaced at once, so R>B B>R swaps red and blue."""
    return ["".join(changes.get(pixel, pixel) for pixel in row) for row in rows]


def _words(edit: str) -> list[str]:
    return re.sub(r"\s*>\s*", ">", edit).split()


def _changes(words: list[str]) -> dict[str, str]:
    changes: dict[str, str] = {}
    for change in words:
        old, arrow, new = change.upper().partition(">")
        if not arrow or old not in COLORS or new not in COLORS:
            raise ValueError(f"{change!r} is not a color change like R>B")
        if old in changes:
            raise ValueError(f"{old} is changed twice")
        changes[old] = new
    if not changes:
        raise ValueError("recolor names no color change, like R>B")
    return changes


def edit(rows: list[str], one: str) -> list[str]:
    """``rows`` after one edit, read ignoring case and extra spaces; an edit that cannot be read raises."""
    words = _words(one)
    action = words[0].lower() if words else ""
    if action == "rotate":
        if len(words) != 2 or words[1] not in ANGLES:
            raise ValueError("rotate takes 90, 180 or 270")
        return rotate(rows, ANGLES[words[1]])
    if action == "flip":
        if len(words) != 2 or words[1].lower() not in DIRECTIONS:
            raise ValueError("flip takes horizontal or vertical")
        return flip(rows, words[1].lower())
    if action == "recolor":
        return recolor(rows, _changes(words[1:]))
    raise ValueError("an edit starts with rotate, flip or recolor")


def edited(rows: list[str], edits: list[str]) -> list[str]:
    """``rows`` after ``edits``, in order."""
    if len(edits) > MOST_EDITS:
        raise ValueError(f"there may be at most {MOST_EDITS} edits, not {len(edits)}")
    for number, one in enumerate(edits, 1):
        try:
            rows = edit(rows, one)
        except ValueError as error:
            raise ValueError(f"edit {number} ({one!r}) is not an edit: {error}") from None
    return rows


def _color_changes(rows: list[str], target: list[str]) -> dict[str, str] | None:
    """The one color change per color that makes ``rows`` the target, or None when a color would need two."""
    changes: dict[str, str] = {}
    for pixel, wanted in zip("".join(rows), "".join(target), strict=True):
        if changes.setdefault(pixel, wanted) != wanted:
            return None
    return {old: new for old, new in sorted(changes.items()) if old != new}


def shortest(picture: list[str], target: list[str]) -> list[str] | None:
    """The fewest edits that make the target from the picture, or None when no edits do."""
    found = None
    for moves in MOVES:
        changes = _color_changes(edited(picture, moves), target)
        if changes is None:
            continue
        edits = moves + (["recolor " + " ".join(f"{old}>{new}" for old, new in changes.items())] if changes else [])
        if found is None or len(edits) < len(found):
            found = edits
    return found


def pictures_problem(given: PicturesInput) -> str | None:
    """What makes ``given`` not a picture and a target that some edits make, or None."""
    for what, rows in (("the picture", given.picture), ("the target", given.target)):
        if len(rows) != SIDE or any(len(row) != SIDE for row in rows):
            return f"{what} must be {SIDE} rows of {SIDE} pixels"
        if any(set(row) - set(COLORS) for row in rows):
            return f"{what} may hold only the color letters {' '.join(COLORS)}"
    if given.picture == given.target:
        return "the target is the picture already: there is nothing to edit"
    if shortest(given.picture, given.target) is None:
        return "no rotate, flip and recolor make the target from the picture"
    return None


def _checked(given: PicturesInput | TryInput) -> None:
    problem = pictures_problem(PicturesInput(picture=given.picture, target=given.target))
    if problem:
        raise ValueError(problem)


def view_pictures(given: PicturesInput, workspace: Path) -> ViewOutput:
    """The picture, the target and the colors they use, as a vision model might read them; it solves nothing."""
    _checked(given)
    used = sorted(set("".join(given.picture + given.target)), key=list(COLORS).index)
    colors = [f"{letter} {COLORS[letter]}" for letter in used]
    output = ViewOutput(path=VIEW_FILE, picture=given.picture, target=given.target, colors=colors, question=QUESTION)
    saved = {key: value for key, value in plain_output(output).items() if key != "path"}
    (workspace / VIEW_FILE).write_text(json.dumps(saved, indent=1) + "\n", encoding="utf-8")
    return output


def _tried(given: TryInput, edits: list[str]) -> Tried:
    try:
        result = edited(given.picture, edits)
    except ValueError as error:
        # Edits that cannot be read make nothing, so every pixel counts as off.
        return Tried(edits, [], False, SIDE * SIDE, False, str(error))
    differences = sum(a != b for a, b in zip("".join(result), "".join(given.target), strict=True))
    lined_up = _color_changes(result, given.target) is not None
    return Tried(edits, result, differences == 0, differences, lined_up, "")


def try_edits(given: TryInput, workspace: Path) -> TryOutput:
    """Each list of edits applied to the picture, and how far its result is from the target."""
    _checked(given)
    if not 1 <= len(given.tries) <= MOST_TRIES:
        raise ValueError(f"there must be 1 to {MOST_TRIES} tries, not {len(given.tries)}")
    return TryOutput(tries=[_tried(given, edits) for edits in given.tries])


def find_edits(given: PicturesInput, workspace: Path) -> EditsOutput:
    """The pinned reference: one shortest list of edits; NanoAgent runs it out of the agent's sight."""
    _checked(given)
    return EditsOutput(edits=shortest(given.picture, given.target))
