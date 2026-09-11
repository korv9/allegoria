# The normative-structure axis

Constructed Swedish passages vary the location and conditionality of a norm.
They are written in Kantian and Aristotelian **form**, not quoted or translated
from either author. This is a selection audit, not a result about model drift.

| Type | Where the norm lives | Intended structure | Future prediction |
| --- | --- | --- | --- |
| Virtue | Character description | No explicit deontic slots | Neutral while descriptive |
| Statutory | Rule with carve-outs | Duty, exception, qualifier | Qualifier loss may loosen |
| Categorical | Unconditional duty | Duty without an escape clause | Added escape clause loosens |
| Conditional control | Duty with an existing carve-out | Topic-matched duty and exception | Less new exception insertion |

The virtue group is a negative control for an explicit deontic instrument.
Silence is expected on these descriptions, not on all virtue ethics: Aristotle
also discusses right action. The categorical group tests insertion rather than
only deletion. Its paired conditional controls distinguish a differential effect
from generic hedging. A new exception does not by itself prove that a model has
adopted consequentialism or changed its entire ethical theory.

Form sources, consulted 2026-09-11:
[Aristotle, Nicomachean Ethics II, especially 6–7](https://classics.mit.edu/Aristotle/nicomachaen.2.ii.html)
(character and the mean), and
[Kant, Groundwork, sections I–II](https://www.gutenberg.org/cache/epub/5682/pg5682-images.html)
(truthful promising and persons as ends). Modern duties in the corpus are
operational constructions, not a catalogue of Kant's derived duties. In particular
consent, confidentiality and conversational respect need independent philosophical
review. Actor/object scope is not an escape clause; this distinction needs human
annotation before measurement. A conditionally defeasible duty is also not the
same thing as Kant's technical term “hypothetical imperative”.

Construction reduces verbatim recall and matches register and length; it cannot
eliminate training familiarity or isolate every syntactic and semantic confound.
The descriptive texts necessarily differ from prescriptions. A lexical null on
texts designed without modal words is a limited check, not instrument validation.

## Data and reproducibility

`corpus/philosophy_v1.yaml` contains ten descriptive sketches and ten paired
categorical/conditional duties. Pair members share their entire opening; only
the final sentence varies. `corpus/statutory_axis_v1.yaml` preserves the twenty
full-text blocks from the existing specimen sheet with its byte hash, source
URLs, IDs and original review caveats. It is a derivative snapshot, not a new
legal-source ingestion. The sheet is unchanged.

No statutory experiment YAML or loader existed in this checkout. Both files use
one small envelope (`schema_version`, `passages`) and the same loader in
`simulacria.selection.axis`. Passage identity, text hash and source are mandatory;
paired duties additionally carry `pair_id`. This is not the future slot contract.
The notebook checks the snapshot against the sheet and manifest provenance.

The target band is the full specimen range, 200–407 Unicode characters including
spaces and line breaks. Achieved distributions and pair differences are computed
in the notebook and in `review/2026-09-11/NORMATIVE_AXIS_RESULTS.md`. Statutory
matching uses greedy nearest length to categorical texts, without replacement,
in ascending length/ID order, breaking ties by specimen ID. No hit filter is used.
The full baseline is also reported: it was already marker-selected and therefore
cannot independently validate recall. Flagged specimens stay visible.

## What the current audit actually found

The expected lexical separation fails: `undantag` fires inside `utan undantag`;
bare `om` fires in descriptive and nonconditional complements. These passages
are retained, not rewritten to make the detector pass. Existing marker code,
library extraction, ceiling work and specimen annotations are unchanged.

See [the executed notebook](notebooks/02_normative_axis.ipynb) and
[future predictions](predictions/2026-09-11-normative-axis.md). No generation
curve, twin gap or human agreement score exists yet. The proposed public demo
can show those only after actual runs, complete manifests and blinded annotation.
Loosening describes permitted action, not moral quality or who benefits.
