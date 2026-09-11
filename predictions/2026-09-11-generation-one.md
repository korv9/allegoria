# Generation-one exploratory pilot

Written before the API pilot. This is not a git-timestamped preregistration.
The user requested actual generation-one examples and authorized OpenAI with an
inexpensive adequate model on 2026-09-11. This supersedes the earlier task's
no-model-call scope, not its prohibition on simulated output.

Use the three sources in `corpus/law_probe_v1.yaml` with their full legal text.
Run four styles (paraphrase, summarize, explain, allegorize), two prompt variants
each, once per source. Every child takes generation zero as its only parent.
Keep all twenty-four attempts; no selecting only successful or dramatic results.

Transformer: `gpt-5.4-nano-2026-03-17`, reasoning none, provider-default temperature,
900 maximum output tokens. Reader: `gpt-5.4-mini-2026-03-17`, reasoning none,
provider-default temperature, 1600 maximum output tokens. Both use Responses API,
no tools and `store=false`. Record actual returned model, parameters, usage,
request and raw response. No automated retries. Local cost reservation limit: USD 0.50.

The separate reader receives only current text and slot questions, in shuffled
order mixing generation zero and one. Source quotes, style, generation number
and previous text are withheld. Its exact quotes are checked against its input.
Missing, duplicate, unknown slot IDs or fabricated quotations fail explicitly.

Working expectations: allegory changes literal phrasing more than paraphrase;
rest-period compensation and exception deadlines may be rephrased or omitted.
Neither ordering is assumed by the report. All unchanged, reversed or ambiguous
outcomes remain visible. Literal nonmatches never mean semantic absence.

This is a development pilot with draft source annotations, one transformer,
no human agreement yet, no statutory twins and no implemented direction metric.
It cannot confirm the research hypotheses in PROTOCOL.md. Its purpose is to make
real source/child texts and independently quoted slot readings inspectable.
Formal experiments still require the protocol's committed preregistration,
multiple transformer models and blinded human review. Numeric direction results
remain unavailable until the ambiguous specification and annotation are resolved.
