---
name: preza-merge
description: Carry a course manager's hand-edited .pptx fork (font sizes, paddings, code-panel borders) into the preza_gen generator as a reusable formatting profile — since the decks are GENERATED from YAML, edits made only to the returned file die on the next build. Runs propose (three-way diff base/ours/theirs → docs/reviews/merge/*.md + *.proposal.yml with numeric evidence, decision null per rule) → human accept/reject → apply (writes settings/formats.yml profile, points deck.format at it, builds a patch version) → verify (structural residual vs her fork, invariant check against ours). Triggers on "she sent back an edited deck", "her formatting changes keep getting lost on rebuild", "merge the reviewer's pptx fork", "what did the manager actually change", "слить правки ревьюера/менеджера в генератор", or running `just preza-merge-propose|apply|verify|run`.
model: "default"
reasoning_effort: "normal"
---

Judge and carry a reviewer's hand-edited `.pptx` fork into the `preza_gen` generator instead of
into one file. Sibling of `preza-review` (accent coverage) and `preza-de-validate`
(schema/bounds): this skill does not touch content, only formatting that survived a human pass
on a built deck. Sub-agent `preza-merge-keeper` owns this lane end to end — invoke it for
multi-step merge work; use this skill directly for a single propose/apply/verify call or to look
up the flow.

## Why this lane exists

The course manager receives a built deck, edits it by hand in her tool (font sizes, paddings,
code-panel borders), and sends the file back. The decks are GENERATED from YAML
(`content/*-content.yml` → `preza_gen`), so her edits die on the next `just build` unless they
are turned into generator rules. This lane answers "what did she actually change" and writes the
systematic part of the answer into a formatting profile the generator can reuse on every future
deck — not just this one file.

## Flow

`propose` → human decisions → `apply` → `verify`. Spec: `docs/preza-merge-lane.md` (repo root).
Settings SSoT: `settings/merge.yml` (thresholds, tolerances, per-rule overrides). Profiles:
`settings/formats.yml` (generated-and-edited by `apply` — never hand-write prose into it).

1. **`propose`** diffs THREE sides — `base` (the version she was handed), `ours` (our newer
   build), `theirs` (her fork) — aligns slides by title, and derives formatting RULES, each with
   numeric evidence (share of eligible slides the change appears on). Writes
   `docs/reviews/merge/<...>.md` (human-readable report) and `<...>.proposal.yml` (structured
   decisions file).
2. Every derived rule lands with `decision: null`. A human reviews the evidence and writes
   `accept` or `reject` into the proposal file.
3. **`apply`** REFUSES to run while any `decision` is still `null` — that gate is the entire
   reason the proposal file exists, not a formality to route around. Once every rule is decided,
   it writes the accepted keys into a named profile in `settings/formats.yml`, points the deck's
   content yaml at it (`deck.format`), and builds a patch version
   `_v{major}.{minor}.{patch}+{descr}`.
4. **`verify`** answers two separate questions:
   - STRUCTURAL — rebuild the `base` content with the new profile and compare against her fork;
     residuals within `merge.tolerances` are expected because rules approximate hand-placed
     boxes, they don't reproduce them pixel-for-pixel.
   - INVARIANT — compare the merged build against `ours`; a formatting profile may not change
     what the deck SAYS, only how it looks.

## Run

From the course repo root. Paths are POSITIONAL and quoted by the recipe, so the fork's real
filename (spaces and parentheses) survives. The Justfile and `src/preza_merge/cli.py` are the
authoritative shapes — check them, not prose.

```bash
just preza-merge-propose <deck> <base> <ours> <theirs> <rev> [--profile NAME]
just preza-merge-apply   <proposal> --patch-of <major.minor> --descr <slug>
just preza-merge-verify  <proposal> <merged> [--contact-sheet]
just preza-merge-run     <deck> <base> <ours> <theirs> <rev> [--profile NAME]
```

`--patch-of` and `--descr` are REQUIRED on `apply` — without them it exits `Missing option
'--patch-of'`. They name the version being patched and the build tag: `--patch-of 3.19
--descr alina-fmt` produces `_v3.19.1+alina-fmt`.

`run` is NOT a one-shot pipeline. It runs `propose` and then STOPS at the decisions, printing
`дальше: проставьте decision: …` — because `apply` refuses to run while any rule is still
`decision: null`. That gate is the point of the lane; a command that skipped it would defeat it.

`<rev>` is `base-content-rev` — the commit whose content produced `base`. It is mandatory: without
it, her edit to `base` is indistinguishable from a content change we made ourselves between
versions. Path arguments containing spaces or parentheses (a reviewer's fork filename routinely
does, e.g. `"... v3.15 (1).pptx"`) must be quoted.

## Rules the lane knows how to detect

From the first real case (course manager's edits to a built dbt deck):

| rule | what it detects |
|---|---|
| R1 | bullets inherit the master's size |
| R2 | the visual (picture or code panel) is pinned to a bottom edge |
| R3 | tables sit lower under the title |
| R4 | the bullet column widens adaptively |
| R6 | empty placeholders are dropped |
| R7 | the title slide is uppercased (taste; default off) |
| R11 | the code panel's blue border is removed |

**R5 is explicitly NOT a rule** — code-panel font shrink-to-fit is what the generator's own
fitter already does; the diff finding it is not a merge candidate.

A change becomes a rule only when SYSTEMATIC — at least `merge.min_share` of the slides that
could carry it actually does. Below the threshold it stays a per-slide note in the report
instead of a rule. Documented per-rule overrides (e.g. a conditional rule like R4, or a
by-hand-applied one like R6) live in `settings/merge.yml → merge.min_share_overrides` — never
lower `min_share` itself to force a stubborn rule to fire.

## Invariants

1. **Edits go into the GENERATOR, never into one `.pptx`.** A merge written only to the file dies
   on the next build.
2. **`base` is mandatory.** Without it, her edit is indistinguishable from our own change between
   versions.
3. **A change becomes a rule only when SYSTEMATIC**, per the `min_share` gate above; anything
   rarer stays a per-slide note.
4. **Export artefacts of her editing tool are reported as REGRESSIONS, never merged** — swapped
   theme fonts, lost speaker notes, merged paragraphs. "Not merged" must never read as
   "overlooked": the report says so explicitly.
5. **The manager's written rules are an input alongside the diff**, not a fallback:
   `settings/config.yml → course_production.design` and `docs/course-rules.md`. R11 (blue
   code-panel border removed) was found that way, not by the pixel diff.
6. **Copying slides between `.pptx` files (the `graft` backend) is deliberately unimplemented**
   and raises — this lane derives generator rules, it does not splice binary slide content.
   When slides genuinely must move between two decks — two HAND-edited lines of the same deck
   that diverged, so there is no single source to port into the content YAML — that is a
   different lane: `/preza-graft` (`.tmp/graft_slides.py` + `.tmp/renumber_notes.py`).

## Routing

- BUILDING decks → the `preza-*` just recipes (`just build`, etc.).
- ACCENTS / content review → `/preza-review` and the `preza-accents-keeper` agent.
- PUBLISHING a finished deck → `just publish-new` (spec: `docs/deck-publish-pipeline.md`).
- This merge lane → the `preza-merge-keeper` sub-agent, or the recipes above directly.
