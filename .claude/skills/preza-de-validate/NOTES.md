# preza-de-validate — project-local HARDLINK port

`skill.md` here is a **hardlink** sharing the inode of the canonical file:
`/Users/nk.myg/.ai/skills/_catalog/docs/pptx/preza-de-validate/SKILL.md`

- Same bytes on disk; editing either path edits both (no copy drift).
- Survives moves of the canonical *directory* (the inode persists) — unlike the symlink.
- After editing via a tool that rewrites the file (new inode), re-run this script to re-link.
