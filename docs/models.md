# Choosing models

Two models do the work, and they must be different ones: a **transformer** that
rewrites text, and an **extractor** that reads the result and answers the slot
questions. A model reading its own output is not an instrument, it is the same
guess twice — `PROTOCOL.md`, "Separate models".

Which two is configuration, not code.

## Where the choice lives

| File | Holds |
| --- | --- |
| `configs/models.yaml` | every usable model: provider, wire id, prices, parameters, and whether anyone has actually called it |
| `configs/<experiment>.yaml` | which two of them that experiment uses |
| `simulacria/providers/` | one module per API — `anthropic.py`, `openai.py` |

No model id appears anywhere else in the codebase. A run records the full
resolved spec in its manifest, so a result can be read years later without
guessing what "the cheap reader" meant at the time.

```powershell
python scripts/run/chains.py --list-models
python scripts/run/chains.py --check --extractor opus-5      # price a better reader
python scripts/run/pilot.py  --transformer sonnet-4-6 --check
```

An override on the command line is for pricing and one-off tests. A run you
intend to keep should name its models in its config, because that file is what
gets frozen into `design.json`.

## The current choice, and the evidence for it

**Transformer: `sonnet-5`.** It followed the transformer instructions more
cleanly than Opus in the selection probe, at about a third of the cost. Rewriting
is routine work, so effort is `low`. Temperature is not settable on this model.

**Extractor: `haiku-4-5`** is the current default, adopted when the user asked
for the cheapest pair (DD047). The comparison below says it should probably be
replaced by `gpt-5-4-mini`, which is both better and cheaper.

## The cross-provider comparison, 2026-09-12

66 calls, $0.30, through the pipeline's own request path:
`scripts/investigations/compare_models.py`, saved in
`data/local/probes/model-comparison-6b280886b6be/`. Three writers on 3 statutory
passages x 2 styles; four readers on those 3 sources plus 9 allegories, blinded
to who wrote each text.

### As reader

"Valid" means the answer parsed, covered every slot, and quoted the text
verbatim. The sources are the easy case: every slot was annotated from that exact
text, so a failure there is a failure on a question with a known answer.

| Reader | Sources valid | Allegories valid | Agreement with `opus-5` | USD per reading |
| --- | --- | --- | --- | --- |
| `opus-5` | 3/3 | 9/9 | — | $0.0184 |
| `gpt-5-4-mini` | 3/3 | 8/9 | 96% | $0.0009 |
| `haiku-4-5` | 2/3 | 6/9 | 97% | $0.0033 |
| `gpt-5-4-nano` | 2/3 | 6/9 | 92% | $0.0002 |

**`gpt-5-4-mini` dominates `haiku-4-5`:** more valid readings on both the easy and
the hard case, and 3.5x cheaper. Against `opus-5` it is 20x cheaper for one
invalid reading out of twelve.

### As writer

| Writer | Paraphrase length | Allegory length | Output tokens | Seconds | USD per call |
| --- | --- | --- | --- | --- | --- |
| `sonnet-5` | 0.96x | 2.61x | 166 / 412 | 3.4 / 11.0 | $0.0021 / $0.0045 |
| `gpt-5-4-mini` | 0.99x | 2.12x | 125 / 286 | 1.4 / 3.0 | $0.0003 / $0.0006 |
| `gpt-5-4-nano` | 1.00x | 1.77x | 113 / 208 | 1.5 / 2.3 | $0.00005 / $0.0001 |

All three followed the instruction on all 18 transformations. They differ in how
much they expand an allegory, which is a property of the object of study, not a
defect: a transformer is what the experiment is *about*.

### What a full Swedish run would cost

840 transformations and 873 readings, priced from the token means measured above:

| Transformer | Extractor | USD |
| --- | --- | --- |
| `sonnet-5` | `opus-5` | 18.86 |
| `sonnet-5` | `haiku-4-5` | 5.66 |
| `sonnet-5` | `gpt-5-4-mini` | **3.60** |
| `gpt-5-4-mini` | `haiku-4-5` | 3.25 |
| `gpt-5-4-nano` | `gpt-5-4-mini` | **0.88** |
| `gpt-5-4-mini` | `gpt-5-4-nano` | 0.55 |

### What this does not settle

