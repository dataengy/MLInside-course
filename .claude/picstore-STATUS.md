# picstore — build status (session 2026-07-27/28)

Plan: `/Users/nk.myg/.claude/plans/let-s-create-submodule-4-expressive-nova.md`
Repo: `hnkovr/picstore` · mounted at `src/picstore`

## Shipped (committed, gates green)

| phase | what | picstore | host |
|---|---|---|---|
| 0 | `id:` slide key on `SlideSpec` + skill `SLIDE_KEYS` | `preza_gen@3fd74bd` | `1371fd4` |
| 1 | skeleton: settings SSoT, provider contract, `doctor` | `cb0b20a`, `a19fe62` | `858cd98` |
| 2 | sqlite catalog + deterministic XML + 208 slide ids | `7b2a6be` | `ffab5c2` |

Gates at time of writing: 105 picstore tests + doctests pass · `ruff check src` clean ·
host `pytest src --ignore=src/orchestration` exit 0 · 1 `ty` diagnostic (optional
`playwright` import) vs 24 pre-existing repo-wide.

`just picstore-doctor` → local ✓ · commons ✓ · openverse ✓ · websearch ✗ (no key) ·
shots ✗ (opt-in, disabled).

## OPEN BLOCKERS — need a decision

1. **Host remote does not resolve.** `git push` fails with
   `remote: Repository not found` for `https://github.com/dataengy/MLInside-course.git`;
   `gh` cannot resolve it either, though both `hnkovr` and `dataengy` accounts are
   authenticated and git-lfs already tracks 48 objects against that endpoint. **8 host
   commits are unpushed.** Options: recreate the repo, `gh auth switch -u dataengy`, or
   re-point `origin`. NOT actioned — changing which account/URL a repo pushes to is the
   user's call. Both submodules ARE pushed, so no dangling-gitlink risk.
2. **dbt deck fails the validator** on a missing provenance stamp
   (`— Сгенерировано:`). **Pre-existing** — absent at HEAD too, and precisely why
   `preza-validate-all` excludes that deck. Means dbt has no working validation gate.
3. **A concurrent session is active in this repo.** `src/schedule/`, `integrations/`,
   `content/presentations.yml`, `docs/reviews/`, the `gsheets` extra in the root
   `pyproject.toml`, and the `preza-review*` Justfile recipes are all theirs. **Never
   `git add -A` here.** For shared files (Justfile) stage a synthesized blob of
   `HEAD` + only your own hunk (`git hash-object -w` + `git update-index --cacheinfo`).

## Plan corrections learned the hard way

- The skill hardlink port covers **only `SKILL.md`**, not `scripts/` — editing
  `preza_schema.py` breaks no inode, so the plan's re-port step was unnecessary.
- The id backfill needs **two** guards, not one. A test proved the structural
  before/after gate alone is foolable: YAML lets the last duplicate key win, so an
  injected `title:` the slide also defines parses away silently while still leaving a
  bogus line in the file. Primary guard is now token validation
  (`^[A-Za-z0-9][A-Za-z0-9._-]*$`) at the source; the structural diff is the backstop.
- `ids._dedupe` is near-dead code: the `{idx:03d}` prefix already makes ids unique. Kept
  as defence if `ids.pattern` is ever changed to drop the index.
- LFS rules **must** stay path-scoped to `data/images/**`; a bare `*.png` would claim the
  72 plain-git blobs in `data/source/media/` and require `git lfs migrate`.

## Next — phase 3 (task #4)

Local provider + ranking + review artifacts, in `src/picstore/`:

- `providers/local.py` — walk `data/source/media` + `data/media`; skip `.wdp`/`.svg`
  **by extension, never a bare except** (PIL cannot open them); reuse
  `.tmp/contact_sheet.py`'s rels-parsing to recover the source-deck slide→image map.
- `images.py` — PIL probe, dhash, `classify_type` (deterministic colour-count / edge-
  density / axis-run heuristic).
- `query.py` — `queries_for(slide, types, styles)`; RU handled by the offline lexicon
  (`text.search_terms` already built and tested); transliteration is for slugs ONLY.
- `rank.py` — 6-part weighted score from `ranking.weights`; aspect peaks at 1.10;
  <900px scores 0 on resolution; dhash ≤ 6 suppressed across the whole deck.
- `review.py` — `contact-sheet.png` + `review.html` + `review-<deck>.yml` (write surface).

**Acceptance:** the dbt contact sheet reproduces that deck's existing 16 image↔slide
pairings.

Then phases 4–7 per the plan file. Phase 4 carries the load-bearing fix:
`src/preza_gen/renderers/html.py:23` hardcodes the media dir and ignores `cfg.media_dir`
— without fixing it the apply path *looks* correct while producing image-less HTML.
