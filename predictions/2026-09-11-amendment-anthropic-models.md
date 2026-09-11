# Amendment: model provider changed to Anthropic

Amends `2026-09-11-generation-one.md` and `2026-09-11-recursive.md`. Those files
are not edited; PROTOCOL.md allows amendments only as new files with reasons.
Like the originals, this is a pre-run design note, NOT a committed or externally
timestamped preregistration.

**This amendment changes models and request parameters only. No prediction, no
sample, no prompt text and no analysis is changed.**

## What changed

| | Originals | From this amendment |
| --- | --- | --- |
| Provider | OpenAI Responses API | Anthropic Messages API |
| Transformer | `gpt-5.4-nano-2026-03-17` | `claude-sonnet-5` |
| Reader | `gpt-5.4-mini-2026-03-17` | `claude-opus-5` |
| Reasoning | none | adaptive thinking (model default); effort `low` to transform, `medium` to read |
| Temperature | provider default | not settable on these models — the API rejects it |
| Output caps | 900 / 1600 (gen 1); 1800 / 2400 (recursive) | 8000 for every call |
| Refusal fallbacks | not applicable | disabled: a fallback would silently substitute a different model |

The higher output cap exists because thinking tokens count against it. A chain
ended by a token ceiling would be an artifact of the cap, not a transformation
outcome. The caps in the originals were set for models without thinking.

## Why

The user switched the project to Anthropic on 2026-09-11. OpenAI's limit of 50
requests per day per model would have stretched the planned recursive run over
roughly a month of daily resumes.

The model assignment follows a selection probe, not an assumption
(`scripts/investigations/model_probe.py`; raw responses under
`data/local/probes/`). Both candidates read every slot of all three sources
correctly. On allegorical texts they disagreed on 2 of 30 slots, and on reading
the texts `claude-opus-5` was right both times — including catching a duty
rewritten as a mere possibility. The stronger model therefore reads.
`claude-sonnet-5` followed the transformer instructions more cleanly and at about
a third of the cost. Both are Claude 5 models: different models as PROTOCOL.md
requires, but less independent than a reader from another provider would be.

## Consequences

- IDs such as `claude-sonnet-5` have no dated snapshot; the API returns the same
  string, and the Models API gives `created_at` 2026-06-29 (Sonnet 5) and
  2026-07-24 (Opus 5). Manifests record the returned model string.
- The partial OpenAI recursive run `recursive-81c11f28ed4541158fd07abd83f85dab`
  is not continued. Its design is frozen and pinned to OpenAI models, so any
  Anthropic generation is a new run. Its files are preserved unchanged.
- The USD 15 reservation cap in the recursive original is unchanged.
