# Specimen sheet

Twenty candidates to pick a twinned corpus from, drawn from both pools and
capped at two per statute. Nineteen statutes are represented.

**Selected on QUALIFIER determinacy, not provision determinacy.** The previous
sheet claimed all twenty were `specific`; they were not. The ladder in
`DIRECTION.md` grades the qualifier, and measuring it over the whole provision
counted deadlines sitting in the duty or the exception. Only five of the previous
twenty had a checkable qualifier of their own. Twelve of these do.

That matters because a vague qualifier has one rung left to fall
(`vague → absent`) while a specific one has two
(`specific → vague → absent`). The founding observation was a specific
qualifier, and the intermediate step is what made it interesting.

**Read this before trusting the count: 14 or 8, depending on a decision you
have not made yet.** The computed `qualifier_determinacy` calls 14 of these 20
specific. Reading each one by hand and grading only the *conditional* clause I
quoted as the qualifier, I get 8. The gap is not a bug in either number — it is
an open question in the schema. In most of these provisions the checkable bound
sits in the duty as a deadline ("ska väcka talan **inom två år**") while the
conditional clause is untestable ("Om konsumenten inte gör det"). `DIRECTION.md`
test case 2 is "Qualifier on duty: `specific` → `absent`", which says a duty
deadline *is* a qualifier — and on that reading 14 is right. On the narrower
reading, where "the qualifier" means the third moving part and not the duty's
own time limit, 8 is right. Six entries say `computed says …, disagrees`; those
are exactly the ones where the question bites.

**Ordered best-first.** "Best" means, in order: the qualifier carries its own
checkable bound; all three parts are separable; one coherent rule rather than a
bundle; and a domain a fictional twin can move to without sounding absurd. The
last five are deliberately awkward — two where the computed determinacy is wrong
and the entry says why, one cross-referential, one carrying content risk, one
negative control — because a sheet of only clean cases will not show where the
schema breaks.

**Two things are left blank on purpose.** Which part a qualifier attaches to,
and whether a `ceiling?` is really a ceiling. Both decide the sign of a removal,
and `DIRECTION.md` puts that call in human hands.

**`ceiling?` is a flag, not a verdict.** Four specimens carry a `dock` clause
that bounds a granted power rather than carving cases out of a duty. Removing a
ceiling *loosens*; removing an exception *tightens*. Nothing here resolves which
it is — see `review/DIRECTION-ceiling-proposal.md`, pending ratification.

One passage from the previous sheet, `sfs-2024-237:P2`, was dropped outright and
not replaced within its domain: a model hedging or refusing on that subject
would register in the data as degradation and be indistinguishable after the
fact from meaning drift.


---

## 1. sfs-2026-1281:K10P10

**Elmarknadslag (2026:1281)** — 10 §  
321 characters · pool v1 · rank 43  
<https://data.riksdagen.se/dokument/sfs-2026-1281.html#K10P10>

### Full text

```
Nätmyndigheten ska ta upp en tvist om vilka kostnader som ska debiteras enligt 6, 7 eller 9 §.

En tvist ska dock inte prövas om ansökan om prövning har kommit in till nätmyndigheten senare än två år efter det att den systemansvariga skickat ett skriftligt ställningstagande till den berörda partens senaste kända adress.
```

### Parts

- **Duty:** “Nätmyndigheten ska ta upp en tvist om vilka kostnader som ska debiteras enligt 6, 7 eller 9 §”
- **Exception:** “En tvist ska dock inte prövas”
- **Qualifier:** “om ansökan om prövning har kommit in till nätmyndigheten senare än två år efter det att den systemansvariga skickat ett skriftligt ställningstagande till den berörda partens senaste kända adress”

### Annotation

| Field | Value |
| --- | --- |
| Qualifier attaches to | ☐ duty ☐ exception — *to be filled in by hand* |
| Second part is | exception |
| Qualifier determinacy (read) | `specific` |
| Qualifier bound found | senare än, två år |
| `dock` + bound in text | - |
| Provision-level determinacy | `specific` — not the ladder figure |

**Why this one:** The worked example DIRECTION.md argues from, and now demonstrably the right shape: the two-year limit sits in the qualifier itself, not in the duty, so it can fall specific → vague → absent. Best specimen in the set.

---

## 2. sfs-2022-725:P47

