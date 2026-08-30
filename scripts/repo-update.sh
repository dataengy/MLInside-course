#!/usr/bin/env bash
# scripts/repo-update.sh — bring a checkout of this repo to a fully working state.
#
# Everything here is idempotent: safe to run on a fresh clone, on a stale one, or
# twice in a row. Ordering matters and encodes two hard-won facts:
#
#   1. git-lfs must exist BEFORE any checkout. .gitattributes routes *.pptx, *.pdf,
#      *.mp4, *.zip, *.docx, *.xlsx and data/images/** through the LFS filter with
#      filter.lfs.required=true. Without the binary every checkout dies with
#        git-lfs: command not found  ->  fatal: the remote end hung up unexpectedly
#      git then rolls back the index write, leaving an EMPTY index. The symptom is
#      misleading: `git status` shows all ~360 tracked files as "deleted", the files
#      still on disk show up as untracked, and `git switch` refuses to move because
#      it "would overwrite untracked files". Nothing is actually lost — the index is.
#
#   2. Four of the six submodules are PRIVATE repos under github.com/hnkovr.
#      macOS osxkeychain hands git whichever github.com credential it cached (often
#      the dataengy identity), and `gh auth switch` does NOT change that — the keychain
#      helper wins. So the submodule step injects gh's credential helper for that one
#      command instead of mutating global config or the active gh account.
#
# Usage: bash scripts/repo-update.sh [all|doctor|lfs|fetch|submodules|deps]
#        just update                 (= all)
#        just repo-doctor            (= doctor, read-only)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# Account that owns the private hnkovr/* submodules. Override if the fork moves.
SUBMODULE_ACCOUNT="${MLINSIDE_GH_ACCOUNT:-hnkovr}"

