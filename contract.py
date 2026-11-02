"""Each tool's and task's typed input and output (see nanoagent.plugin.v0001.contract): declarations only."""

from dataclasses import dataclass
from enum import Enum
from typing import Annotated

from slimconfig import Output


class Tool(Enum):
    VIEW_PICTURES = "view_pictures"
    TRY_EDITS = "try_edits"
    FIND_EDITS = "find_edits"


class Task(Enum):
    MATCH_THE_TARGET = "match-the-target"


@dataclass
class PicturesInput(Output):
    picture: Annotated[
        list[str], "The picture, 6 rows of 6 pixels, top to bottom, one color letter per pixel (K W R G B Y O P)"
    ]
    target: Annotated[list[str], "The edited picture to make, drawn the same way"]


@dataclass
class TryInput(Output):
    picture: Annotated[list[str], "The picture, exactly as view_pictures returned it"]
    target: Annotated[list[str], "The target, exactly as view_pictures returned it"]
    edits: Annotated[
        list[str], "The edits to try on the picture, in order, at most 4: rotate 90, flip horizontal, recolor R>B ..."
    ]


@dataclass
class ViewOutput(Output):
    path: Annotated[str, "The view's JSON file, relative to the workspace"]
    picture: Annotated[list[str], "The picture, row by row; row 0 is the top"]
    target: Annotated[list[str], "The target, row by row; row 0 is the top"]
    colors: Annotated[list[str], "Each color letter in the pictures and its name, such as 'R red'"]
    question: Annotated[str, "The question to answer about the pictures"]


@dataclass
class TryOutput(Output):
    result: Annotated[list[str], "The picture after the edits, row by row"]
    matches_target: Annotated[bool, "Whether the result is the target, pixel for pixel"]
    differences: Annotated[int, "How many pixels of the result differ from the target"]


@dataclass
class EditsOutput(Output):
    edits: Annotated[
        list[str],
        "The edits that turn the picture into the target, in order, at most 4: "
        "rotate 90|180|270, flip horizontal|vertical, or recolor with changes like R>B",
    ]


TOOLS = {
    Tool.VIEW_PICTURES: (PicturesInput, ViewOutput),
    Tool.TRY_EDITS: (TryInput, TryOutput),
    Tool.FIND_EDITS: (PicturesInput, EditsOutput),
}
TASKS = {Task.MATCH_THE_TARGET: (PicturesInput, EditsOutput)}