**Växtskyddslag (2022:725)** — 47 §  
226 characters · pool v2 · rank 129  
<https://data.riksdagen.se/dokument/sfs-2022-725.html#P47>

### Full text

```
Innan kontrollmyndigheten beslutar om sanktionsavgift ska den som avgiften ska tas ut av få tillfälle att yttra sig. Om så inte har skett inom två år från det att överträdelsen ägde rum får någon sanktionsavgift inte beslutas.
```

### Parts

- **Duty:** “Innan kontrollmyndigheten beslutar om sanktionsavgift ska den som avgiften ska tas ut av få tillfälle att yttra sig”
- **Exception:** “får någon sanktionsavgift inte beslutas”
- **Qualifier:** “Om så inte har skett inom två år från det att överträdelsen ägde rum”

### Annotation

| Field | Value |
| --- | --- |
| Qualifier attaches to | ☐ duty ☐ exception — *to be filled in by hand* |
| Second part is | exception |
| Qualifier determinacy (read) | `specific` |
| Qualifier bound found | två år |
| `dock` + bound in text | - |
| Provision-level determinacy | `specific` — not the ladder figure |

**Why this one:** Two sentences, one rule each, and the deadline is inside the condition. Missing it extinguishes the authority's power rather than excusing it, which is a useful check that direction follows structure and not who benefits.

---

## 3. sfs-2026-1281:K16P10

**Elmarknadslag (2026:1281)** — 10 §  
208 characters · pool v1 · rank 93  
<https://data.riksdagen.se/dokument/sfs-2026-1281.html#K16P10>

### Full text

```
Konsumenten ska underrätta motparten om anspråk på ersättning enligt 6-8 §§ inom två år från det att skadan inträffade. Om konsumenten inte gör det, är rätten till ersättning för den uppkomna skadan förlorad.
```

### Parts

- **Duty:** “Konsumenten ska underrätta motparten om anspråk på ersättning enligt 6-8 §§ inom två år från det att skadan inträffade”
- **Exception:** “är rätten till ersättning för den uppkomna skadan förlorad”
- **Qualifier:** “Om konsumenten inte gör det”

### Annotation

| Field | Value |
| --- | --- |
| Qualifier attaches to | ☐ duty ☐ exception — *to be filled in by hand* |
| Second part is | exception |
| Qualifier determinacy (read) | `unmarked` — **computed says `specific`, disagrees** |
| Qualifier bound found | två år |
| `dock` + bound in text | - |
| Provision-level determinacy | `specific` — not the ladder figure |

**Why this one:** 208 characters, one actor, one duty, one consequence. The two-year period is stated in the duty and referred back to by the condition, so annotation has to decide where the deadline slot lives -- a clean test of that call.

---

## 4. sfs-2026-723:P9

**Lag (2026:723) om talan om administrativ sanktionsavgift i mål om bidragsbrott** — 9 §  
200 characters · pool v1 · rank 66  
<https://data.riksdagen.se/dokument/sfs-2026-723.html#P9>

### Full text

```
En sanktionsavgift får inte dömas ut om den misstänkte inte har fått ta del av åklagarens yrkande om sanktionsavgift inom fem år från den dag då uppgiften lämnades eller anmälningsskyldigheten uppkom.
```

### Parts

- **Duty:** “En sanktionsavgift får inte dömas ut”
- **Exception:** “om den misstänkte inte har fått ta del av åklagarens yrkande om sanktionsavgift inom fem år”
- **Qualifier:** “inom fem år från den dag då uppgiften lämnades eller anmälningsskyldigheten uppkom”

### Annotation

| Field | Value |
| --- | --- |
| Qualifier attaches to | ☐ duty ☐ exception — *to be filled in by hand* |
| Second part is | exception |
| Qualifier determinacy (read) | `specific` |
| Qualifier bound found | fem år |
| `dock` + bound in text | - |
| Provision-level determinacy | `specific` — not the ladder figure |

**Why this one:** A prohibition whose entire content is a limitation period. Minimal and hard to separate duty from qualifier, which makes it a good stress case for the slot schema.

---

## 5. sfs-2018-1138:K4P8

**Spellag (2018:1138)** — 8 §  
318 characters · pool v2 · rank 134  
<https://data.riksdagen.se/dokument/sfs-2018-1138.html#K4P8>

