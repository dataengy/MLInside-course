# Secrets sync — new-workstation bootstrap

`settings/.env.secrets` (gitignored, 15 vars — names in
[`settings/.env.secrets.template`](../settings/.env.secrets.template)) travels between
workstations over two independent lanes. Engine: `scripts/secrets-sync.sh`; all commands
below are `just` recipes. Neither lane ever commits a plaintext secret.

| lane | transport | what's needed on the new machine |
|---|---|---|
| **Bitwarden** (primary) | secure notes in the personal vault (`bw` CLI) | `bw login` + master password |
| **git-secret** (in-repo fallback) | GPG-encrypted `settings/.env.secrets.secret`, committed | the GPG private key (itself fetchable from the vault) |

## Old workstation — publish the secrets (one-time, and after every change)

```bash
export BW_SESSION=$(bw unlock --raw)   # master password prompt
just secrets-push                      # .env.secrets → vault note "MLInside-course/.env.secrets"

# optional but recommended — arm the in-repo fallback too:
just secrets-gpg-init                  # generate + enroll a GPG key (pinentry passphrase)
just secrets-hide                      # writes settings/.env.secrets.secret → commit it
bash scripts/secrets-sync.sh bw-push-gpg   # park the GPG private key in the vault

# file-typed secrets (service-account JSONs) go as base64 notes:
bash scripts/secrets-sync.sh bw-push-file "$GOOGLE_APPLICATION_CREDENTIALS"
```

## New workstation — bootstrap

**Order matters: `git-lfs` must exist before the clone.** The repo keeps 72 LFS objects
(~1.2 GB of `.pptx` / `.pdf` / `.zip` decks and source materials); cloning without git-lfs
silently checks them out as text pointer stubs, and every deck command then fails on a file
that looks present.

```bash
# 1 — toolchain FIRST (missing pieces only)
brew install git-lfs just uv bitwarden-cli gnupg git-secret
git lfs install                       # once per machine

# 2 — clone with submodules (6 of them) and LFS payload
git clone --recurse-submodules https://github.com/dataengy/MLInside-course.git
cd MLInside-course
git lfs pull                          # no-op if step 1 preceded the clone; the repair if it didn't

# 3 — Python deps
just sync                             # uv sync --extra dev --extra gsheets

# 4 — secrets
bw login hnkovr@gmail.com
export BW_SESSION=$(bw unlock --raw)
just secrets-bootstrap                # Bitwarden pull → (fallback) gpg-key pull + git-secret reveal → doctor

# 5 — gate
just secrets-doctor                   # must exit 0
just test                             # 371 passed / 4 skipped as of 2026-08-26
```

Two known traps on a fresh machine:

- **`uv.lock` is git-ignored**, so dependencies re-resolve from `pyproject.toml` ranges instead
  of being pinned — the new machine can legitimately get different versions.
- **`just test` runs `python3 -m pytest`, i.e. whatever `python3` resolves to on `PATH`**, not
  the `.venv` that `just sync` builds. On this workstation that happens to be a framework
  Python 3.13 with the deps installed globally. On a clean machine the gate fails until the
  deps are in the ambient interpreter too; `uv run python -m pytest` runs green inside the venv
  (and collects *more* tests than the ambient interpreter does).

`secrets-bootstrap` is safe to re-run; it ends with `secrets-doctor`, which checks tools,
vault status, GPG key presence, template drift, that file-typed secrets
(`YC_SERVICE_ACCOUNT_KEY_FILE`, `GOOGLE_APPLICATION_CREDENTIALS`) point at existing files,
and that the **publish-lane credentials named in [`settings/publish.yml`](../settings/publish.yml)
exist** — pull missing ones with
`bash scripts/secrets-sync.sh bw-pull-file <item-name> <dest-path>`.

## What `.env.secrets` does NOT carry

`settings/.env.secrets` is currently a **names-only skeleton — all 16 values are blank**, so
both lanes above escrow an empty file. Everything this repo actually authenticates with lives
in files *outside* the repo, and `.env.secrets` does not point at them (its
`GOOGLE_*` vars are blank too). They must be escrowed **individually**, or the new
workstation gets a green `secrets-doctor` and a dead publish lane:

| file | used by | escrow (old machine) → restore (new machine) |
|---|---|---|
| `~/.config/gcloud/application_default_credentials.json` | Drive upload (`just publish-new`), user-ADC `hnkovr@gmail.com`, scope `drive.file` | `bw-push-file` → `bw-pull-file 'MLInside-course/files/application_default_credentials.json' ~/.config/gcloud/application_default_credentials.json` |
| `~/.secrets/google-sa-for-prodamus-1-494316.json` | schedule sheet read + sheet columns, SA `gsheets-reader@…` | `bw-push-file` → `bw-pull-file 'MLInside-course/files/google-sa-for-prodamus-1-494316.json' ~/.secrets/google-sa-for-prodamus-1-494316.json` |

```bash
# old machine, vault unlocked — escrow both (values never printed):
export BW_SESSION=$(bw unlock --raw)
bash scripts/secrets-sync.sh bw-push-file ~/.config/gcloud/application_default_credentials.json
bash scripts/secrets-sync.sh bw-push-file ~/.secrets/google-sa-for-prodamus-1-494316.json
```

The ADC file is a refreshable OAuth token, not a permanent key: re-consenting on the new
machine (`just -f ~/.ai/scripts/gcloud/Justfile adc-login account=hnkovr@gmail.com`) is an
equally valid restore path — see [`deck-publish-pipeline.md`](deck-publish-pipeline.md) for the
scope traps (`drive` and `spreadsheets` are both blocked in that client).

## Rules

- **Plaintext never enters git.** `.gitignore` blocks `settings/.env.secrets`; only the
  `.secret` GPG blob and the blank-value template are committed.
- **The template is a names contract.** Add a var → add its NAME to
  `settings/.env.secrets.template` (value stays blank); `just secrets-doctor` flags drift.
- **Rotation** = edit `settings/.env.secrets` → `just secrets-push` (+ `just secrets-hide`
  and commit, if the git-secret lane is armed).
- The vault item names are fixed: `MLInside-course/.env.secrets`,
  `MLInside-course/git-secret-gpg-key`, `MLInside-course/files/<basename>`.
