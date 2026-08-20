# LAS source inspection

LAS was first inspected on 2026-08-19 from Riksdagen's official open-data endpoint:

```text
https://data.riksdagen.se/dokument/sfs-1982-80
```

## Canonical source

LAS now lives in the shared SFS corpus:

```text
data/source/sfs/sfs-1982-80.xml
data/bronze/sfs/sfs-1982-80.json
```

The XML file is the unmodified HTTP response and is pinned with SHA-256:

```text
a310dbc84411b7a7cfa7fc29bd0f52306e2b4358407ac84f74363a8aa5db2f9b
```

`data/source/sfs/manifest.json` records the source URL, retrieval batch, file name, and hash. The
Bronze JSON retains the same payload losslessly in `raw_xml` together with decoded metadata,
plain text, and source HTML.

## Observed structure

The response root is `dokumentstatus`, containing one `dokument` element. Fields used by the
pipeline include:

| Field | Observed value or role |
| --- | --- |
| `dok_id` | Stable source identifier: `sfs-1982-80` |
| `titel` | `Lag (1982:80) om anställningsskydd` |
| `subtitel` | Source version: `t.o.m. SFS 2022:836` |
| `datum` | Original issue date |
| `publicerad` | Publication timestamp for this representation |
| `text` | Plain legal text with source line breaks |
| `html` | HTML representation supplied by Riksdagen |
| `avdelningar` | Additional source structure |

The current response is 146,007 bytes and parses into 70 paragraph records plus 22 transition
records. LAS is now one regression case among 50 laws rather than a separate data pipeline.