### Full text

```
En licens ska avse en viss tid och får, om inte annat anges i denna lag, ges för högst fem år.

Om en ansökan om förnyelse av licensen har getts in senast fyra månader innan giltighetstiden för den gällande licensen går ut, ska licensen gälla till dess att spelmyndigheten beslutat om den nya ansökan. Lag (2022:1674).
```

### Parts

- **Duty:** “En licens ska avse en viss tid och får, om inte annat anges i denna lag, ges för högst fem år”
- **Exception:** “ska licensen gälla till dess att spelmyndigheten beslutat om den nya ansökan”
- **Qualifier:** “Om en ansökan om förnyelse av licensen har getts in senast fyra månader innan giltighetstiden för den gällande licensen går ut”

### Annotation

| Field | Value |
| --- | --- |
| Qualifier attaches to | ☐ duty ☐ exception — *to be filled in by hand* |
| Second part is | exception |
| Qualifier determinacy (read) | `specific` |
| Qualifier bound found | fyra månader |
| `dock` + bound in text | - |
| Provision-level determinacy | `specific` — not the ladder figure |

**Why this one:** Two deadlines doing different jobs: a duration cap in the duty and a filing cut-off in the qualifier. Good check that slots are distinguished by kind rather than by merely being numbers.

---

## 6. sfs-2026-408:K8P7

**Vapenlag (2026:408)** — 7 §  
396 characters · pool v1 · rank 72  
<https://data.riksdagen.se/dokument/sfs-2026-408.html#K8P7>

### Full text

```
Skjutvapen, ammunition och ljuddämpare som en person vid resa fört med till Sverige för personligt bruk men inte haft rätt att föra in, får föras ut om föremålen anmälts i behörig ordning till Tullverket. Om föremålen inte förs ut inom fyra månader efter en sådan anmälan eller inom den längre tid som Tullverket bestämmer, tillfaller föremålen staten och ska behandlas som om de hade förverkats.
```

### Parts

- **Duty:** “Skjutvapen, ammunition och ljuddämpare som en person vid resa fört med till Sverige för personligt bruk men inte haft rätt att föra in, får föras ut om föremålen anmälts i behörig ordning till Tullverket”
- **Exception:** “tillfaller föremålen staten och ska behandlas som om de hade förverkats”
- **Qualifier:** “Om föremålen inte förs ut inom fyra månader efter en sådan anmälan eller inom den längre tid som Tullverket bestämmer”

### Annotation

| Field | Value |
| --- | --- |
| Qualifier attaches to | ☐ duty ☐ exception — *to be filled in by hand* |
| Second part is | exception |
| Qualifier determinacy (read) | `specific` |
| Qualifier bound found | fyra månader |
| `dock` + bound in text | - |
| Provision-level determinacy | `specific` — not the ladder figure |

**Why this one:** The qualifier carries its own escape hatch -- “eller inom den längre tid som Tullverket bestämmer” -- so the deadline is specific but discretionarily extendable. A probe for whether the ladder handles a soft override.

---

## 7. sfs-2026-772:K7P1

**Privatuthyrningslag (2026:772)** — 1 §  
402 characters · pool v1 · rank 112  
<https://data.riksdagen.se/dokument/sfs-2026-772.html#K7P1>

### Full text

```
En hyresvärd eller en hyresgäst som vill framställa fordringsanspråk på grund av ett hyresförhållande, ska väcka talan om detta inom två år från det att hyresgästen lämnade lägenheten. Görs det senare är rätten till talan förlorad, om inte annat har avtalats.

Om den ena parten har väckt talan i rätt tid, har den andra parten rätt till kvittning, fastän hans eller hennes rätt till talan är förlorad.
```

### Parts

- **Duty:** “En hyresvärd eller en hyresgäst som vill framställa fordringsanspråk på grund av ett hyresförhållande, ska väcka talan om detta inom två år från det att hyresgästen lämnade lägenheten”
- **Exception:** “är rätten till talan förlorad, om inte annat har avtalats”
- **Qualifier:** “Görs det senare”

### Annotation

