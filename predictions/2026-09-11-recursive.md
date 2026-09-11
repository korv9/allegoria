# Exploratory recursive test, recorded before API generation

This is a pre-run design snapshot, NOT a committed or externally timestamped
preregistration. The user authorized actual generations 1-10 on 2026-09-11.

## Fixed sample and interventions

All three provisions in law_probe_v1, all thirty passages in philosophy_v1.
Law: four styles x two prompt variants x ten generations (240 texts).
Philosophy: paraphrase x two variants x ten generations (600 texts).
Total: 84 chains, 840 generated texts, 33 source readings + 840 generated readings.
Every generation receives only its immediate parent's text and its chain's fixed
instruction. No source reminder, retrieval, previous response ID or assistant history.
Models: gpt-5.4-nano-2026-03-17 transforms; gpt-5.4-mini-2026-03-17 reads.
Reasoning none, temperature provider default. Raw requests and responses are retained.
Output caps: transformations 1800 tokens; readings 2400 tokens. USD 15 reservation cap.

## Predictions and actual tests

1. For each law exception, its attached source condition may first be read absent
   before the exception is first read absent. Report earlier / same / later /
   not observed within ten generations / unresolved separately, by chain and slot.
   Predefined pairs: exception_deadline and deadline_start vs exception (disputes);
   unforeseen_event and compensation vs temporary_exception (rest);
   special_reasons vs exception (leave). Night exception has no separately
   annotated exception slot: do not force it into this test.
2. Categorical passages may acquire allowed exceptions, unlike their baseline.
   Report observed state sequences for matched conditional controls, not an
   invalid raw insertion comparison with controls already containing exceptions.
3. Descriptive virtue passages should not acquire explicit duties. This is a limited
   probe of deontic structure, not proof of semantic preservation of virtue ethics.
4. Compare philosophical groups with statutory paraphrases ONLY. The other statutory
   styles are separate interventions. Summarization intentionally compresses, so
   differences do not alone establish spontaneous distortion in faithful paraphrase.

Counts are descriptive; chains within a passage and adjacent generations are not
independent samples. No significance claim, universal model claim or ethical-theory
switch is inferred. Unexpected/null results and failures stay visible.

## Interpretation and limits

Reader outputs are present/absent/uncertain with verifiable quotations. They do not
measure specificity or normative direction. No loosening curve will be fabricated.
Lexical deletion does not imply semantic absence. Contradictions and ambiguous scope
require review. Human annotation is pending; assistant inspection is not human agreement.
No twins, second transformer or independent repeated chains are included in this
bounded exploratory run. Cannot establish memorization, reproducibility or generality.
First absence is an observed event, not necessarily permanent; later reappearance
must be reported. Missing/uncertain earlier readings prevent exact first-loss timing.

## Failure and repeat policy

Up to three recorded attempts for transient HTTP/network errors, no repeated quota
failures; up to two independently recorded identical reading attempts if schema or
verbatim evidence fails validation. No regeneration to obtain a preferred result.
Resume skips saved successes and preserves failed attempts and previous code receipts.
