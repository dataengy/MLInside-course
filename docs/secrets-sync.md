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

```bash
git clone --recurse-submodules https://github.com/dataengy/MLInside-course.git
cd MLInside-course
brew install bitwarden-cli gnupg git-secret git-lfs just uv   # missing pieces only

bw login hnkovr@gmail.com
export BW_SESSION=$(bw unlock --raw)
just secrets-bootstrap      # Bitwarden pull → (fallback) gpg-key pull + git-secret reveal → doctor
```

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
