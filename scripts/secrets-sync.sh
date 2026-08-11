#!/usr/bin/env bash
# scripts/secrets-sync.sh — sync settings/.env.secrets across workstations.
#
# Two lanes, both optional, both idempotent (runbook: docs/secrets-sync.md):
#   Bitwarden lane (transport):  bw-push / bw-pull — secure notes in the personal vault.
#   git-secret lane (in-repo):   hide / reveal     — GPG-encrypted copy committed to git.
#
# The Bitwarden lane needs an unlocked vault:  export BW_SESSION=$(bw unlock --raw)
# The git-secret lane needs a GPG key:         scripts/secrets-sync.sh gpg-init
#
# New workstation bootstrap:  just secrets-bootstrap

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SECRETS_FILE="settings/.env.secrets"
TEMPLATE_FILE="settings/.env.secrets.template"
BW_ITEM_ENV="MLInside-course/.env.secrets"
BW_ITEM_GPG="MLInside-course/git-secret-gpg-key"
BW_ITEM_FILE_PREFIX="MLInside-course/files"
GPG_UID="${MLINSIDE_GPG_UID:-$(git -C "$REPO_ROOT" config user.email 2>/dev/null || echo '')}"

log()  { printf '»» %s\n' "$*"; }
warn() { printf 'WARN: %s\n' "$*" >&2; }
die()  { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
need() { command -v "$1" >/dev/null 2>&1 || die "'$1' not installed — $2"; }

# ── Bitwarden helpers ─────────────────────────────────────────────────────────

bw_require_unlocked() {
    need bw "brew install bitwarden-cli"
    local st
    st="$(bw status 2>/dev/null | python3 -c 'import json,sys; print(json.load(sys.stdin)["status"])')" \
        || die "bw status failed"
    [ "$st" = "unlocked" ] || die "Bitwarden vault is '$st' — run: export BW_SESSION=\$(bw unlock --raw)"
}

# Print the id of the vault item with EXACTLY this name, or nothing.
bw_item_id() {
    bw list items --search "$1" 2>/dev/null | NAME="$1" python3 -c '
import json, os, sys
items = [i for i in json.load(sys.stdin) if i.get("name") == os.environ["NAME"]]
if items: print(items[0]["id"])'
}

# Create-or-update a secure note. $1 = item name, $2 = file whose content becomes notes.
bw_upsert_note() {
    local name="$1" src="$2" id
    id="$(bw_item_id "$name")"
    if [ -n "$id" ]; then
        bw get item "$id" | CONTENT="$(cat "$src")" python3 -c '
import json, os, sys
item = json.load(sys.stdin)
item["notes"] = os.environ["CONTENT"]
print(json.dumps(item))' | bw encode | bw edit item "$id" >/dev/null
        log "bw: updated '$name'"
    else
        bw get template item | NAME="$name" CONTENT="$(cat "$src")" python3 -c '
import json, os, sys
item = json.load(sys.stdin)
item.update(type=2, name=os.environ["NAME"], notes=os.environ["CONTENT"],
            secureNote={"type": 0}, login=None)
print(json.dumps(item))' | bw encode | bw create item >/dev/null
        log "bw: created '$name'"
    fi
}

bw_fetch_note() {  # $1 = item name, $2 = destination file
    local id
    id="$(bw_item_id "$1")"
    [ -n "$id" ] || die "bw: no item named '$1' in the vault — push from the old workstation first"
    bw get notes "$id" > "$2"
    chmod 600 "$2"
    log "bw: '$1' → $2"
}

# ── Commands ──────────────────────────────────────────────────────────────────

cmd_bw_push() {
    bw_require_unlocked
    [ -f "$REPO_ROOT/$SECRETS_FILE" ] || die "$SECRETS_FILE not found"
    bw sync >/dev/null || warn "bw sync failed — pushing against the local vault cache"
    bw_upsert_note "$BW_ITEM_ENV" "$REPO_ROOT/$SECRETS_FILE"
}

cmd_bw_pull() {
    bw_require_unlocked
    bw sync >/dev/null || warn "bw sync failed — pulling from the local vault cache"
    bw_fetch_note "$BW_ITEM_ENV" "$REPO_ROOT/$SECRETS_FILE"
}

# Any file (e.g. YC / Google service-account JSONs) → base64 secure note, and back.
cmd_bw_push_file() {
    local src="${1:?usage: bw-push-file <path> [item-name]}"
    local name="${2:-$BW_ITEM_FILE_PREFIX/$(basename "$src")}"
    [ -f "$src" ] || die "no such file: $src"
    bw_require_unlocked
    bw sync >/dev/null || true
    local tmp; tmp="$(mktemp)"; trap 'rm -f "$tmp"' RETURN
    base64 < "$src" > "$tmp"
    bw_upsert_note "$name" "$tmp"
}

cmd_bw_pull_file() {
    local name="${1:?usage: bw-pull-file <item-name> <dest-path>}" dest="${2:?dest path required}"
    bw_require_unlocked
    bw sync >/dev/null || true
    local tmp; tmp="$(mktemp)"; trap 'rm -f "$tmp"' RETURN
    bw_fetch_note "$name" "$tmp"
    mkdir -p "$(dirname "$dest")"
    base64 -d < "$tmp" > "$dest"
    chmod 600 "$dest"
    log "decoded → $dest"
}

cmd_gpg_init() {
    need gpg "brew install gnupg"
    need git-secret "brew install git-secret"
    [ -n "$GPG_UID" ] || die "no git user.email and MLINSIDE_GPG_UID unset — cannot pick a key UID"
    if gpg --list-secret-keys "$GPG_UID" >/dev/null 2>&1; then
        log "gpg: secret key for $GPG_UID already exists"
    else
        log "gpg: generating a key for $GPG_UID (pick a passphrase in the pinentry dialog)"
        gpg --quick-generate-key "$GPG_UID" future-default default 2y
    fi
    ( cd "$REPO_ROOT" && git secret tell "$GPG_UID" ) || true
    log "git-secret: $GPG_UID enrolled — 'just secrets-hide' now works"
}

cmd_hide() {
    need git-secret "brew install git-secret"
    [ -d "$REPO_ROOT/.gitsecret" ] || die ".gitsecret/ missing — run: git secret init"
    [ -f "$REPO_ROOT/$SECRETS_FILE" ] || die "$SECRETS_FILE not found"
    cd "$REPO_ROOT"
    git secret list 2>/dev/null | grep -qx "$SECRETS_FILE" || git secret add "$SECRETS_FILE"
    git secret hide -F
    log "encrypted → ${SECRETS_FILE}.secret (commit it)"
}

cmd_reveal() {
    need git-secret "brew install git-secret"
    cd "$REPO_ROOT"
    git secret reveal -f
    chmod 600 "$SECRETS_FILE" 2>/dev/null || true
    log "decrypted → $SECRETS_FILE"
}

cmd_bw_push_gpg() {
    need gpg "brew install gnupg"
    [ -n "$GPG_UID" ] || die "no key UID (git user.email / MLINSIDE_GPG_UID)"
    bw_require_unlocked
    bw sync >/dev/null || true
    local tmp; tmp="$(mktemp)"; trap 'rm -f "$tmp"' RETURN
    gpg --export-secret-keys --armor "$GPG_UID" > "$tmp"
    [ -s "$tmp" ] || die "gpg export produced nothing — no secret key for $GPG_UID?"
    bw_upsert_note "$BW_ITEM_GPG" "$tmp"
}

cmd_bw_pull_gpg() {
    need gpg "brew install gnupg"
    bw_require_unlocked
    bw sync >/dev/null || true
    local tmp; tmp="$(mktemp)"; trap 'rm -f "$tmp"' RETURN
    bw_fetch_note "$BW_ITEM_GPG" "$tmp"
    gpg --import "$tmp"
    log "gpg key imported — 'just secrets-reveal' now works"
}

cmd_bootstrap() {
    log "new-workstation bootstrap (runbook: docs/secrets-sync.md)"
    if cmd_bw_pull; then
        log "secrets pulled from Bitwarden"
    elif [ -f "$REPO_ROOT/${SECRETS_FILE}.secret" ]; then
        warn "Bitwarden lane failed — falling back to git-secret reveal"
        cmd_bw_pull_gpg || warn "no GPG key in the vault either; import one manually"
        cmd_reveal
    else
        die "no Bitwarden item and no ${SECRETS_FILE}.secret in the repo"
    fi
    cmd_doctor || true
}

cmd_doctor() {
    cd "$REPO_ROOT"
    local rc=0
    for t in bw gpg git-secret; do
        command -v "$t" >/dev/null 2>&1 && log "tool: $t OK" || { warn "tool missing: $t"; rc=1; }
    done
    if command -v bw >/dev/null 2>&1; then
        log "bw status: $(bw status 2>/dev/null | python3 -c 'import json,sys; print(json.load(sys.stdin)["status"])' 2>/dev/null || echo '?')"
    fi
    if [ -n "$GPG_UID" ] && gpg --list-secret-keys "$GPG_UID" >/dev/null 2>&1; then
        log "gpg: secret key for $GPG_UID present"
    else
        warn "gpg: no secret key for '${GPG_UID:-<unset>}' — git-secret lane inert (run gpg-init)"
    fi
    [ -d .gitsecret ] && log "git-secret: initialized" || warn "git-secret: not initialized"
    if [ -f "$SECRETS_FILE" ]; then
        log "$SECRETS_FILE: present ($(grep -cE '^[A-Za-z_]+=' "$SECRETS_FILE") vars)"
        # Template drift: every live var must be declared in the template and vice versa.
        if [ -f "$TEMPLATE_FILE" ]; then
            local drift
            drift="$(comm -3 \
                <(grep -oE '^[A-Za-z_]+' "$SECRETS_FILE" | sort -u) \
                <(grep -oE '^[A-Za-z_]+' "$TEMPLATE_FILE" | sort -u) | tr -d '\t' | paste -sd' ' -)"
            [ -z "$drift" ] && log "template: in sync" || { warn "template drift: $drift"; rc=1; }
        fi
        # File-typed secrets must point at existing files.
        for var in YC_SERVICE_ACCOUNT_KEY_FILE GOOGLE_APPLICATION_CREDENTIALS; do
            local p
            p="$(grep -E "^${var}=" "$SECRETS_FILE" | head -1 | cut -d= -f2- | sed -e 's/^"//' -e 's/"$//')"
            [ -z "$p" ] && continue
            p="${p/#\~/$HOME}"
            [ -f "$p" ] && log "$var → file present" \
                || { warn "$var → '$p' missing (bw-pull-file '$BW_ITEM_FILE_PREFIX/$(basename "$p")' '$p')"; rc=1; }
        done
    else
        warn "$SECRETS_FILE missing — run bootstrap"
        rc=1
    fi
    return "$rc"
}

usage() {
    sed -n '2,12p' "${BASH_SOURCE[0]}"
    printf '\ncommands: doctor | bootstrap | bw-push | bw-pull | bw-push-file | bw-pull-file\n'
    printf '          gpg-init | hide | reveal | bw-push-gpg | bw-pull-gpg\n'
}

case "${1:-}" in
    doctor)        cmd_doctor ;;
    bootstrap)     cmd_bootstrap ;;
    bw-push)       cmd_bw_push ;;
    bw-pull)       cmd_bw_pull ;;
    bw-push-file)  shift; cmd_bw_push_file "$@" ;;
    bw-pull-file)  shift; cmd_bw_pull_file "$@" ;;
    gpg-init)      cmd_gpg_init ;;
    hide)          cmd_hide ;;
    reveal)        cmd_reveal ;;
    bw-push-gpg)   cmd_bw_push_gpg ;;
    bw-pull-gpg)   cmd_bw_pull_gpg ;;
    ""|-h|--help)  usage ;;
    *)             usage; die "unknown command: $1" ;;
esac
