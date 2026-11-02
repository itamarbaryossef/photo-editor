"""Checks shared by the tool verifiers. Pure functions of their arguments; they edit pictures on their own,
apart from src/plugin/editor.py, so a fault there cannot pass for an answer here."""

import re

COLORS = "KWRGBYOP"  # black, white, red, green, blue, yellow, orange, purple
SIDE = 6  # rows, and pixels in a row, of every picture
MOST_EDITS = 4
LAST = SIDE - 1
# Where the pixel at (row, column) goes under each turn or flip.
TURNS = {"90": lambda r, c: (c, LAST - r), "180": lambda r, c: (LAST - r, LAST - c), "270": lambda r, c: (LAST - c, r)}
FLIPS = {"horizontal": lambda r, c: (r, LAST - c), "vertical": lambda r, c: (LAST - r, c)}
ROTATE = re.compile(r"rotate (90|180|270)")
FLIP = re.compile(r"flip (horizontal|vertical)")
RECOLOR = re.compile(r"recolor((?: [A-Z]>[A-Z])+)")


def result(valid, message, *, score=None, **details):
    return {
        "valid": valid,
        "score": float(valid) if score is None else score,
        "message": message,
        "details": details,
    }


def grid(rows):
    """``rows`` as {(row, column): color letter}."""
    return {(row, column): color for row, line in enumerate(rows) for column, color in enumerate(line)}


def rows_of(pixels):
    return ["".join(pixels[row, column] for column in range(SIDE)) for row in range(SIDE)]


def moved(pixels, where):
    return {where(row, column): color for (row, column), color in pixels.items()}


def apply(pixels, edit):
    """``pixels`` after ``edit``, or the reason ``edit`` is not one, as a string."""
    text = " ".join(re.sub(r"\s*>\s*", ">", edit).split())
    if match := ROTATE.fullmatch(text.lower()):
        return moved(pixels, TURNS[match[1]])
    if match := FLIP.fullmatch(text.lower()):
        return moved(pixels, FLIPS[match[1]])
    head, _, rest = text.partition(" ")
    if head.lower() == "recolor" and (match := RECOLOR.fullmatch(f"recolor {rest.upper()}")):
        changes = [change.split(">") for change in match[1].split()]
        olds = [old for old, _ in changes]
        if set(olds + [new for _, new in changes]) - set(COLORS):
            return f"its colors must be among {' '.join(COLORS)}"
        if len(set(olds)) != len(olds):
            return "it changes a color twice"
        table = dict(changes)
        return {spot: table.get(color, color) for spot, color in pixels.items()}
    return "an edit is rotate 90|180|270, flip horizontal|vertical, or recolor with changes like R>B"


def replay(rows, edits):
    """(the rows after ``edits``, None), or (None, the reason they cannot be made)."""
    if len(edits) > MOST_EDITS:
        return None, f"there are {len(edits)} edits, more than {MOST_EDITS}"
    pixels = grid(rows)
    for number, edit in enumerate(edits, 1):
        pixels = apply(pixels, edit)
        if isinstance(pixels, str):
            return None, f"edit {number} ({edit!r}) is not an edit: {pixels}"
    return rows_of(pixels), None


def recolors_to(rows, target):
    """Whether one color change per color turns ``rows`` into ``target``."""
    seen = {}
    return all(seen.setdefault(have, want) == want for have, want in zip("".join(rows), "".join(target)))


def arrangements(rows):
    """``rows`` under each of the 8 turns and flips, itself included."""
    pixels = grid(rows)
    turned = [pixels, *(moved(pixels, turn) for turn in TURNS.values())]
    return [rows_of(each) for each in turned + [moved(each, FLIPS["horizontal"]) for each in turned]]


def reachable(picture, target):
    return any(recolors_to(each, target) for each in arrangements(picture))


def pictures_problem(pictures):
    """What makes ``pictures`` not a picture and a target that edits make, or None."""
    for what, rows in (("the picture", pictures.picture), ("the target", pictures.target)):
        if len(rows) != SIDE or any(len(row) != SIDE for row in rows):
            return f"{what} must be {SIDE} rows of {SIDE} pixels"
        if any(set(row) - set(COLORS) for row in rows):
            return f"{what} may hold only the color letters {' '.join(COLORS)}"
    if pictures.picture == pictures.target:
        return "the target is the picture already: there is nothing to edit"
    if not reachable(pictures.picture, pictures.target):
        return "no rotate, flip and recolor make the target from the picture"
    return None


def differences(rows, target):
    """Every (row, column) where ``rows`` and ``target`` differ, top to bottom."""
    have, want = grid(rows), grid(target)
    return [spot for spot in sorted(want) if have[spot] != want[spot]]


def verify_pictures(value):
    """verify_input of view_pictures and find_edits: their input is the picture and the target."""
    problem = pictures_problem(value)
    if problem:
        return result(False, problem)
    return result(True, "input is valid")
