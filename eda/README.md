# EDA — exploring the data before any model touches it

Five notebooks that look at what is already on disk. **No API calls, no model
output, no simulated results.** Everything here is computed from the corpus, the
selection tables and the annotated slots, so it costs nothing to re-run and
nothing here depends on an experiment having been run.

| Notebook | Question it asks |
| --- | --- |
| [01_corpus_landscape](01_corpus_landscape.py) | What is in the corpus? Length, structure, how uneven the documents are. |
| [02_marker_behaviour](02_marker_behaviour.py) | How do the selection markers actually behave, including where they are wrong? |
| [03_candidate_quality](03_candidate_quality.py) | Is the shortlist finding normative structure, or just long provisions? |
| [04_annotated_slots](04_annotated_slots.py) | What do the hand-drafted slots look like across Swedish statute, philosophy and RFCs? |
| [05_analysis_designs](05_analysis_designs.py) | Which analyses can this data support, and which cannot be answered yet? |

Run them in any order. Each begins with the imports and paths it needs.

Two standing caveats apply to every number in this folder:

- **Selection markers are lexical.** A hit is a regex match, not a norm. They are
  recall-tuned and carry known false positives, several of which are shown in 02.
- **Slot annotations are assistant drafts.** No human has reviewed them, so any
  count derived from them inherits that.

Build the tables first if they are missing:

```powershell
python scripts/pipeline/build_silver.py
python scripts/pipeline/build_tables.py
```