| Field | Value |
| --- | --- |
| Qualifier attaches to | ☐ duty ☐ exception — *to be filled in by hand* |
| Second part is | exception |
| Qualifier determinacy (read) | `unmarked` — **computed says `specific`, disagrees** |
| Qualifier bound found | två år |
| `dock` + bound in text | - |
| Provision-level determinacy | `specific` — not the ladder figure |

**Why this one:** A limitation period that parties may contract out of, so the exception is an open renvoi to agreement rather than a substantive carve-out. Ordinary private-law shape, easy to twin.

---

## 8. sfs-2024-945:K15P12

**Patentlag (2024:945)** — 12 §  
375 characters · pool v2 · rank 140  
<https://data.riksdagen.se/dokument/sfs-2024-945.html#K15P12>

### Full text

```
Rätten till ersättning för skada preskriberas om talan inte väcks inom fem år från det att skadan uppkom.

Första stycket gäller dock inte om talan om ersättning enligt
11 § väcks senast ett år efter det att tiden för invändning har gått ut eller, om invändning har gjorts, senast ett år efter det att Patent- och registreringsverket beslutade att patentet ska upprätthållas.
```

### Parts

- **Duty:** “Rätten till ersättning för skada preskriberas om talan inte väcks inom fem år från det att skadan uppkom”
- **Exception:** “Första stycket gäller dock inte”
- **Qualifier:** “om talan om ersättning enligt 11 § väcks senast ett år efter det att tiden för invändning har gått ut”

### Annotation

| Field | Value |
| --- | --- |
| Qualifier attaches to | ☐ duty ☐ exception — *to be filled in by hand* |
| Second part is | exception |
| Qualifier determinacy (read) | `specific` |
| Qualifier bound found | ett år, fem år |
| `dock` + bound in text | dock inte om talan om ersättning enligt 11 § väcks senast et… |
| Provision-level determinacy | `specific` — not the ladder figure |

**Why this one:** Both the rule and its exception carry their own specific deadline, five years against one year. Rare and valuable: qualifier death can be watched independently in two positions in the same passage.

---

## 9. sfs-2025-400:K20P2

**Socialtjänstlag (2025:400)** — 2 §  
407 characters · pool v2 · rank 30  
<https://data.riksdagen.se/dokument/sfs-2025-400.html#K20P2>

### Full text

```
Om en anmälan till socialnämnden gäller barn eller unga, ska socialnämnden fatta beslut om att inleda eller inte inleda utredning inom fjorton dagar efter det att anmälan har kommit in (förhandsbedömning). Ett sådant beslut behöver dock inte fattas om det redan pågår en utredning om det barn eller den unge som anmälan avser. Tiden för förhandsbedömningen får endast förlängas om det finns synnerliga skäl.
```

### Parts

- **Duty:** “ska socialnämnden fatta beslut om att inleda eller inte inleda utredning inom fjorton dagar efter det att anmälan har kommit in”
- **Exception:** “Ett sådant beslut behöver dock inte fattas om det redan pågår en utredning om det barn eller den unge som anmälan avser”
- **Qualifier:** “Tiden för förhandsbedömningen får endast förlängas om det finns synnerliga skäl”

### Annotation

| Field | Value |
| --- | --- |
| Qualifier attaches to | ☐ duty ☐ exception — *to be filled in by hand* |
| Second part is | exception |
| Qualifier determinacy (read) | `unmarked` — **computed says `specific`, disagrees** |
| Qualifier bound found | fjorton dagar |
| `dock` + bound in text | - |
| Provision-level determinacy | `specific` — not the ladder figure |

**Why this one:** A fourteen-day deadline, a `dock` carve-out, and a separate extension rule gated on `synnerliga skäl`. Three distinct moving parts, though the third makes it slightly busier than the specimens above.

---

## 10. sfs-2024-506:K5P8

**Lag (2024:506) om arbetslöshetsförsäkring** — 8 §  
342 characters · pool v2 · rank 137  
<https://data.riksdagen.se/dokument/sfs-2024-506.html#K5P8>

### Full text

```
När tiden med medlemskap eller anslutning beräknas enligt
4 eller 5 § ska det bortses från avbrott i medlemskapet eller anslutningen som understiger en månad, om den sammanlagda avbrottstiden inte överstiger åtta veckor. Det gäller dock inte avbrott till följd av ett beslut om uteslutning enligt
37 § lagen (1997:239) om arbetslöshetskassor.
```

### Parts

