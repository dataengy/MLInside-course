# SDD ledger — plan: docs/plans/2026-08-26-preza-merge.md

Spec: docs/preza-merge-lane.md (reachable, read). Tracker: #8. Branch: feat/preza-merge.
Base at start: e6af47a (plan preflight fixes → c12d0a9).

## Ruling: branch instead of worktree
Repo carries 6 submodules + git-LFS data/. A worktree would need submodule re-init and a
second LFS materialization for no isolation this plan needs (no parallel implementers).
Cost if wrong: implementation shares the working tree with the user's other sessions —
mitigated by all work living on feat/preza-merge, never main.

## Preflight scan

### Task pairs sharing files / interfaces
| A | B | shared | A produces → B consumes | finding |
|---|---|--------|--------------------------|---------|
| 1 | 2 | utils.py, test_version.py | resolve_out_name(patch_of=, descr=) → _resolve_naming | ok |
| 2 | 12 | pipeline.build_deck | build_deck(patch_of=, descr=) → apply.run | ok |
| 3 | 2 | settings.Config | Config(fmt=, format_name=) → Task 2's test fixture | CONFLICT (ordering) |
| 3 | 4,5 | renderers/pptx.py, formats.yml | Config.fmt → cfg.fmt in render() | ok (3 does a stopgap edit 4 rewrites) |
| 4 | 5 | pptx.py render(), test_format_render.py | _add_code(border=), _mini_content/_build | CONFLICT (test helpers) |
| 4 | 15 | formats.yml alina profile | profile keys → apply/verify | ok |
| 7 | 8,9,10,13 | model.Deck/Shape | Shape.line_color → rules._r11; Deck.titles → align | ok |
| 8 | 10 | diff.DiffReport | runs_size_cleared/paras_*/notes_lost/theme_changed/counts | ok |
| 10 | 11 | rules.Finding, MergeConfig | Finding(kind/key/value) → report rows | ok |
| 11 | 12,13 | cli.py, report helpers | accepted_keys/undecided → apply.run; load_proposal → verify | ok |
| 12 | 15 | formats.yml, deck.format | write_profile/set_deck_format → merged build | ok |
| 3,4 | 12 | classic profile key set | write_profile rejects keys absent from classic | ok (code_border added to classic in 3) |
| 14 | — | .claude/settings.json, hooks | — | ok |

### Per-task self-consistency (own tests vs own code)
1 ok · 2 CONFLICT(see below) · 3 ok · 4 CONFLICT(see below) · 5 ok · 6 ok · 7 ok · 8 ok ·
9 ok · 10 ok · 11 CONFLICT(see below) · 12 ok · 13 ok · 14 ok (no code) · 15 ok

### Rulings
Ruling: Task 3 runs before Task 2 — Task 2's Config fixture uses fmt/format_name introduced
by Task 3. Already stated in the plan's «Порядок задач»; execution order is 1,3,2,4,5,…
Cost if wrong: Task 2 fails at import, one re-dispatch.

Ruling: Task 4's R11 test rewritten to use only Task-4 helpers (_build) and _mini_content
gained a code slide; each _build gets its own out dir. As written it called Task 5's
_build_content on a deck with no code panel — NameError, then IndexError. Fixed in c12d0a9.
Cost if wrong: the R11 renderer rule ships unverified.

Ruling: Task 11's report stem built as a string before joining to report_dir. `Path.replace`
is a filesystem rename and rejects two args — propose would have crashed. Fixed in c12d0a9.
Cost if wrong: propose crashes on first real run.

Ruling: Task 4's _drop_empty_placeholders compares XML elements, not shape proxies —
python-pptx returns a new proxy per shapes.title access, so `==` is unreliable. Fixed in
c12d0a9. Cost if wrong: an empty title could be dropped on some layouts.

## Progress
Task 1: dispatched (haiku, BASE c12d0a9)

