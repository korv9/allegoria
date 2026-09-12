# Adding a dataset

The experiment is about what recursive rewriting does to normative text. Which
normative text is a parameter. Adding one is four files and no edits to the
engine. `simulacria/domains/rfc.py` and `corpus/rfc_probe_v1.yaml` are a worked
example of every step below.

## 1. An adapter, `simulacria/domains/<name>.py`

Write one function and register it:

```python
def resolve(passage_id: str, root: Path, spec: dict) -> PassageSource:
    """passage id -> text, plus the lineage proving where the text came from."""
```

It must fail loudly when the bytes it was pinned to have moved. `sfs.py`
re-hashes the original XML, compares the bronze envelope field by field and
checks that the parser sees the same HTML; `rfc.py` re-hashes the plain text
before cutting out a section. Silently measuring a different text is the one
outcome this layer exists to prevent.

`inline.py` is the fallback for text with no upstream document: the corpus file
carries the text and pins it with `text_sha256`.

## 2. Bronze, if the domain has source documents

An ingest script under `scripts/pipeline/`: fetch, write the exact bytes to
`data/source/<name>/`, write an envelope to `data/bronze/<name>/` with the URL,
the retrieval time, the SHA-256 and the decoded payload. Never overwrite an
existing document — a refetch that differs is a new document.

Skip this for an inline corpus.

## 3. A corpus, `corpus/<name>_probe_v1.yaml`

```yaml
schema_version: 2
domain: <name>
group: <how these passages group in analysis>
annotation_status: assistant_draft_requires_human_review
passages:
  - passage_id: <resolvable by your adapter>
    rationale: why this passage is worth including
    slots:
      - slot_id: deviation_allowed
        kind: exception          # modality | actor | condition | deadline | exception
        attaches_to: duty        # duty | exception
        question: Does the text allow a departure from the rule?
        quote: <a verbatim span of the passage, occurring exactly once>
```

`default_slots:` at the top level applies to every passage that declares none
(`corpus/philosophy_v1.yaml` uses it for three questions across 30 passages).

Two rules the loader enforces and you should not work around: the slot
vocabulary is shared across domains, because `attaches_to` decides the sign of a
direction change; and questions live in the corpus, in the corpus's language,
not in Python.

## 4. Prompts and a config

Mirror `prompts/sv/` for the new language: `transform.yaml` with the same styles
and variants, `read_slots.txt` for the reader. Then:

```yaml
# configs/<experiment>.yaml
experiment: <name>
language: en
generations: 10
corpora:
  - path: corpus/<name>_probe_v1.yaml
    styles: all           # or a list, e.g. [paraphrase]
prompts: prompts/en/transform.yaml
reader_prompt: prompts/en/read_slots.txt
prediction: predictions/<date>-<name>.md
```

## 5. Check it before spending anything

```powershell
python scripts/run/pilot.py  --check --config configs/<experiment>.yaml
python scripts/run/chains.py --check --config configs/<experiment>.yaml
```

`--check` resolves every passage through the adapter, validates every slot quote
and builds every request without making a call. Add the corpus to the
parametrised case in `tests/test_domains.py` so the lineage check runs in CI.

## What you may not change

The instrument. Slot vocabulary, blinding, the reading schema, the receipts, the
budget and the retry rules are identical for every dataset. Results from two
corpora are only comparable while that stays true, and a domain that could
change them would make the comparison meaningless without anyone noticing.

Also: a second domain is not a replication. Different language, register and
subject matter differ in more ways than one, so results are reported per
experiment and never pooled.