- **Duty:** “ska det bortses från avbrott i medlemskapet eller anslutningen som understiger en månad”
- **Exception:** “Det gäller dock inte avbrott till följd av ett beslut om uteslutning”
- **Qualifier:** “om den sammanlagda avbrottstiden inte överstiger åtta veckor”

### Annotation

| Field | Value |
| --- | --- |
| Qualifier attaches to | ☐ duty ☐ exception — *to be filled in by hand* |
| Second part is | exception |
| Qualifier determinacy (read) | `specific` |
| Qualifier bound found | åtta veckor |
| `dock` + bound in text | - |
| Provision-level determinacy | `specific` — not the ladder figure |

**Why this one:** The qualifier is a cumulative cap on an aggregate, not a deadline, which broadens the kinds of specific qualifier the corpus covers beyond time limits.

---

## 11. sfs-2026-1358:K1P10

**Lag (2026:1358) om statlig e-legitimation och elektronisk identifiering** — 10 §  
306 characters · pool v1 · rank 68  
<https://data.riksdagen.se/dokument/sfs-2026-1358.html#K1P10>

### Full text

```
En e-legitimation ska utfärdas med en giltighetstid om fem år. Om sökanden inte har fyllt tolv år ska giltighetstiden vara tre år.

Regeringen eller den myndighet som regeringen bestämmer får meddela föreskrifter om att den statliga e-legitimationen i särskilt angivna fall ska ha en kortare giltighetstid.
```

### Parts

- **Duty:** “En e-legitimation ska utfärdas med en giltighetstid om fem år”
- **Exception:** “Regeringen eller den myndighet som regeringen bestämmer får meddela föreskrifter om att den statliga e-legitimationen i särskilt angivna fall ska ha en kortare giltighetstid”
- **Qualifier:** “Om sökanden inte har fyllt tolv år ska giltighetstiden vara tre år”

### Annotation

| Field | Value |
| --- | --- |
| Qualifier attaches to | ☐ duty ☐ exception — *to be filled in by hand* |
| Second part is | exception |
| Qualifier determinacy (read) | `specific` |
| Qualifier bound found | fem år, tolv år, tre år |
| `dock` + bound in text | - |
| Provision-level determinacy | `specific` — not the ladder figure |

**Why this one:** The qualifier substitutes one specific value for another rather than switching the rule off, so it exercises the ladder's `strengthened` direction, which most specimens here cannot.

---

## 12. sfs-2024-7:P8

**Lag (2024:7) om preventiva vistelseförbud** — 8 §  
333 characters · pool v2 · rank 136  
<https://data.riksdagen.se/dokument/sfs-2024-7.html#P8>

### Full text

```
Ett vistelseförbud ska gälla för en viss tid, högst sex månader.

Vistelseförbudet gäller omedelbart, om inte annat beslutas.

Ett vistelseförbud får förlängas med högst sex månader i taget om förutsättningarna i 3-5 §§ är uppfyllda. Ett förbud med villkor om elektronisk övervakning får dock förlängas med högst tre månader i taget.
```

### Parts

- **Duty:** “Ett vistelseförbud får förlängas med högst sex månader i taget”
- **Ceiling?:** “Ett förbud med villkor om elektronisk övervakning får dock förlängas med högst tre månader i taget”
- **Qualifier:** “om förutsättningarna i 3-5 §§ är uppfyllda”

### Annotation

| Field | Value |
| --- | --- |
| Qualifier attaches to | ☐ duty ☐ exception ☐ ceiling — *to be filled in by hand* |
| Second part is | **ceiling or exception? — to be resolved by hand** |
| Qualifier determinacy (read) | `unmarked` — **computed says `specific`, disagrees** |
| Qualifier bound found | tre månader |
| `dock` + bound in text | dock förlängas med högst tre månader i taget.… |
| Provision-level determinacy | `specific` — not the ladder figure |

**Why this one:** Flagged `ceiling?`: the `dock` clause lowers the cap on a granted power from six months to three, rather than carving cases out of a duty. If it were annotated as an exception the derivation rule would return the wrong sign.

---

## 13. sfs-2026-786:K10P20

**Lag (2026:786) om nordisk verkställighet i brottmål** — 20 §  
308 characters · pool v1 · rank 69  
<https://data.riksdagen.se/dokument/sfs-2026-786.html#K10P20>