## Ruling: review packages use the implementer's own commit range
A parallel session in this same working tree is committing its own lane (#7 course rules)
onto feat/preza-merge — ac7062c landed between my BASE and Task 1's commit. BASE..HEAD would
therefore hand reviewers foreign diffs. Every review package is built from the implementer's
reported SHAs instead (<first>^..<last>). Cost if wrong: a task's own change could be split
across non-contiguous commits and partially reviewed — checked per task against `git log`.

## Ruling: preza_gen changes commit inside the submodule
src/preza_gen is a git submodule (hnkovr/preza_gen); Tasks 1-5 land there and the parent repo
only records the pointer bump. Review packages for those tasks are built from the submodule's
own git. The submodule commits are UNPUSHED — pushing hnkovr/preza_gen is an outward-facing
action left for the finish step, flagged to the user.
Cost if wrong: submodule work invisible to reviewers (mitigated: packages built per-submodule).

Task 1: implemented (submodule 1a881f3, parent e8949da), 10 passed incl. 4 doctests
Task 1: review dispatched (sonnet)
Task 1: minor (deferred): task-1-report.md overstates its verification — `pytest src/preza_gen`
  resolves rootdir to the SUBMODULE pyproject (testpaths=tests, no --doctest-modules), so the
  reported run collected 0 doctests. Reviewer verified doctests do pass when invoked properly.
Task 1: minor (deferred): utils._EXTS strips only .pptx/.html/.pdf; a future export format would
  be swallowed into `descr` (latent, not live — those are the only formats build_deck emits).
Task 1: complete (submodule 1a881f3, parent e8949da, review clean — 2 minors deferred)

## Ruling: submodule test command must force doctests
Tasks touching src/preza_gen must run `python3 -m pytest src/preza_gen --doctest-modules -q`
AND a root-level `python3 -m pytest -q`; a bare `pytest src/preza_gen` silently skips doctests.
Carried into every later preza_gen dispatch. Cost if wrong: doctests rot unnoticed.

Task 3: dispatched (sonnet, spans submodule + parent repo)
Task 3: implemented (submodule 1a881f3..8dc7cc4, parent e8949da..0634f8e); doctests 37 passed,
  full suite 298 passed / 4 skipped (baseline 294/4); `just build` → 70 slides, throwaway v3.20
  artifacts removed (data/generated .pptx/.html + ~/Downloads hardlink)
Task 3: review dispatched (sonnet)
Task 3: minor (deferred): settings.py:143 `d.get("format", "classic")` is an inline default,
  in tension with the module's own no-inline-defaults docstring (came verbatim from the brief).
Task 3: minor (deferred): missing-`formats_file` FileNotFoundError is implemented but untested.
Task 3: Ruling: the `format` default stays. Five other decks (prefect, cicd, airflow, ogip,
  dagster) carry no `format:` key, and `classic` IS today's behaviour — requiring the key would
  break every deck that never opted into a profile. This is back-compat, not a config scalar.
  Cost if wrong: a future content yaml that omits `format:` silently renders classic instead of
  failing — visible on first build, cheap to catch.
Task 3: complete (submodule 8dc7cc4, parent 0634f8e, review clean — 2 minors deferred)
Task 2: dispatched (haiku, BASE parent 0634f8e / sub 8dc7cc4)
Task 2: implemented (submodule 8dc7cc4..1a41fcd, parent 0634f8e..284a62d); 299 passed / 4 skipped.
  Unplanned but necessary edit: tests/test_pdf.py mock of _resolve_naming updated for new kwargs.
Task 2: review dispatched (sonnet); Task 4: dispatched in parallel (sonnet, disjoint files)
Task 2: complete (submodule 1a41fcd, parent 284a62d, review clean — no findings)
Task 4: implemented (submodule b20128c, parent 0c88400) — awaiting report
Task 4: 42 doctest-mode passed, full suite 303/4 (baseline 299/4); LFS template materialized so
  all 4 render tests really ran; just build → 70 slides, throwaways removed.
Task 4: review dispatched (sonnet); Task 5: dispatched in parallel (sonnet)
Task 4: review — spec ✅, quality Approved with 1 Important + 1 Minor.
  IMPORTANT (open): _drop_empty_placeholders also strips the body placeholder on section/closing
  slides and an empty subtitle on the title slide; untested for that scenario. Behaviour matches
  what the fork did (R6 exists to do exactly this) → fix = pin it with a test, not change code.
  minor (deferred): _add_code's border=="none" branch unreachable by any current profile.
  note (deferred, pre-existing): render() has no branch for kind=="closing", so bullets on a
  closing slide were silently dropped before this plan; R6 now also removes the empty box.
Task 4: Ruling: its fix round waits until Task 5 reports — both touch renderers/pptx.py and the
  fix is additive (a test). Cost if wrong: one extra rebase-ish edit; no behavioural risk.
Task 5: implemented (submodule c3a422f) — awaiting report
Task 5: implemented (submodule c3a422f, parent 6c52799); 310 passed / 4 skipped (baseline 303/4).
  KEY EVIDENCE: across 42 code panels + pictures of the real dbt deck under alina-2026-08 the
  bottom edge is 7.0000" (range 6.999998..7.0) — the fork's median was 6.98-7.02. R2 reproduces.
Task 4: fix round 1/5 dispatched (resumed original implementer) — pin R6 on section/title slides
Task 5: review dispatched (sonnet)
Task 5: minor (deferred): `if spec.code:` now computes code_box even when spec.image is also set
  (was elif); result discarded, no drift, just wasted work on the rare image+code slide.
Task 5: complete (submodule c3a422f, parent 6c52799, review clean — 1 minor deferred)
Task 4: fix round 1/5 (1 addressed, 0 open; submodule c3a422f..e037dd9, parent bb47266) —
  3 covering tests, 313 passed / 4 skipped, no production code touched
Task 4: re-review dispatched (haiku, test-only diff); Task 6: dispatched in parallel (haiku)
Task 4: complete (submodule b20128c..e037dd9, parent 0c88400..bb47266; fix round 1 ADDRESSED)
Task 6: implemented (parent 54f5513); 317 passed / 4 skipped; publish-status runs clean
  (note: the implementer quoted the Dagster line, not the dbt one — cosmetic reporting slip)
Task 6: review dispatched (haiku); Task 7: dispatched in parallel (sonnet, new package)
Task 6: complete (parent 54f5513, review clean — no findings)
Task 7: implemented (parent 612e23d), 322 passed / 4 skipped. DONE_WITH_CONCERNS: the brief's
  own test_text_joins_runs... selected the TITLE shape (it lacked the shapes_title_name exclusion
  its neighbour has); implementer fixed that one line, model.py byte-identical to the brief.
  SMOKE (real decks): ours 57 slides/18 panels/borders ['2419FF']/59 links/Corbel;
  fork 57/18/['tx1']/59/Calibri — the model sees every signal the rules need.
Task 7: Ruling: accept the implementer's test-line fix. The plan's test was wrong, the model was
  right; forcing the brief's text would have pinned a test that asserts the wrong shape.
  Cost if wrong: none — the corrected test is strictly more specific.
Task 7: review dispatched (sonnet); Task 8: dispatched in parallel (sonnet)
Task 7: minor (deferred): dead constants model.py _EMU_IN, _RUN_KEYS; test_bottom_edge_is_derived
  is tautological; no test for the empty theme/master degrade path. All inherited from the brief.
Task 7: complete (parent 612e23d, review clean — 3 minors deferred)
Task 8: implemented (parent 6d26f60), 328 passed / 4 skipped.
  SMOKE (real decks): counts {notes 1, shapes 5, font 40, geometry 43, paragraph 2, text 1,
  theme 1}; 203 runs size-cleared; text change ONLY on slide 23; notes lost on slide 1.
  Reproduces the controller's manual analysis exactly — run-joining kills the round-trip noise.
Task 8: review dispatched (sonnet); Task 9: dispatched in parallel (haiku)
Task 8: minor (deferred) x3: zip(pa.runs, pb.runs) truncates so a pure run add/remove with no
  size/text delta is untracked; runs_size_cleared is one-directional (size→None only);
  bold/italic/underline/font are modelled but never compared though the class is named "font".
Task 8: complete (parent 6d26f60, review clean — 3 minors deferred)
Task 9: implemented (parent 1d2e766), 333 passed / 4 skipped.
  SMOKE: 74 rows — 53 unchanged + 3 dropped + 1 both (= 57 base slides) + 16 ours-only
  + 1 theirs-only; unaligned []. Reconciles exactly: the 3 dropped are the SQLMesh slides
  3.18 replaced, 16 ours-only = 13 net-new + 3 replacements, and the both/theirs-only pair is
  the title slide whose fork copy was upper-cased (R7) so its title no longer matches.
Task 9: review dispatched (haiku); Task 10: dispatched in parallel (sonnet, largest module)
Task 9: minor (deferred): align3's parameters lack type hints (align.py:76).
Task 9: complete (parent 1d2e766, review clean — 1 minor deferred)
Task 10: implemented (parent facdd90), 340 passed / 4 skipped. DONE_WITH_CONCERNS:
  R2/R3/R7/R11 + R8/R9/R10 reproduce the manual analysis exactly (visual_bottom 7.01 over 33/34
  elements; table_top 2.47 on 9/9; code_border dark on 18/18; theme swap; merged paras slide 23;
  notes lost slide 1). R1, R4, R6 did NOT fire.
Task 10: controller investigation — the detectors' share denominators are the defect, not the
  threshold. Measured directly:
    R1  40/44 = 0.909 when the cohort is "base slides that HAD explicitly-sized runs"
        (the brief used "slides with any paragraphs" = 56, diluting it to 0.714).
        The 4 non-hits (25,26,33,50) are table slides whose only sized runs live in cells.
    R4  27/34 = 0.794 when the cohort is "body placeholder sharing the slide with a visual"
        (the brief used all 40 body slides). 7 visual slides were not widened.
    R6  5/7 = 0.714 on the correct cohort already; the manager simply skipped two section
        slides (38, 45) by hand.
Task 10: Ruling: fix R1's cohort (a real denominator bug) AND add per-rule threshold overrides
  in settings/merge.yml for R4 (0.75) and R6 (0.70), each carrying its reason in the file.
  Why this is not tuning-to-fit: min_share exists to separate systematic intent from a one-off,
  and 27/34 + 5/7 are plainly intent. R4 in particular proposes a CONDITIONAL behaviour — the
  generator's `adaptive` widens only where the text clears the visual, which is exactly why the
  manager widened only some slides; measuring a conditional rule against an unconditional
  denominator can never reach 0.8. 0.8 was my pre-data guess; per-rule, documented overrides
  are honest, a silent global lowering would not be.
  Cost if wrong: R4/R6 could fire on a future fork where the manager touched only ~70% of slides
  deliberately — visible in the proposal's evidence line, and the human can answer `reject`.
Task 10: fix round 1/5 dispatched (resumed implementer)
Task 10: fix round 1/5 (3 addressed, 0 open; parent facdd90..9cb0849), 343 passed / 4 skipped.
  ALL rules now fire — verified independently by the controller running the detector:
  R1 0.91 · R2 0.97 (7.01") · R3 1.00 (2.47") · R4 0.79 · R6 0.71 · R7 1.00 · R11 1.00 (18/18)
  + regressions R8 theme, R9 slide 23, R10 slide 1.
Task 10: re-review dispatched (sonnet); Task 11: dispatched in parallel (sonnet)
Task 10: review (original+fix1) — spec ✅, Approved with 1 Important + 1 Minor.
  IMPORTANT (open): no tests for _r2's outlier/decline branches nor _r3/_r6 positive fire.
  minor: MergeConfig.threshold() silently falls back for an unknown rule id (typo'd override).
Task 10: fix round 2/5 dispatched (resumed implementer) — tests + fail-loud override validation
Task 10: fix round 2/5 (1 Important + 1 minor addressed; parent 9cb0849..c8745b7), 38 tests in
  the package; smoke shares unchanged. Implementer correctly scoped its git add around Task 11's
  concurrent uncommitted work in the same tree and reconciled the suite count.
Task 10: re-review dispatched (haiku, test-only diff)
Task 11: implemented (parent 0278555) — awaiting report
Task 11: implemented (parent 0278555), 355 passed / 4 skipped. DONE_WITH_CONCERNS:
  (a) found + fixed a REAL bug beyond the brief: report.write used Path.with_suffix, which
      truncates at the LAST dot — deck names always carry a version dot (v3.19), so different
      merges silently collapsed onto one output filename.
  (b) `just preza-merge-propose` breaks on the --theirs path (spaces + parens) — just's *ARGS
      splits on whitespace. Pre-existing repo-wide pattern, but FATAL here: the fork's filename
      always contains " (1)".
  Real run (module invoked directly): 7 rules + 3 regressions, exit 0, unaligned empty.
Task 11: Ruling: (b) must be fixed, not documented. The Justfile recipe is the lane's canonical
  entry point and the ONE path it will always be handed contains spaces and parens. The repo
  already solves this in `preza-import-pptx` with a named parameter + {{quote(...)}} — the merge
  recipes follow that precedent. Cost if wrong: none; the *ARGS passthrough stays for flags.
Task 11: review dispatched (sonnet); fix round 1/5 dispatched in parallel (Justfile quoting)
Task 10: fix round 2 re-review — both findings ADDRESSED, detectors untouched, shares identical.
Task 10: complete (parent 1d2e766..c8745b7 incl. 2 fix rounds, review clean)
Task 11: review — spec ✅ (with_suffix deviation verified TRUE and correctly fixed), Approved.
  minor (deferred): accepted_keys' dict-expansion (R2) and undecided's reject-exclusion are
  correct by trace but untested; cli._content_at_rev is dead code until Task 12/13 uses it.
Task 11: fix round 1/5 (1 addressed, 0 open; parent 0278555..e9869cb) — just recipes take named
  path params through quote(); verified end to end THROUGH just with the fork's real path
  (spaces + parens) → exit 0. +1 test pinning that two `ours` versions get different stems.
Task 11: re-review dispatched (haiku); Task 12: dispatched in parallel (sonnet)
Task 11: fix re-review — ADDRESSED, entry point verified through just with the fork path
  (exit 0, «правил: 7 · регрессий: 3»), no new breakage.
Task 11: complete (parent c8745b7..e9869cb incl. fix round 1, review clean — 2 minors deferred)
Task 12: implemented (parent f0f4502), 362 passed / 4 skipped. apply.run exercised end-to-end on
  COPIES (real build ran, repo files untouched — verified by git status).
  Declared deviation: `apply` takes the proposal as a positional click.argument, matching the
  existing `preza-merge-apply proposal *ARGS` recipe rather than the brief's --proposal option.
Task 12: review dispatched (sonnet); Task 13: dispatched in parallel (sonnet)
Task 12: review — spec ✅ (positional proposal arg verified coherent with Justfile:179), Approved.
  minor (deferred): set_deck_format's regex is not scoped to the `deck:` block — safe on the real
  content file (one `format:` line, at line 8) but correct by data shape, not by design.
  → carried into Task 15: after apply, confirm the content yaml diff is EXACTLY one line.
  minor (deferred): the undecided-gate test proves "no write" only indirectly (brief-inherited).
Task 12: complete (parent f0f4502, review clean — 2 minors deferred)
Task 13: implemented (parent 682418b), 367 passed / 4 skipped. LibreOffice present but the
  contact_sheet path is not exercised by any test (optional convenience, not a gate).
  Declared deviation: verify takes positional args, matching the Justfile recipe (as instructed).
Task 13: review dispatched (sonnet); Task 14: dispatched in parallel (sonnet, hook+agent)
Task 13: review — spec ✅, NOT approved: 2 Important, both plan-mandated (my brief's snippet).
  Ruling 1: invariants() compares titles case-insensitively on EVERY slide though R7 only
  uppercases slide 1 → restrict the exception to the first slide, exact elsewhere. Cost if
  wrong: a deliberate deck-wide case change would need the test updated — trivial.
  Ruling 2: a missing tolerance key silently skipped its geometry check → make it raise,
  validating every diff._GEOM_ATTRS has a tolerance. Cost if wrong: none; it is fail-loud.
  minor: a weak `any("1" in m)` assertion in test_verify.
Task 13: fix round 1/5 dispatched (resumed implementer)
Task 14: implemented (parent 80acc25), 367 passed / 4 skipped. Hook works: names the real fork
  candidate AND the undecided proposal; genuine fail-open confirmed (the implementer noticed the
  brief's /tmp check was invalid because BASH_SOURCE resolves absolutely, and tested properly).
  Registered alongside the 5 existing hooks. Skill NOT created — left to the controller per policy.
Task 14: review dispatched (haiku)
Task 14: review — spec ✅, Approved (no findings). Controller then caught what the review missed,
  visible in its own captured output: the hook prints a flag-style command with an UNQUOTED,
  120-char-TRUNCATED path, while Task 11's fix changed the recipe to five POSITIONAL params.
  The printed command cannot run — and printing a runnable command is the hook's whole contract.
Task 14: Ruling: fix the hook to print the real signature with quoted paths and no truncation,
  discovering deck/ours/base (the fork's own version number names the base build) and using an
  obvious placeholder for the git rev it cannot derive. Cost if wrong: a slightly wrong base
  guess, visible to the human before they run it.
Task 14: fix round 1/5 dispatched (resumed implementer)
Task 13: fix round 1/5 (2 Important + 1 minor addressed; parent c38092c), 369 passed / 4 skipped.
  Second-order fix the implementer found on its own: the title's text also flows through the
  general shape-text comparison, so a title-only helper was needed for the R7 exception to hold.
Task 14: fix round 1/5 (1 Important addressed; parent 4ba0dfe). Printed command now positional
  and quoted; the implementer RAN it (exit 0, 7 rules / 3 regressions) and re-checked fail-open.
Task 13/14: scoped re-reviews dispatched (haiku)
Task 13: fix re-review — all 3 findings ADDRESSED; the second-order _texts() helper judged
  correct and minimal (uppercases only the title shape, only on slide 1). No new breakage.
Task 13: complete (parent 682418b..c38092c incl. fix round 1, review clean)
Task 14: fix re-review — ADDRESSED; hook's printed command runs (exit 0, 7 rules / 3 regressions),
  paths shlex-quoted, base derived from the fork's version with a placeholder fallback,
  fail-open intact, 5-entry cap kept.
Task 14: complete (parent 80acc25..4ba0dfe incl. fix round 1, review clean)
Task 15: dispatched (sonnet) — the supervised merge itself
Task 15: complete (parent 4fb9265). Merge REAL and verified independently by the controller:
  70 slides · panel borders 1A1A1A only (no 2419FF) · all 42 visual bottoms at 7.01" ·
  table tops 2.47" · 263 body runs with NO explicit size (was 26/20/17pt) · adaptive column
  full-width on 10 of 42 visual slides. R7 rejected (title caps — owner's taste, not asked for).
  Implementer caught and corrected a drifted `profile: merged` in the uncommitted proposal.
TWO OPEN ITEMS carried into the final review:
  (1) IMPORTANT — verify_cmd rebuilds the historical BASE content WITHOUT injecting the decided
      profile, so the structural half compares an unformatted classic rebuild against the fork;
      it exits 1 with ~30 residuals that are largely an artefact of that. My plan's defect.
  (2) IMPORTANT — `just check` is RED: 7 ruff errors, ALL in src/preza_merge (ruff is green on
      main — measured). ty went 56 → 61 diagnostics, 2 of them in preza_merge. The Global
      Constraint says just check must stay green; the Task 15 report mis-attributed this to
      pre-existing debt.
Final review dispatched (opus-class) with both items named.
FINAL REVIEW (opus): 3 Critical + 3 Important; confirmed both controller items with measurements
  (profile injection: 110→80 mismatches, font slides 40→7). Verified GOOD: `classic` is
  BYTE-IDENTICAL for all six never-opted-in decks (it unzipped both builds and compared parts).
FINAL FIX WAVE (parent eb5f66b): all 7 fixed. ruff green; ty 60 pre-existing, none in preza_merge;
  tests 371 passed / 4 skipped. Measured residuals: left med 0.19 max 1.15 · top med 0.37 max 1.14
  · width med 0.99 max 5.40 · height med 0.49 max 1.26. Tolerances left/top/height 0.45, width 5.5.
  verify FINAL: RED, honestly — 45 mismatches / 19 slides (top 27, height 14, left 4, width 0);
  invariants CLEAN (slides, links 81, footers 43, notes 70 all match).
Skill /preza-merge created via /create-skill (catalog docs/pptx, validate OK, claude+codex+hub).
Final fix re-review dispatched (sonnet)
FINAL FIX RE-REVIEW: 6 of 7 ADDRESSED and independently reproduced (verify's 45/19 reproduced
  live; ruff exit 0; 371 passed / 4 skipped; no new breakage).
  2(b) called out as half-honest: left/top/height got a principled 0.45" bound and the residuals
  were REPORTED not hidden, but `width: 5.5` was fitted to the observed maximum (5.40) — on a
  13.3" slide that absorbs ~90% of R4's entire 6.1" binary span and functionally disables the
  width check as a regression guard.
FINAL Ruling (parked, surfaced to the user): the reviewer is right; 5.5 is not a tolerance, it is
  a disabled check wearing a number. It changes nothing about the delivered deck and hides nothing
  today (width mismatches are currently 0). Its real cost is future: a fork where R4 genuinely
  fails to reproduce — say the manager NARROWS a column the rule widens — would pass unreported.
  The honest form is an explicit "width is not a structural check under R4" exclusion rather than
  a fitted number. Not fixed here: there is no second fix wave, and this is the user's call.
BRANCH COMPLETE.
