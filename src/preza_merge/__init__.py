"""preza_merge — merge a reviewer's .pptx fork back into the deck GENERATOR.

The lane normalizes decks into a comparable model, diffs the three sides (base / ours /
theirs), derives formatting RULES with evidence, writes them into a named profile that
preza_gen executes, and verifies the result by rebuilding the base content with the new
profile against the fork. Spec: docs/preza-merge-lane.md.
"""
