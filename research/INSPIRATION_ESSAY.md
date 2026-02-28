# Inspiration Essay

Author: `howaeri`
Source basis: `docs/WHY_CORTEX.md`

I built Cortex because I kept seeing the same pattern: models could produce plausible work fast, but they were rewarded more for sounding finished than for being correct.

That creates a bad loop in real projects. You get confident output, then discover missing checks, skipped edge cases, or architecture drift after the fact. The human ends up doing invisible cleanup.

I did not want another framework layer that “guides behavior” in prose. I wanted mechanical pressure:

- tests the model does not control
- required challenge categories it cannot skip
- memory of failed approaches across sessions
- warnings when the foundation is unstable before edits start

The thesis is simple: small, hard constraints beat large instruction sets.

Testing changed how I think about this project. Early runs showed that Cortex core gates were useful, but repo-map ranking quality was inconsistent. That was a good failure. It gave a concrete improvement path: tighter ranking heuristics, better evidence discipline, and no parity claims until the data supports them.

What I will not claim:

- I will not call repo-map parity done before the gates in `docs/REPOMAP_PARITY_CRITERIA.md` are satisfied.
- I will not hide limitations behind confident language.
- I will not trade reliability for complexity theater.

What I care about is boring in the best way: fewer escaped defects, less supervision overhead, and faster delivery of changes people can trust.

If you want to help, the highest leverage contributions are small and test-first:

- reproduce a concrete failure
- add a failing test
- ship the smallest fix
- attach evidence in `docs/evidence/`

That is the standard I use for my own changes too.
