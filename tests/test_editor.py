from __future__ import annotations

import json
from pathlib import Path

import pytest
from slimconfig import build_output, plain_output

import verifier.checks
from contract import PicturesInput, TryInput
from plugin.editor import VIEW_FILE, edited, find_edits, pictures_problem, try_edits, view_pictures

INPUTS = Path(__file__).parent / "evals" / "inputs"
# Every eval input's shortest edits, worked out by hand: its file name says which case it is.
EXPECTED = {
    "01-rotate-90": ["rotate 90"],
    "02-rotate-180": ["rotate 180"],
    "03-flip-horizontal": ["flip horizontal"],
    "04-flip-vertical": ["flip vertical"],
    "05-recolor": ["recolor G>R"],
    "06-color-swap": ["recolor B>R R>B"],
    "07-merge-colors": ["recolor K>B"],
    "08-rotate-and-recolor": ["rotate 90", "recolor W>Y"],
    "09-flip-and-recolor": ["flip horizontal", "recolor B>G Y>R"],
    "10-turn-and-flip": ["rotate 90", "flip horizontal"],
    "11-symmetric-picture": ["rotate 180"],
    "12-rotate-270": ["rotate 270"],
    "13-rotate-flip-recolor": ["rotate 90", "flip vertical", "recolor R>P W>Y"],
    "14-many-colors": ["rotate 180", "recolor K>W W>K"],
    "15-two-colors": ["rotate 270", "recolor K>W W>K"],
}
CORNER = ["RWWWWW", "WWWWWW", "WWWWWW", "WWWWWW", "WWWWWW", "WWWWWB"]  # red top left, blue bottom right


def _pictures(name: str) -> PicturesInput:
    return build_output(json.loads((INPUTS / f"{name}.json").read_text()), PicturesInput)


def _with(name: str, **changes) -> PicturesInput:
    return build_output({**plain_output(_pictures(name)), **changes}, PicturesInput)


def test_each_edit_moves_or_recolors_the_pixels() -> None:
    assert edited(CORNER, ["rotate 90"])[0] == "WWWWWR"  # top left goes to top right
    assert edited(CORNER, ["rotate 180"])[0] == "BWWWWW"
    assert edited(CORNER, ["rotate 270"])[5] == "RWWWWW"  # top left goes to bottom left
    assert edited(CORNER, ["flip horizontal"])[0] == "WWWWWR"
    assert edited(CORNER, ["flip vertical"])[0] == "WWWWWB"
    assert edited(CORNER, ["recolor R>B B>R"]) == ["BWWWWW", *CORNER[1:5], "WWWWWR"]  # a swap, at once
    assert edited(CORNER, ["  Rotate   90", "RECOLOR r > g"]) == edited(CORNER, ["rotate 90", "recolor R>G"])


@pytest.mark.parametrize(
    "edit", ["rotate 45", "rotate", "flip sideways", "recolor", "recolor R>X", "recolor R>B R>G", "crop 1 1 2 2"]
)
def test_an_edit_that_cannot_be_read_is_refused(edit: str) -> None:
    with pytest.raises(ValueError, match="edit 1"):
        edited(CORNER, [edit])
    assert verifier.checks.replay(CORNER, [edit])[0] is None


def test_every_eval_input_has_its_intended_edits(tmp_path: Path) -> None:
    assert sorted(path.stem for path in INPUTS.glob("*.json")) == sorted(EXPECTED)
    for name, expected in EXPECTED.items():
        pictures = _pictures(name)
        assert pictures_problem(pictures) is None is verifier.checks.pictures_problem(pictures), name
        assert find_edits(pictures, tmp_path).edits == expected, name
        assert verifier.checks.replay(pictures.picture, expected) == (pictures.target, None), name


def test_the_view_is_the_pictures_and_their_colors(tmp_path: Path) -> None:
    viewed = view_pictures(_pictures("07-merge-colors"), tmp_path)
    assert viewed.colors == ["K black", "W white", "B blue", "Y yellow"]
    saved = json.loads((tmp_path / VIEW_FILE).read_text())
    assert saved == {key: value for key, value in plain_output(viewed).items() if key != "path"}


def test_trying_edits_counts_the_pixels_off(tmp_path: Path) -> None:
    pictures = plain_output(_pictures("01-rotate-90"))
    right = try_edits(build_output({**pictures, "edits": ["rotate 90"]}, TryInput), tmp_path)
    assert (right.matches_target, right.differences) == (True, 0)
    wrong = try_edits(build_output({**pictures, "edits": ["rotate 270"]}, TryInput), tmp_path)
    assert wrong.matches_target is False and wrong.differences > 0


@pytest.mark.parametrize(
    ("changes", "problem"),
    [
        ({"picture": ["WWWWW"] * 6}, "6 rows of 6"),
        ({"target": ["WWWWWW"] * 5}, "6 rows of 6"),
        ({"picture": ["WWWWWW"] * 5 + ["WWWWWX"]}, "color letters"),
        ({"picture": ["wwwwww"] * 6}, "color letters"),
        ({"target": ["RWWWWW"] + ["WWWWWW"] * 5}, "no rotate, flip and recolor"),  # one red pixel of many
        ({"target": json.loads((INPUTS / "01-rotate-90.json").read_text())["picture"]}, "nothing to edit"),
    ],
)
def test_refuses_pictures_without_an_answer(changes: dict, problem: str, tmp_path: Path) -> None:
    pictures = _with("01-rotate-90", **changes)
    assert problem in pictures_problem(pictures)
    assert problem in verifier.checks.pictures_problem(pictures)
    with pytest.raises(ValueError, match=problem):
        find_edits(pictures, tmp_path)