### Full text

```
Den som i en nordisk stat dömts till ett fängelsestraff får utan tillstånd transporteras genom Sverige till en annan nordisk stat för verkställighet av straffet.

Om det är nödvändigt för att transporten ska kunna genomföras, får Polismyndigheten hålla den som överförs i förvar, dock längst under 48 timmar.
```

### Parts

- **Duty:** “Den som i en nordisk stat dömts till ett fängelsestraff får utan tillstånd transporteras genom Sverige till en annan nordisk stat för verkställighet av straffet”
- **Ceiling?:** “får Polismyndigheten hålla den som överförs i förvar, dock längst under 48 timmar”
- **Qualifier:** “Om det är nödvändigt för att transporten ska kunna genomföras”

### Annotation

| Field | Value |
| --- | --- |
| Qualifier attaches to | ☐ duty ☐ exception ☐ ceiling — *to be filled in by hand* |
| Second part is | **ceiling or exception? — to be resolved by hand** |
| Qualifier determinacy (read) | `unmarked` |
| Qualifier bound found | - |
| `dock` + bound in text | dock längst under 48 timmar.… |
| Provision-level determinacy | `specific` — not the ladder figure |

**Why this one:** Flagged `ceiling?` -- “dock längst under 48 timmar” bounds how far a power reaches, it does not remove cases from a duty. Removing it would leave detention unbounded, which is `loosening`, the opposite of removing an exception.

---

## 14. sfs-2026-1283:K2P6

**Lag (2026:1283) om elektriska ledningar** — 6 §  
327 characters · pool v1 · rank 44  
<https://data.riksdagen.se/dokument/sfs-2026-1283.html#K2P6>

### Full text

```
Prövningsmyndigheten får, om det finns särskilda skäl, medge att

1. en starkströmsledning eller en transformator- eller kopplingsstation byggs innan det finns en nätkoncession, och

2. starkströmsledningen, när den är färdig att tas i bruk, används i avvaktan på att koncessionsfrågan slutligt avgörs, dock under högst tre år.
```

### Parts

- **Duty:** “Prövningsmyndigheten får, om det finns särskilda skäl, medge att 1. en starkströmsledning eller en transformator- eller kopplingsstation byggs innan det finns en nätkoncession”
- **Ceiling?:** “dock under högst tre år”
- **Qualifier:** “om det finns särskilda skäl”

### Annotation

| Field | Value |
| --- | --- |
| Qualifier attaches to | ☐ duty ☐ exception ☐ ceiling — *to be filled in by hand* |
| Second part is | **ceiling or exception? — to be resolved by hand** |
| Qualifier determinacy (read) | `unmarked` |
| Qualifier bound found | - |
| `dock` + bound in text | dock under högst tre år.… |
| Provision-level determinacy | `specific` — not the ladder figure |

**Why this one:** Flagged `ceiling?`. Also the clearest case of the A2 defect in the old sheet: it reported `specific` on “tre år”, but that figure is the ceiling, while the qualifier “om det finns särskilda skäl” is not checkable at all.

---

## 15. sfs-2026-1601:K6P8

**Lag (2026:1601) om särskilda befogenheter för den statliga barn- och ungdomsvården** — 8 §  
261 characters · pool v2 · rank 67  
<https://data.riksdagen.se/dokument/sfs-2026-1601.html#K6P8>

### Full text

```
Ett barn eller en ung person som omfattas av bestämmelserna i 1 § får, i den utsträckning det är lämpligt, vistas utanför det särskilda ungdomshemmet under en på förhand bestämd tid, dock högst fyra veckor.

Innan beslut fattas ska samråd ske med socialnämnden.
```

### Parts

- **Duty:** “Ett barn eller en ung person som omfattas av bestämmelserna i 1 § får, i den utsträckning det är lämpligt, vistas utanför det särskilda ungdomshemmet under en på förhand bestämd tid”
- **Ceiling?:** “dock högst fyra veckor”
- **Qualifier:** “i den utsträckning det är lämpligt”

### Annotation

| Field | Value |
| --- | --- |
| Qualifier attaches to | ☐ duty ☐ exception ☐ ceiling — *to be filled in by hand* |
| Second part is | **ceiling or exception? — to be resolved by hand** |
| Qualifier determinacy (read) | `vague` |
| Qualifier bound found | - |
| `dock` + bound in text | dock högst fyra veckor.  Innan beslut fattas ska samråd ske … |
| Provision-level determinacy | `specific` — not the ladder figure |

