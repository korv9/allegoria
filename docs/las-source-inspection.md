# LAS source inspection

Inspected on 2026-08-19 from Riksdagen's official open-data endpoint:

```text
https://data.riksdagen.se/dokument/sfs-1982-80
```

## Canonical source

`data/source/las/sfs-1982-80.xml` is the unmodified HTTP response. It is the canonical local copy of LAS and must not be formatted, normalized, or edited manually.

The exact response is pinned with SHA-256:

```text
a310dbc84411b7a7cfa7fc29bd0f52306e2b4358407ac84f74363a8aa5db2f9b
```

`data/source/las/provenance.json` records where and when this copy was retrieved.

## Observed structure

The response root is `dokumentstatus`, containing one `dokument` element. The fields currently needed are:

| Field | Observed value or role |
| --- | --- |
| `dok_id` | Stable source identifier: `sfs-1982-80` |
| `titel` | `Lag (1982:80) om anställningsskydd` |
| `subtitel` | Source version: `t.o.m. SFS 2022:836` |
| `datum` | Original issue date |
| `publicerad` | Publication timestamp for this source representation |
| `text` | Plain legal text, including source line breaks |
| `html` | HTML representation supplied by Riksdagen |
| `avdelningar` | Additional document structure supplied by Riksdagen |

The full response is 146,007 bytes. The extracted `text` field contains 57,372 characters when parsed by Python's standard XML parser.

## Current boundary

The project currently preserves and loads the source only. No Bronze, Silver, Gold, chunk, or retrieval schema has been introduced yet.

The next design step is to inspect paragraph boundaries, headings, amendment annotations, and references in the exact source text. Those observations will determine the first Bronze representation.
