# Photo Editor

A `nanoagent.plugin/v0001` plugin for visual reasoning by a text-only agent, over several steps: editing
a picture to match a target. Its input is a small picture and an edited copy of it, the target, and
the agent must find the edits that turn one into the other. It tries edits with a tool, looks at the
result, and adjusts until the result matches, then submits its edits. Many lists of edits are right
(a 180° turn is also two flips), so the verifier replays the agent's edits on the picture itself and
compares the result with the target pixel by pixel, with no model.

A picture is 6 rows of 6 pixels, one color letter per pixel: `K` black, `W` white, `R` red, `G`
green, `B` blue, `Y` yellow, `O` orange, `P` purple.

```json
{
  "picture": ["BBBWWW", "BBBWWW", "RRRRRR", "WWWWWW", "RRRRRR", "WWWWWW"],
  "target":  ["YRYRBB", "YRYRBB", "YRYRBB", "YRYRYY", "YRYRYY", "YRYRYY"]
}
```

The target is the picture turned a quarter clockwise with its white made yellow, so
`["rotate 90", "recolor W>Y"]` makes it, and so do `["recolor W>Y", "rotate 90"]` and
`["rotate 270", "rotate 180", "recolor W>Y"]`.

The edits, applied in order and read ignoring case and extra spaces:

- `rotate 90`, `rotate 180` or `rotate 270`: turn the whole picture clockwise;
- `flip horizontal` (swap left and right) or `flip vertical` (swap top and bottom);
- `recolor` with color changes such as `recolor R>B G>W`: every `R` becomes `B` and every `G`
  becomes `W`, all at once, so `recolor R>B B>R` swaps red and blue.

Every answer is at most 4 edits. Any target that can be made at all needs at most 3 (one turn, one
flip, one recolor).

The input is refused unless both pictures are 6 rows of 6 pixels of those letters, the target is not
the picture already, and some edits make it. Pictures are kept this small so that DeepSeek V4 Flash's
reasoning fits inside RUSH Lab's 2048-token output limit.

## Tools

| Tool | Does | Code |
|---|---|---|
| `view_pictures` | Returns the picture, the target and the colors they use, saves them as `pictures.json` in the workspace, and states the question; it solves nothing | `src/plugin/editor.py` |
| `try_edits` | Applies a list of edits to the picture and returns the result, whether it matches the target, and how many pixels differ | `src/plugin/editor.py` |
| `find_edits` | Finds one shortest list of edits that makes the target; the `match-the-target` task's pinned reference | `src/plugin/editor.py` |

### Tasks

| Task | Does | Runner |
|---|---|---|
| `match-the-target` | Finds the edits that turn a picture into its edited target | `agent`, with `view_pictures` and `try_edits`; reference `find_edits` |

The task's input is the two pictures, as above. Its output is `{"edits": [...]}`: the edits, in
order.

The verifier (`verifier/`) edits pictures on its own, apart from `src/plugin/`, and checks:

- `verify_input`: both pictures keep the rules above, and some edits make the target (any edits come
  down to one of the 8 turns and flips followed by one recolor, so that is 8 checks).
- `verify_output` of `view_pictures`: the returned view is the `pictures.json` saved in the
  workspace, the question is the task's, and the pictures and colors are the input's.
- `verify_output` of `try_edits`: the result is the verifier's own replay of the edits, and its count
  of differing pixels is right.
- `verify_output` of `find_edits`: its edits make the target.
- `verify_task`: the input and the pinned edits again, then the agent's edits, with their own message
  for each way to be wrong: no edits, more than 4, an edit that cannot be read, or a result that
  differs from the target (`details` give the count, the first differing pixel, and whether only the
  colors or only the turn or flip are wrong). Any edits that make the target are right, scored 1.

## Layout

```text
.
├── nanoagent.yaml   # manifest (a slimconfig ManifestConfig): id, runtime, permissions, tools, tasks
├── contract.py      # each tool's and task's typed input and output: slimconfig Output classes
├── README.md
├── LICENSE
├── pyproject.toml
├── uv.lock
├── .gitignore
├── .env             # environment variable NAMEs this plugin needs, never values (none)
├── src/plugin/      # the MCP server (__main__.py) and the edits and tools (editor.py)
├── tests/           # test_editor.py (the tools), test_verifier.py (the verifier), evals/ (model runs)
├── ui/              # how the page draws the outputs: renderers.js and renderers.css
├── product/         # the product page a catalog shows: product.yaml and icon.svg
└── verifier/        # deterministic verifier package: view.py, tries.py, edits.py and checks.py
```

`contract.py` is the one place a value's shape is declared. Its `Output` classes are the JSON
Schemas the server offers and the agent sees, and every input and output is built into its class
on the way in and out. A tool that fails raises; NanoAgent sees an MCP error. The plugin needs no
network, no API key, no data files and no randomness: every answer follows from the pictures alone.

## Develop and run

Prerequisites: Git, Python 3.12 or later, and `uv`.

```bash
uv sync --extra dev
uv run pytest
uv run ruff check .
```

To see an input's view and shortest edits without an agent:

```bash
uv run python -c "
import json
from pathlib import Path
from slimconfig import build_output
from contract import PicturesInput
from plugin.editor import find_edits, view_pictures
given = build_output(json.loads(Path('tests/evals/inputs/08-rotate-and-recolor.json').read_text()), PicturesInput)
print(view_pictures(given, Path('.')))
print(find_edits(given, Path('.')))
"
```

This writes `pictures.json`, the view, to the current folder.

## Evaluating with a model

`tests/evals/` runs the `match-the-target` task end to end with the model and limits RUSH Lab uses
(DeepSeek V4 Flash through OpenRouter, `tests/evals/agent.yaml`) on the 15 inputs in
`tests/evals/inputs/`, each named for the case it tests: each turn and flip alone, a recolor, a color
swap, two colors merged, a turn or flip with a recolor, a turn with a flip, a symmetric picture that
two edits make, all three kinds together, many colors, and two colors swapped. `tests/test_editor.py`
checks each one's shortest edits. It is its own uv project, which installs NanoAgent pinned to a
commit of github.com/RUSH-LAB/nanoagent, so it needs only Git, `uv` and an OpenRouter API key:

```bash
export OPENROUTER_API_KEY=...   # your own key; never commit it
uv run --project tests/evals python tests/evals/run.py
```

Each input gets a folder `tests/evals/runs/<name>/` holding `result.json` (the agent's edits),
`reference.json` (one shortest answer), `verdict.json` (the verifier's verdict), `messages.json` (the
conversation) and `run.log`. `tests/evals/runs/summary.md` tabulates them, and `all_inputs.json`,
`all_verdicts.json` and `all_run_logs.log` gather every run's input, verdict and log. A folder that
already exists is not rerun, so delete `tests/evals/runs/` to start over. The references and verdicts
are deterministic, but the model's answers can differ from run to run.

Publishing checks every plugin rule: push the plugin to a public GitHub repository and submit its
URL in the RUSH Lab marketplace. In the plugin's chat, paste two pictures such as the ones above,
and the result card shows the verifier's verdict.
