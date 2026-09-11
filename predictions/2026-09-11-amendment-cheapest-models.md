# Amendment: cheapest model pair

Amends `2026-09-11-amendment-anthropic-models.md`, which amends the two originals.
None of them is edited. Like them, this is a pre-run design note, NOT a committed or
externally timestamped preregistration.

**This amendment changes the reader model and its request parameters only. No
prediction, no sample, no prompt text and no analysis is changed.**

## What changed

| | Previous amendment | From this amendment |
| --- | --- | --- |
| Transformer | `claude-sonnet-5`, effort `low`, adaptive thinking | unchanged |
| Reader | `claude-opus-5`, effort `medium`, adaptive thinking | `claude-haiku-4-5-20251001` |
| Reader effort | `medium` | not sent — the model does not support the parameter |
| Reader thinking | adaptive (default) | off (model default) |
| Reader temperature | not settable | API default 1.0, not set in the request |
| Reader price (USD per million tokens, in / out) | 5 / 25 | 1 / 5 |

The reader is pinned by its dated ID: the alias `claude-haiku-4-5` is answered with
the dated ID, which would fail the check that the returned model matches the request.

## Why

The user asked on 2026-09-11 for the cheapest models. PROTOCOL.md requires two
different models, so the cheapest pair is Haiku 4.5 and Sonnet 5. Reading is about
half the calls and most of the tokens, so the cheaper model reads: an estimated
USD 4–5 for the full recursive design, against USD 16–17 with Opus 5 reading and
about USD 8 with the roles swapped. Estimates come from measured token counts, not quotes.

## What the reader check showed before this was adopted

Nine live readings through the pipeline's own request path
(`data/local/probes/haiku-reader-check-53105a2979d7/`, USD 0.03), on the three
sources and the six allegories from the earlier selection probe:

- 3 of 9 readings failed validation because a quote was not a verbatim substring
  of the text, one of them on a source text where every slot is known to be present.
  Opus 5 and Sonnet 5 had produced valid readings of all three sources.
- Every valid reading marked every slot `present`. On the one allegory where Opus 5
  had marked the duty `uncertain` — the duty rewritten as a mere possibility —
  Haiku marked it `present`, as Sonnet 5 had.

Nine readings are too few to estimate a rate. They are enough to say that the new
reader has not shown that it can detect the kind of change this study measures.

## Consequences

- Invalid readings are retried once and then flagged, per PROTOCOL.md. A high
  invalid rate means more flagged, unread texts.
- A reader that reports `present` where meaning has shifted biases slot readings
  toward "no degradation". Results from this configuration must be read with that
  limitation stated, and they are not comparable with readings by another model.
- Transformer and reader are now from different model generations, which makes
  them somewhat more independent than two Claude 5 models.
- The USD 15 reservation cap in the recursive original is unchanged.
