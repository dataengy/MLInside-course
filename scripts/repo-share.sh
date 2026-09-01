#!/usr/bin/env bash
# scripts/repo-share.sh — keep every repo of the course family reachable from BOTH
# GitHub identities the course is worked from.
#
# Why this exists. The course spans one public umbrella repo (dataengy/MLInside-course)
# and six submodules owned by the other account (hnkovr/*), four of them private. Whichever
# identity a given workstation's credential helper hands to git decides whether a
# `git submodule update` succeeds — see note 2 in scripts/repo-update.sh. Rather than
# fight the keychain per machine, we make BOTH accounts admin on BOTH sides, once.
#
# Two facts this script encodes, both learned the hard way:
#
#   1. `PUT /repos/{o}/{r}/collaborators/{u}` is NOT idempotent w.r.t. permission when a
#      pending invitation already exists. It returns the EXISTING invite untouched, still
#      at the old permission. `PATCH .../invitations/{id}` does report the new permission —
#      but an invite that has been patched can then be accepted and silently NOT create the
#      collaborator (observed on hnkovr/preza_gen: accept returned 204, membership 404).
#      So: a pending invite at the wrong permission is REVOKED and re-created, never patched.
#
#   2. `gh auth switch` does not help here — it flips the active account globally and
#      races with anything else using gh. We read each account's token explicitly with
#      `gh auth token --user <acct>` and scope it to one command via GH_TOKEN.
#
# The repo list is derived from .gitmodules, so adding a submodule automatically brings it
# into scope. EXTRA_REPOS covers repos related by hand rather than by gitlink.
#
# Usage: bash scripts/repo-share.sh [doctor|sync|help]
#        just repo-share-doctor      (= doctor, read-only — prints the access matrix)
#        just repo-share             (= sync, invites + accepts anything missing)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Both identities the course is worked from. Each must be logged in: gh auth login.
ACCOUNTS=(hnkovr dataengy)
# Repos related to the course but not referenced as a submodule.
EXTRA_REPOS=(dataengy/MLInside-course hnkovr/MLInside-course)
PERMISSION="${MLINSIDE_SHARE_PERMISSION:-admin}"

log()  { printf '»» %s\n' "$*"; }
ok()   { printf 'OK   %s\n' "$*"; }
warn() { printf 'WARN: %s\n' "$*" >&2; }
die()  { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

# ── repo inventory ────────────────────────────────────────────────────────────

# owner/name for every submodule url in .gitmodules, plus EXTRA_REPOS, deduped.
repos() {
    {
        git -C "$REPO_ROOT" config -f .gitmodules --get-regexp '^submodule\..*\.url$' 2>/dev/null |
            awk '{print $2}' |
            sed -E 's#^(https://github\.com/|git@github\.com:)##; s#\.git$##'
        printf '%s\n' "${EXTRA_REPOS[@]}"
    } | grep -E '^[^/]+/[^/]+$' | sort -u
}

# ── gh plumbing ───────────────────────────────────────────────────────────────

token_for() {
    local acct=$1 tok
    tok=$(gh auth token --user "$acct" 2>/dev/null) || true
    [[ -n $tok ]] || die "no gh token for '$acct' — run: gh auth login --user $acct"
    printf '%s' "$tok"
}

# gh_as <account> <gh args...>
gh_as() { local acct=$1; shift; GH_TOKEN="$(token_for "$acct")" gh "$@"; }

# What does <account> actually hold on <repo>? admin | write | read | none
access_of() {
    local acct=$1 repo=$2 perms
    perms=$(gh_as "$acct" api "repos/$repo" --jq \
        '[.permissions | to_entries[] | select(.value) | .key] | join(",")' 2>/dev/null) || {
        printf 'none'; return
    }
    case ",$perms," in
        *,admin,*) printf 'admin' ;;
        *,push,*)  printf 'write' ;;
        *,pull,*)  printf 'read'  ;;
        *)         printf 'none'  ;;
    esac
}

# Pending invite for <user> on <repo>, as "<id> <permission>"; empty if none.
pending_invite() {
    local owner=${2%%/*} repo=$2 user=$1
    gh_as "$owner" api "repos/$repo/invitations" --jq \
        ".[] | select(.invitee.login==\"$user\") | \"\(.id) \(.permissions)\"" 2>/dev/null || true
}

# ── grant ─────────────────────────────────────────────────────────────────────

# grant <repo> <user> — bring <user> to $PERMISSION on <repo>, inviting and accepting.
grant() {
    local repo=$1 user=$2 owner=${1%%/*} invite id perm
    invite=$(pending_invite "$user" "$repo")
    if [[ -n $invite ]]; then
        read -r id perm <<<"$invite"
        if [[ $perm == "$PERMISSION" ]]; then
            log "$repo: invite for $user already pending at $perm"
        else
            # Fact 1: do not PATCH — revoke and re-create, or the accept silently no-ops.
            log "$repo: revoking stale $perm invite for $user"
            gh_as "$owner" api -X DELETE "repos/$repo/invitations/$id" --silent
            invite=""
        fi
    fi
    if [[ -z $invite ]]; then
        log "$repo: inviting $user as $PERMISSION"
        gh_as "$owner" api -X PUT "repos/$repo/collaborators/$user" \
            -f permission="$PERMISSION" --silent
    fi

    # Accept from the invitee side. Nothing to accept => already a collaborator.
    id=$(gh_as "$user" api user/repository_invitations --jq \
        ".[] | select(.repository.full_name==\"$repo\") | .id" 2>/dev/null | head -1)
    if [[ -n $id ]]; then
        gh_as "$user" api -X PATCH "user/repository_invitations/$id" --silent
        log "$repo: $user accepted"
    fi
}

# ── commands ──────────────────────────────────────────────────────────────────

cmd_doctor() {
    local repo acct got bad=0
    printf '%-38s %-9s %s\n' REPO VISIBILITY "$(printf '%-9s' "${ACCOUNTS[@]}")"
    while read -r repo; do
        local owner=${repo%%/*} vis line
        vis=$(gh_as "$owner" api "repos/$repo" --jq \
            'if .private then "private" else "public" end' 2>/dev/null) || vis='??'
        line=$(printf '%-38s %-9s' "$repo" "$vis")
        for acct in "${ACCOUNTS[@]}"; do
            got=$(access_of "$acct" "$repo")
            [[ $got == "$PERMISSION" ]] || bad=1
            line+=$(printf ' %-9s' "$got")
        done
        printf '%s\n' "$line"
    done < <(repos)
    echo
    if (( bad )); then
        warn "not every account holds '$PERMISSION' everywhere — run: just repo-share"
        return 1
    fi
    ok "all accounts hold '$PERMISSION' on all ${#ACCOUNTS[@]}-way shared repos"
}

cmd_sync() {
    local repo acct
    while read -r repo; do
        for acct in "${ACCOUNTS[@]}"; do
            [[ ${repo%%/*} == "$acct" ]] && continue          # owner needs no invite
            [[ $(access_of "$acct" "$repo") == "$PERMISSION" ]] && continue
            grant "$repo" "$acct"
        done
    done < <(repos)
    echo
    cmd_doctor
}

usage() {
    sed -n '2,28p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

case "${1:-doctor}" in
    doctor)     cmd_doctor ;;
    sync|all)   cmd_sync ;;
    help|-h|--help) usage ;;
    *) die "unknown command '$1' — try: doctor | sync | help" ;;
esac