- Twelve readings per reader. That is enough to rank validity, not to estimate a
  rate, and the allegories are freshly generated text, not the ones the September
  11 probe scored.
- Every reader answered `present` to 95-98% of slots. On texts that still contain
  the duty that is the right answer; it also means none of them has yet been shown
  to detect a shift, because these texts mostly did not contain one. One case is
  suggestive: on the allegory `gpt-5-4-mini` wrote, three readers independently
  marked the duty `uncertain` or `absent` and `gpt-5-4-nano` marked it `present`.
- OpenAI prices in the registry are unconfirmed against the current price list.
- Readers and writers here share a provider in some pairs. The instrument is more
  independent when they do not.

## The open decision

Two changes are worth making, and both are a word in a config:

1. **Reader: `haiku-4-5` -> `gpt-5-4-mini`.** Better on every measured axis and
   cheaper. This changes what the DD047 amendment says, so it needs its own
   amendment before a run is created.
2. **A second transformer.** At $3.60 per full run, running `sonnet-5` and
   `gpt-5-4-mini` as two transformers costs less than one Opus-read run and
   closes the "one transformer" limitation PROTOCOL.md names. They must be two
   runs, not one: a transformer is the object of study, and mixing two into one
   result would make the outcome unattributable.

Pacing: the OpenAI account allows 5,000 requests per minute, so
`scripts/run/chains.py --check` suggests an interval from the declared limits
when every model in the run has one. For an all-OpenAI run that is minutes
instead of the three hours the 6.2-second default implies. Anthropic entries
record no limit, so nothing is guessed for them.

## `verified:` is a claim about reality

An entry is verified when someone made a real call through this code and checked
four things: the request was accepted, the response decoded, the returned model
id matched the pinned request, and usage appeared where the cost accounting looks
for it.

```powershell
python scripts/investigations/check_provider.py haiku-4-5 --schema
```

One cheap call, saved under `data/local/probes/`, with the date to write into
`configs/models.yaml` printed at the end. Unverified models are refused by
`scripts/run/*.py` unless you pass `--allow-unverified-model`, because an
unverified entry is a hypothesis about an API, and the way you find out it was
wrong is a failed paid run.

The OpenAI provider was verified live on 2026-09-12: both models answered,
decoded, returned their pinned id and reported usage where the cost accounting
looks for it, including structured output. Its prices are still the ones recorded
on 2026-09-11 and should be re-checked against the current price list — a stale
price makes the budget guard wrong in the direction that costs money.

## Adding a model

Add an entry to `configs/models.yaml`, run `check_provider.py`, write the date in
`verified:`. That is the whole procedure when the provider already exists.

```yaml
opus-4-8:
  provider: anthropic
  model: claude-opus-4-8
  input_usd_per_million: 5.00
  output_usd_per_million: 25.00
  max_tokens: 8000
  params: {effort: medium}
  structured_output: true
  verified: null
  notes: why this model is here and what it is for
```

Two fields are worth care. `params` is sent verbatim, so it must contain only
what that model accepts — `haiku-4-5` declares none because it answers `effort`
with HTTP 400. `structured_output: false` makes a model unusable as a reader, and
`resolve()` refuses it rather than discovering the problem mid-run.

## Adding a provider

A module under `simulacria/providers/` implementing the contract in `base.py`:
build a payload, send it, decode a response, report usage, classify an error, and
say which keys it accepts. Register it in `base.get`.

Two rules it must keep:

- **Return the raw bytes untouched.** They are the receipt. Everything parsed
  from them must be reproducible from the bytes on disk.
- **Never substitute silently.** No client-side retry that hides a paid attempt,
  no fallback model. A refusal is data; a pinned model that quietly becomes
  another model destroys the only thing a manifest is for.

Keys are per provider (`OPENAI_API_KEY`, or the shared `LLM_API_KEY`), and each
provider decides which keys it accepts. That check is not cosmetic: an Anthropic
key also starts with `sk-`, and a bare prefix test would have handed it to
OpenAI.

## What is deliberately not configurable

The instrument. Slot vocabulary, blinding, the reading schema, the receipts, the
budget rules and the retry scopes are the same whatever model runs. Results from
two models are comparable only while that holds — and a model choice that could
also change the measurement would make every comparison meaningless without
anyone noticing.