**Why this one:** Flagged `ceiling?`. A vague qualifier guarding a specific ceiling: the permission is gated on `lämpligt`, which cannot be tested, while the four-week cap can. Watch which of the two dies first.

---

## 16. sfs-2022-700:K3P9

**Lag (2022:700) om särskild kontroll av vissa utlänningar** — 9 §  
214 characters · pool v2 · rank 127  
<https://data.riksdagen.se/dokument/sfs-2022-700.html#K3P9>

### Full text

```
/Upphör att gälla U:2027-03-01/
En utlänning som inte har fyllt 18 år får inte hållas i förvar längre tid än 72 timmar. Om det finns synnerliga skäl får utlänningen dock hållas i förvar under ytterligare 72 timmar.
```

### Parts

- **Duty:** “En utlänning som inte har fyllt 18 år får inte hållas i förvar längre tid än 72 timmar”
- **Ceiling?:** “får utlänningen dock hållas i förvar under ytterligare 72 timmar”
- **Qualifier:** “Om det finns synnerliga skäl”

### Annotation

| Field | Value |
| --- | --- |
| Qualifier attaches to | ☐ duty ☐ exception ☐ ceiling — *to be filled in by hand* |
| Second part is | **ceiling or exception? — to be resolved by hand** |
| Qualifier determinacy (read) | `unmarked` — **computed says `specific`, disagrees** |
| Qualifier bound found | 72 timmar |
| `dock` + bound in text | - |
| Provision-level determinacy | `specific` — not the ladder figure |

**Why this one:** **Content risk, lower intensity than the passage dropped from this sheet:** immigration detention of minors. A model may hedge, and hedging would register as degradation. Keep, but read its generations for refusal artifacts before trusting them. Computed `qualifier_determinacy` says `specific`; that is the span heuristic swallowing the ceiling, since no comma separates condition from consequent.

---

## 17. sfs-1982-673:P12

**Arbetstidslag (1982:673)** — 12 §  
355 characters · pool v1 · rank 16  
<https://data.riksdagen.se/dokument/sfs-1982-673.html#P12>

### Full text

```
Alla arbetsgivare som anlitar arbetstagare till arbete annat än tillfälligt skall lämna arbetstagarna besked om ändringar i fråga om den ordinarie arbetstidens och jourtidens förläggning minst två veckor i förväg. Sådant besked får dock lämnas kortare tid i förväg, om verksamhetens art eller händelser som inte har kunnat förutses ger anledning till det.
```

### Parts

- **Duty:** “Alla arbetsgivare som anlitar arbetstagare till arbete annat än tillfälligt skall lämna arbetstagarna besked om ändringar i fråga om den ordinarie arbetstidens och jourtidens förläggning minst två veckor i förväg”
- **Exception:** “Sådant besked får dock lämnas kortare tid i förväg”
- **Qualifier:** “om verksamhetens art eller händelser som inte har kunnat förutses ger anledning till det”

### Annotation

| Field | Value |
| --- | --- |
| Qualifier attaches to | ☐ duty ☐ exception — *to be filled in by hand* |
| Second part is | exception |
| Qualifier determinacy (read) | `unmarked` — **computed says `specific`, disagrees** |
| Qualifier bound found | två veckor |
| `dock` + bound in text | - |
| Provision-level determinacy | `specific` — not the ladder figure |

**Why this one:** Structurally the closest thing to the founding rest-period example. Computed `qualifier_determinacy` says `specific`, but that is wrong: the two weeks sit in the duty and a prepositional `i fråga om` opened a span that reached them. The qualifier itself is not checkable.

---

## 18. sfs-1977-480:P12

**Semesterlag (1977:480)** — 12 §  
276 characters · pool v1 · rank 14  
<https://data.riksdagen.se/dokument/sfs-1977-480.html#P12>

### Full text

```
Om inte annat har avtalats, ska semesterledigheten förläggas så, att arbetstagaren får en ledighetsperiod av minst fyra veckor under juni-augusti. Även utan stöd av avtal får en sådan semesterperiod förläggas till annan tid, när särskilda skäl föranleder det. Lag (2009:1439).
```

