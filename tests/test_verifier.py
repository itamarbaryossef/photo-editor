from __future__ import annotations

import json
from pathlib import Path

from slimconfig import build_output, plain_output

import verifier
from contract import EditsOutput, PicturesInput, TryInput, TryOutput, ViewOutput
from plugin.editor import find_edits, try_edits, view_pictures

TASK = "match-the-target"
INPUTS = Path(__file__).parent / "evals" / "inputs"


# The verifier gets contract instances, as NanoAgent's sandbox builds them from JSON.
def _pictures(name: str) -> PicturesInput:
    return build_output(json.loads((INPUTS / f"{name}.json").read_text()), PicturesInput)


def _reference(pictures: PicturesInput, tmp_path: Path) -> dict:
    return plain_output(find_edits(pictures, tmp_path))


def _check(edits: list[str], *, name: str = "08-rotate-and-recolor", reference=..., tmp_path: Path) -> dict:
    pictures = _pictures(name)
    reference = _reference(pictures, tmp_path) if reference is ... else reference
    built = None if reference is None else build_output(reference, EditsOutput)
    output = build_output({"edits": edits}, EditsOutput)
    return verifier.verify_task(TASK, pictures, output, built, str(tmp_path))


def test_approves_the_tools_and_the_reference_edits(tmp_path: Path) -> None:
    for path in sorted(INPUTS.glob("*.json")):
        pictures = _pictures(path.stem)
        reference = _reference(pictures, tmp_path)
        viewed = build_output(plain_output(view_pictures(pictures, tmp_path)), ViewOutput)
        tries = [reference["edits"], ["rotate 90"], ["flip sideways"]]
        tried = TryInput(picture=pictures.picture, target=pictures.target, tries=tries)
        result = build_output(plain_output(try_edits(tried, tmp_path)), TryOutput)
        assert verifier.verify_input("view_pictures", pictures)["valid"] is True
        assert verifier.verify_output("view_pictures", pictures, viewed, str(tmp_path))["valid"] is True
        assert verifier.verify_input("try_edits", tried)["valid"] is True
        assert verifier.verify_output("try_edits", tried, result, str(tmp_path))["valid"] is True
        built = build_output(reference, EditsOutput)
        assert verifier.verify_output("find_edits", pictures, built, str(tmp_path))["valid"] is True
        verdict = _check(reference["edits"], name=path.stem, tmp_path=tmp_path)
        assert verdict["valid"] is True and verdict["score"] == 1.0, (path.stem, verdict)


def test_accepts_other_edits_that_make_the_target(tmp_path: Path) -> None:
    for edits in [
        ["recolor W>Y", "rotate 90"],  # the other order
        ["rotate 270", "rotate 180", "recolor W>Y"],  # 90 degrees in two turns
        ["flip vertical", "rotate 270", "flip vertical", "recolor W>Y"],
    ]:
        assert _check(edits, tmp_path=tmp_path)["valid"] is True, edits
    for edits in [["rotate 180"], ["flip vertical"], ["flip horizontal", "flip vertical"]]:
        assert _check(edits, name="11-symmetric-picture", tmp_path=tmp_path)["valid"] is True, edits


def test_accepts_edits_in_other_case_or_spacing(tmp_path: Path) -> None:
    assert _check(["  ROTATE 90 ", "recolor  w > y"], tmp_path=tmp_path)["valid"] is True


def test_refuses_a_wrong_turn_and_says_only_the_turn_is_wrong(tmp_path: Path) -> None:
    verdict = _check(["rotate 270", "recolor W>Y"], tmp_path=tmp_path)
    assert verdict["valid"] is False and verdict["score"] == 0.0 and "differs from the target" in verdict["message"]
    assert (verdict["details"]["only_turn_or_flip_wrong"], verdict["details"]["only_colors_wrong"]) == (True, False)
    assert verdict["details"]["one_answer"] == ["rotate 90", "recolor W>Y"]


def test_refuses_wrong_colors_and_says_only_the_colors_are_wrong(tmp_path: Path) -> None:
    verdict = _check(["rotate 90"], tmp_path=tmp_path)
    assert verdict["valid"] is False
    assert (verdict["details"]["only_colors_wrong"], verdict["details"]["only_turn_or_flip_wrong"]) == (True, False)
    first = verdict["details"]["first_difference"]
    assert (first["result"], first["target"]) == ("W", "Y")