log()  { printf '»» %s\n' "$*"; }
ok()   { printf 'OK   %s\n' "$*"; }
warn() { printf 'WARN: %s\n' "$*" >&2; }
die()  { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
has()  { command -v "$1" >/dev/null 2>&1; }

# ── git-lfs ───────────────────────────────────────────────────────────────────

# The binary/config mismatch described in note 1 above.
lfs_broken() { git config --get-regexp '^filter\.lfs\.' >/dev/null 2>&1 && ! has git-lfs; }

cmd_lfs() {
    if ! has git-lfs; then
        log "git-lfs missing — installing"
        has brew || die "git-lfs missing and no brew — install git-lfs manually, then rerun"
        brew install git-lfs >/dev/null || die "brew install git-lfs failed"
    fi
    git lfs install --skip-repo >/dev/null || die "git lfs install failed"
    ok "git-lfs $(git lfs version | awk '{print $1}') — filters registered"
}

# ── index / working tree ──────────────────────────────────────────────────────

# An empty index against a non-empty HEAD is the fingerprint of a checkout that
# died mid-write (note 1). Repairing it needs a hard reset, which we only do when
# nothing would be lost: untracked files survive a reset, and a partial checkout
# has no staged work worth keeping.
index_is_empty() {
    [ "$(git -C "$REPO_ROOT" ls-files | wc -l | tr -d ' ')" -eq 0 ] &&
    [ "$(git -C "$REPO_ROOT" ls-tree -r HEAD --name-only | wc -l | tr -d ' ')" -gt 0 ]
}

cmd_checkout() {
    cd "$REPO_ROOT"
    if index_is_empty; then
        lfs_broken && die "index is empty AND git-lfs is missing — run the 'lfs' step first"
        warn "index is empty (interrupted checkout) — restoring working tree from HEAD"
        git reset --hard HEAD
        ok "index rebuilt: $(git ls-files | wc -l | tr -d ' ') files"
    else
        ok "index intact: $(git ls-files | wc -l | tr -d ' ') files"
    fi
    git lfs pull 2>/dev/null || warn "git lfs pull failed — large files may be pointer stubs"
}

# ── remote ────────────────────────────────────────────────────────────────────

cmd_fetch() {
    cd "$REPO_ROOT"
    git fetch --all --prune --tags
    local branch ahead behind
    branch="$(git rev-parse --abbrev-ref HEAD)"
    if git rev-parse --verify --quiet "origin/$branch" >/dev/null; then
        read -r behind ahead <<<"$(git rev-list --left-right --count "origin/$branch...HEAD")"
        ok "$branch: $ahead ahead, $behind behind origin/$branch"
        [ "$behind" -gt 0 ] && [ "$ahead" -eq 0 ] && { git merge --ff-only "origin/$branch" && ok "fast-forwarded"; } || true
    else
        warn "$branch has no upstream on origin"
    fi
}

# ── submodules ────────────────────────────────────────────────────────────────

# Run git with gh's credential helper for the configured account, scoped to this
# one invocation. `credential.helper=` first CLEARS the inherited helper list
# (osxkeychain from the system gitconfig) — without that reset the keychain answers
# first and wins. GIT_CONFIG_PARAMETERS propagates to the child clone processes.
git_as_submodule_account() {
    local prev rc=0
    if has gh; then
        prev="$(gh auth status --active 2>/dev/null | sed -n 's/.*Logged in to github.com account \([^ ]*\).*/\1/p' | head -1)"
        [ -n "$prev" ] && [ "$prev" != "$SUBMODULE_ACCOUNT" ] &&
            gh auth switch -u "$SUBMODULE_ACCOUNT" >/dev/null 2>&1 || true
        git -c credential.helper= -c credential.helper='!gh auth git-credential' "$@" || rc=$?
        [ -n "$prev" ] && [ "$prev" != "$SUBMODULE_ACCOUNT" ] &&
            gh auth switch -u "$prev" >/dev/null 2>&1 || true
    else
        warn "gh not installed — private submodules may fail to clone"
        git "$@" || rc=$?
    fi
    return $rc
}

cmd_submodules() {
    cd "$REPO_ROOT"
    git_as_submodule_account submodule update --init --recursive ||
        warn "some submodules failed — check access to github.com/$SUBMODULE_ACCOUNT/*"

    # A submodule cloned before git-lfs existed carries the same empty-index damage.
    git submodule foreach --quiet '
        if [ "$(git ls-files | wc -l | tr -d " ")" -eq 0 ] &&
           [ "$(git ls-tree -r HEAD --name-only | wc -l | tr -d " ")" -gt 0 ]; then
            echo "»» repairing empty index in $sm_path"
            git reset --hard HEAD >/dev/null
        fi'
    ok "submodules: $(git submodule status | grep -c '^ ') of $(git submodule status | wc -l | tr -d ' ') clean"
}

# ── python deps ───────────────────────────────────────────────────────────────

cmd_deps() {
    cd "$REPO_ROOT"
    has uv || { warn "uv not installed — skipping dependency sync"; return 0; }
    uv sync --extra dev --extra gsheets && ok "uv sync done"
}

# ── doctor (read-only) ────────────────────────────────────────────────────────

cmd_doctor() {
    cd "$REPO_ROOT"
    local issues=0

    if lfs_broken; then
        printf 'X    filter.lfs.* configured but git-lfs missing — checkouts WILL fail; fix: just update\n'
        issues=$((issues + 1))
    elif has git-lfs; then
        ok "git-lfs present ($(git lfs ls-files | wc -l | tr -d ' ') tracked files)"
    else
        warn "git-lfs not installed (repo does use LFS)"; issues=$((issues + 1))
    fi

    if index_is_empty; then
        printf 'X    index is empty — working tree looks "all deleted"; fix: just update\n'
        issues=$((issues + 1))
    else
        ok "index: $(git ls-files | wc -l | tr -d ' ') files"
    fi

    local missing
    missing="$(git submodule status | grep -c '^-' || true)"
    [ "$missing" -gt 0 ] &&
        { printf 'X    %s submodule(s) not initialised — fix: just update\n' "$missing"; issues=$((issues + 1)); } ||
        ok "submodules initialised"

    git diff --quiet && git diff --cached --quiet && ok "working tree clean" || warn "uncommitted changes present"

    [ "$issues" -eq 0 ] && log "repo healthy" || die "$issues issue(s) — run: just update"
}

cmd_all() { cmd_lfs; cmd_checkout; cmd_fetch; cmd_submodules; cmd_deps; log "repo-update complete"; }

usage() {
    sed -n '2,22p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

case "${1:-all}" in
    all)         cmd_all ;;
    doctor)      cmd_doctor ;;
    lfs)         cmd_lfs ;;
    checkout)    cmd_checkout ;;
    fetch)       cmd_fetch ;;
    submodules)  cmd_submodules ;;
    deps)        cmd_deps ;;
    -h|--help)   usage ;;
    *)           usage; die "unknown command: $1" ;;
esac