### Parts

- **Duty:** “ska semesterledigheten förläggas så, att arbetstagaren får en ledighetsperiod av minst fyra veckor under juni-augusti”
- **Exception:** “Även utan stöd av avtal får en sådan semesterperiod förläggas till annan tid”
- **Qualifier:** “när särskilda skäl föranleder det”

### Annotation

| Field | Value |
| --- | --- |
| Qualifier attaches to | ☐ duty ☐ exception — *to be filled in by hand* |
| Second part is | exception |
| Qualifier determinacy (read) | `unmarked` |
| Qualifier bound found | - |
| `dock` + bound in text | - |
| Provision-level determinacy | `specific` — not the ladder figure |

**Why this one:** Kept for a structural reason rather than a determinacy one: it carries a qualifier in BOTH positions, `Om inte annat har avtalats` on the duty and `när särskilda skäl` on the exception, so one passage exercises both halves of the derivation rule.

---

## 19. sfs-2019-742:K10P6

**Lag (2019:742) om tjänstepensionsföretag** — 6 §  
316 characters · pool v2 · rank 133  
<https://data.riksdagen.se/dokument/sfs-2019-742.html#K10P6>

### Full text

```
I fråga om uppdragstid för revisorn ska ett tjänstepensionsaktiebolag anses som ett sådant aktiebolag som avses i 9 kap. 21 a § aktiebolagslagen (2005:551). Möjligheten enligt den paragrafen att förlänga revisionsuppdraget till högst tjugo eller tjugofyra år gäller dock inte uppdrag i ett tjänstepensionsaktiebolag.
```

### Parts

- **Duty:** “I fråga om uppdragstid för revisorn ska ett tjänstepensionsaktiebolag anses som ett sådant aktiebolag som avses i 9 kap. 21 a § aktiebolagslagen (2005:551)”
- **Exception:** “gäller dock inte uppdrag i ett tjänstepensionsaktiebolag”
- **Qualifier:** “Möjligheten enligt den paragrafen att förlänga revisionsuppdraget till högst tjugo eller tjugofyra år”

### Annotation

| Field | Value |
| --- | --- |
| Qualifier attaches to | ☐ duty ☐ exception — *to be filled in by hand* |
| Second part is | exception |
| Qualifier determinacy (read) | `unmarked` |
| Qualifier bound found | - |
| `dock` + bound in text | - |
| Provision-level determinacy | `specific` — not the ladder figure |

**Why this one:** **Hidden cost, visible here at selection time:** the rule works by cross-reference, so twinning it means inventing the referenced statute too — a second fictional text that must stay consistent across every generation. Budget for that before choosing it.

---

## 20. sfs-2026-578:P19

**Lag (2026:578) om offentlig säljverksamhet** — 19 §  
337 characters · pool v1 · rank 103  
<https://data.riksdagen.se/dokument/sfs-2026-578.html#P19>

### Full text

```
Marknadsstörningsavgift ska betalas till Konkurrensverket inom 30 dagar från det att beslutet fick laga kraft eller inom den längre tid som anges i beslutet.

Om marknadsstörningsavgiften inte betalas i tid, ska Konkurrensverket lämna den obetalda avgiften för indrivning enligt lagen (1993:891) om indrivning av statliga fordringar m.m.
```

### Parts

- **Duty:** “Marknadsstörningsavgift ska betalas till Konkurrensverket inom 30 dagar från det att beslutet fick laga kraft”
- **Exception:** “ska Konkurrensverket lämna den obetalda avgiften för indrivning enligt lagen (1993:891) om indrivning av statliga fordringar m.m.”
- **Qualifier:** “eller inom den längre tid som anges i beslutet”

### Annotation

| Field | Value |
| --- | --- |
| Qualifier attaches to | ☐ duty ☐ exception — *to be filled in by hand* |
| Second part is | exception |
| Qualifier determinacy (read) | `unmarked` |
| Qualifier bound found | - |
| `dock` + bound in text | - |
| Provision-level determinacy | `specific` — not the ladder figure |

**Why this one:** **Negative control, kept deliberately and still saying so.** On a close reading the second sentence is a consequence of breach, not an exception to the duty. If hand annotation files it as an exception, the schema is too permissive.