def test_refuses_a_recolor_that_misses_a_color_and_counts_its_pixels(tmp_path: Path) -> None:
    verdict = _check(["flip horizontal", "recolor B>G"], name="09-flip-and-recolor", tmp_path=tmp_path)
    yellow = "".join(_pictures("09-flip-and-recolor").picture).count("Y")
    assert verdict["valid"] is False and f"in {yellow} pixels" in verdict["message"]
    assert verdict["details"]["only_colors_wrong"] is True


def test_refuses_edits_that_cannot_be_read_or_are_too_many(tmp_path: Path) -> None:
    for edits, message in [
        ([], "has no edits"),
        (["rotate 45"], "edit 1 ('rotate 45') is not an edit"),
        (["rotate 90", "crop 0 0 3 3"], "edit 2"),
        (["recolor W>X"], "colors must be among"),
        (["rotate 90"] * 5, "more than 4"),
    ]:
        verdict = _check(edits, tmp_path=tmp_path)
        assert verdict["valid"] is False and message in verdict["message"], (edits, verdict["message"])


def test_refuses_pinned_edits_that_do_not_make_the_target(tmp_path: Path) -> None:
    pictures = _pictures("08-rotate-and-recolor")
    for broken in [{"edits": ["rotate 90"]}, {"edits": []}, {"edits": ["rotate 45"]}]:
        built = build_output(broken, EditsOutput)
        assert verifier.verify_output("find_edits", pictures, built, str(tmp_path))["valid"] is False
        assert _check(["rotate 90", "recolor W>Y"], reference=broken, tmp_path=tmp_path)["valid"] is False
    assert _check(["rotate 90", "recolor W>Y"], reference=None, tmp_path=tmp_path)["valid"] is False


def test_refuses_a_view_that_differs_from_the_input_or_the_saved_file(tmp_path: Path) -> None:
    pictures = _pictures("08-rotate-and-recolor")
    viewed = plain_output(view_pictures(pictures, tmp_path))
    changed = {**viewed, "target": ["W" * 6] * 6}
    for broken in [changed, {**viewed, "question": "Which color is most common?"}]:
        verdict = verifier.verify_output("view_pictures", pictures, build_output(broken, ViewOutput), str(tmp_path))
        assert verdict["valid"] is False and "not the one saved" in verdict["message"]
    (tmp_path / viewed["path"]).write_text(json.dumps({key: value for key, value in changed.items() if key != "path"}))
    verdict = verifier.verify_output("view_pictures", pictures, build_output(changed, ViewOutput), str(tmp_path))
    assert verdict["valid"] is False and "not the input's" in verdict["message"]
    (tmp_path / viewed["path"]).unlink()
    verdict = verifier.verify_output("view_pictures", pictures, build_output(viewed, ViewOutput), str(tmp_path))
    assert verdict["valid"] is False


def test_refuses_a_tried_result_that_is_not_the_edited_picture(tmp_path: Path) -> None:
    pictures = _pictures("08-rotate-and-recolor")
    tried = TryInput(picture=pictures.picture, target=pictures.target, tries=[["rotate 270"], ["rotate 90"]])
    honest = plain_output(try_edits(tried, tmp_path))
    assert verifier.verify_output("try_edits", tried, build_output(honest, TryOutput), str(tmp_path))["valid"]
    first, second = honest["tries"]
    for change in [
        {"result": pictures.target},
        {"matches_target": True, "differences": 0},
        {"colors_line_up": True},  # rotate 270 is the wrong turn, so its colors cannot line up
        {"problem": "rotate 270 is not an edit"},
    ]:
        broken = {"tries": [{**first, **change}, second]}
        verdict = verifier.verify_output("try_edits", tried, build_output(broken, TryOutput), str(tmp_path))
        assert verdict["valid"] is False and "try 1" in verdict["message"], change
    swapped = build_output({"tries": [second, first]}, TryOutput)
    assert verifier.verify_output("try_edits", tried, swapped, str(tmp_path))["valid"] is False


def test_refuses_no_tries_or_more_than_8(tmp_path: Path) -> None:
    pictures = _pictures("08-rotate-and-recolor")
    for tries in [[], [["rotate 90"]] * 9]:
        tried = TryInput(picture=pictures.picture, target=pictures.target, tries=tries)
        assert verifier.verify_input("try_edits", tried)["valid"] is False


def test_refuses_pictures_without_an_answer() -> None:
    pictures = build_output(
        {"picture": ["RWWWWW"] + ["WWWWWW"] * 5, "target": ["RRWWWW"] + ["WWWWWW"] * 5}, PicturesInput
    )
    for tool in ["view_pictures", "find_edits"]:
        verdict = verifier.verify_input(tool, pictures)
        assert verdict["valid"] is False and "no rotate, flip and recolor" in verdict["message"]
