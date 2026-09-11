"""Render review/SPECIMENS.md from the candidate tables plus hand-written notes.

Provision text, character counts and source URLs come from the data. The quoted
parts and the one-line verdicts are hand-written below, from reading each
provision.

    python scripts/write_specimens.py --out review/SPECIMENS.md

Qualifier attachment is deliberately left blank. DIRECTION.md puts that
annotation in human hands, because which part a qualifier hangs on decides the
sign of its removal -- inferring it here would put a heuristic exactly where the
metric belongs.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import scripts.find_candidates as fc
from scripts.audit_markers import ceiling_hits
from scripts.build_silver import POOLS

# (provision_id, duty, part_kind, part_text, qualifier, hand_determinacy, verdict)
#
# `part_kind` is "exception" or "ceiling?". A ceiling is a bound on a granted
# power rather than a carve-out from an obligation, and removing one LOOSENS
# where removing an exception TIGHTENS -- so the two must not share a label.
# `ceiling?` keeps the question open for hand resolution; nothing here resolves
# it automatically.
#
# `hand_determinacy` is my reading of the QUALIFIER's own rung. Where it
# disagrees with the computed `qualifier_determinacy`, the entry says so and the
# renderer prints both.
SPECIMENS: list[tuple[str, str, str, str, str, str, str]] = [
    (
        "sfs-2026-1281:K10P10",
        "Nätmyndigheten ska ta upp en tvist om vilka kostnader som ska debiteras enligt 6, 7 eller 9 §",
        "exception",
        "En tvist ska dock inte prövas",
        "om ansökan om prövning har kommit in till nätmyndigheten senare än två år efter det att den systemansvariga skickat ett skriftligt ställningstagande till den berörda partens senaste kända adress",
        "specific",
        "The worked example DIRECTION.md argues from, and now demonstrably the right shape: the two-year limit sits in the qualifier itself, not in the duty, so it can fall specific → vague → absent. Best specimen in the set.",
    ),
    (
        "sfs-2022-725:P47",
        "Innan kontrollmyndigheten beslutar om sanktionsavgift ska den som avgiften ska tas ut av få tillfälle att yttra sig",
        "exception",
        "får någon sanktionsavgift inte beslutas",
        "Om så inte har skett inom två år från det att överträdelsen ägde rum",
        "specific",
        "Two sentences, one rule each, and the deadline is inside the condition. Missing it extinguishes the authority's power rather than excusing it, which is a useful check that direction follows structure and not who benefits.",
    ),
    (
        "sfs-2026-1281:K16P10",
        "Konsumenten ska underrätta motparten om anspråk på ersättning enligt 6-8 §§ inom två år från det att skadan inträffade",
        "exception",
        "är rätten till ersättning för den uppkomna skadan förlorad",
        "Om konsumenten inte gör det",
        "unmarked",
        "208 characters, one actor, one duty, one consequence. The two-year period is stated in the duty and referred back to by the condition, so annotation has to decide where the deadline slot lives -- a clean test of that call.",
    ),
    (
        "sfs-2026-723:P9",
        "En sanktionsavgift får inte dömas ut",
        "exception",
        "om den misstänkte inte har fått ta del av åklagarens yrkande om sanktionsavgift inom fem år",
        "inom fem år från den dag då uppgiften lämnades eller anmälningsskyldigheten uppkom",
        "specific",
        "A prohibition whose entire content is a limitation period. Minimal and hard to separate duty from qualifier, which makes it a good stress case for the slot schema.",
    ),
    (
        "sfs-2018-1138:K4P8",
        "En licens ska avse en viss tid och får, om inte annat anges i denna lag, ges för högst fem år",
        "exception",
        "ska licensen gälla till dess att spelmyndigheten beslutat om den nya ansökan",
        "Om en ansökan om förnyelse av licensen har getts in senast fyra månader innan giltighetstiden för den gällande licensen går ut",
        "specific",
        "Two deadlines doing different jobs: a duration cap in the duty and a filing cut-off in the qualifier. Good check that slots are distinguished by kind rather than by merely being numbers.",
    ),
    (
        "sfs-2026-408:K8P7",
        "Skjutvapen, ammunition och ljuddämpare som en person vid resa fört med till Sverige för personligt bruk men inte haft rätt att föra in, får föras ut om föremålen anmälts i behörig ordning till Tullverket",
        "exception",
        "tillfaller föremålen staten och ska behandlas som om de hade förverkats",
        "Om föremålen inte förs ut inom fyra månader efter en sådan anmälan eller inom den längre tid som Tullverket bestämmer",
        "specific",
        "The qualifier carries its own escape hatch -- “eller inom den längre tid som Tullverket bestämmer” -- so the deadline is specific but discretionarily extendable. A probe for whether the ladder handles a soft override.",
    ),
    (
        "sfs-2026-772:K7P1",
        "En hyresvärd eller en hyresgäst som vill framställa fordringsanspråk på grund av ett hyresförhållande, ska väcka talan om detta inom två år från det att hyresgästen lämnade lägenheten",
        "exception",
        "är rätten till talan förlorad, om inte annat har avtalats",
        "Görs det senare",
        "unmarked",
        "A limitation period that parties may contract out of, so the exception is an open renvoi to agreement rather than a substantive carve-out. Ordinary private-law shape, easy to twin.",
    ),
    (
        "sfs-2024-945:K15P12",
        "Rätten till ersättning för skada preskriberas om talan inte väcks inom fem år från det att skadan uppkom",
        "exception",
        "Första stycket gäller dock inte",
        "om talan om ersättning enligt 11 § väcks senast ett år efter det att tiden för invändning har gått ut",
        "specific",
        "Both the rule and its exception carry their own specific deadline, five years against one year. Rare and valuable: qualifier death can be watched independently in two positions in the same passage.",
    ),
    (
        "sfs-2025-400:K20P2",
        "ska socialnämnden fatta beslut om att inleda eller inte inleda utredning inom fjorton dagar efter det att anmälan har kommit in",
        "exception",
        "Ett sådant beslut behöver dock inte fattas om det redan pågår en utredning om det barn eller den unge som anmälan avser",
        "Tiden för förhandsbedömningen får endast förlängas om det finns synnerliga skäl",
        "unmarked",
        "A fourteen-day deadline, a `dock` carve-out, and a separate extension rule gated on `synnerliga skäl`. Three distinct moving parts, though the third makes it slightly busier than the specimens above.",
    ),
    (
        "sfs-2024-506:K5P8",
        "ska det bortses från avbrott i medlemskapet eller anslutningen som understiger en månad",
        "exception",
        "Det gäller dock inte avbrott till följd av ett beslut om uteslutning",
        "om den sammanlagda avbrottstiden inte överstiger åtta veckor",
        "specific",
        "The qualifier is a cumulative cap on an aggregate, not a deadline, which broadens the kinds of specific qualifier the corpus covers beyond time limits.",
    ),
    (
        "sfs-2026-1358:K1P10",
        "En e-legitimation ska utfärdas med en giltighetstid om fem år",
        "exception",
        "Regeringen eller den myndighet som regeringen bestämmer får meddela föreskrifter om att den statliga e-legitimationen i särskilt angivna fall ska ha en kortare giltighetstid",
        "Om sökanden inte har fyllt tolv år ska giltighetstiden vara tre år",
        "specific",
        "The qualifier substitutes one specific value for another rather than switching the rule off, so it exercises the ladder's `strengthened` direction, which most specimens here cannot.",
    ),
    (
        "sfs-2024-7:P8",
        "Ett vistelseförbud får förlängas med högst sex månader i taget",
        "ceiling?",
        "Ett förbud med villkor om elektronisk övervakning får dock förlängas med högst tre månader i taget",
        "om förutsättningarna i 3-5 §§ är uppfyllda",
        "unmarked",
        "Flagged `ceiling?`: the `dock` clause lowers the cap on a granted power from six months to three, rather than carving cases out of a duty. If it were annotated as an exception the derivation rule would return the wrong sign.",
    ),
    (
        "sfs-2026-786:K10P20",
        "Den som i en nordisk stat dömts till ett fängelsestraff får utan tillstånd transporteras genom Sverige till en annan nordisk stat för verkställighet av straffet",
        "ceiling?",
        "får Polismyndigheten hålla den som överförs i förvar, dock längst under 48 timmar",
        "Om det är nödvändigt för att transporten ska kunna genomföras",
        "unmarked",
        "Flagged `ceiling?` -- “dock längst under 48 timmar” bounds how far a power reaches, it does not remove cases from a duty. Removing it would leave detention unbounded, which is `loosening`, the opposite of removing an exception.",
    ),
    (
        "sfs-2026-1283:K2P6",
        "Prövningsmyndigheten får, om det finns särskilda skäl, medge att 1. en starkströmsledning eller en transformator- eller kopplingsstation byggs innan det finns en nätkoncession",
        "ceiling?",
        "dock under högst tre år",
        "om det finns särskilda skäl",
        "unmarked",
        "Flagged `ceiling?`. Also the clearest case of the A2 defect in the old sheet: it reported `specific` on “tre år”, but that figure is the ceiling, while the qualifier “om det finns särskilda skäl” is not checkable at all.",
    ),
    (
        "sfs-2026-1601:K6P8",
        "Ett barn eller en ung person som omfattas av bestämmelserna i 1 § får, i den utsträckning det är lämpligt, vistas utanför det särskilda ungdomshemmet under en på förhand bestämd tid",
        "ceiling?",
        "dock högst fyra veckor",
        "i den utsträckning det är lämpligt",
        "vague",
        "Flagged `ceiling?`. A vague qualifier guarding a specific ceiling: the permission is gated on `lämpligt`, which cannot be tested, while the four-week cap can. Watch which of the two dies first.",
    ),
    (
        "sfs-2022-700:K3P9",
        "En utlänning som inte har fyllt 18 år får inte hållas i förvar längre tid än 72 timmar",
        "ceiling?",
        "får utlänningen dock hållas i förvar under ytterligare 72 timmar",
        "Om det finns synnerliga skäl",
        "unmarked",
        "**Content risk, lower intensity than the passage dropped from this sheet:** immigration detention of minors. A model may hedge, and hedging would register as degradation. Keep, but read its generations for refusal artifacts before trusting them. Computed `qualifier_determinacy` says `specific`; that is the span heuristic swallowing the ceiling, since no comma separates condition from consequent.",
    ),
    (
        "sfs-1982-673:P12",
        "Alla arbetsgivare som anlitar arbetstagare till arbete annat än tillfälligt skall lämna arbetstagarna besked om ändringar i fråga om den ordinarie arbetstidens och jourtidens förläggning minst två veckor i förväg",
        "exception",
        "Sådant besked får dock lämnas kortare tid i förväg",
        "om verksamhetens art eller händelser som inte har kunnat förutses ger anledning till det",
        "unmarked",
        "Structurally the closest thing to the founding rest-period example. Computed `qualifier_determinacy` says `specific`, but that is wrong: the two weeks sit in the duty and a prepositional `i fråga om` opened a span that reached them. The qualifier itself is not checkable.",
    ),
    (
        "sfs-1977-480:P12",
        "ska semesterledigheten förläggas så, att arbetstagaren får en ledighetsperiod av minst fyra veckor under juni-augusti",
        "exception",
        "Även utan stöd av avtal får en sådan semesterperiod förläggas till annan tid",
        "när särskilda skäl föranleder det",
        "unmarked",
        "Kept for a structural reason rather than a determinacy one: it carries a qualifier in BOTH positions, `Om inte annat har avtalats` on the duty and `när särskilda skäl` on the exception, so one passage exercises both halves of the derivation rule.",
    ),
    (
        "sfs-2019-742:K10P6",
        "I fråga om uppdragstid för revisorn ska ett tjänstepensionsaktiebolag anses som ett sådant aktiebolag som avses i 9 kap. 21 a § aktiebolagslagen (2005:551)",
        "exception",
        "gäller dock inte uppdrag i ett tjänstepensionsaktiebolag",
        "Möjligheten enligt den paragrafen att förlänga revisionsuppdraget till högst tjugo eller tjugofyra år",
        "unmarked",
        "**Hidden cost, visible here at selection time:** the rule works by cross-reference, so twinning it means inventing the referenced statute too — a second fictional text that must stay consistent across every generation. Budget for that before choosing it.",
    ),
    (
        "sfs-2026-578:P19",
        "Marknadsstörningsavgift ska betalas till Konkurrensverket inom 30 dagar från det att beslutet fick laga kraft",
        "exception",
        "ska Konkurrensverket lämna den obetalda avgiften för indrivning enligt lagen (1993:891) om indrivning av statliga fordringar m.m.",
        "eller inom den längre tid som anges i beslutet",
        "unmarked",
        "**Negative control, kept deliberately and still saying so.** On a close reading the second sentence is a consequence of breach, not an exception to the duty. If hand annotation files it as an exception, the schema is too permissive.",
    ),
]

HEADER = """\
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
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    rows: dict[str, dict] = {}
    for pool in ("v2", "v1"):  # v1 last so the frozen corpus wins on duplicates
        provisions = fc.load_provisions(POOLS[pool].output_path)
        for rank, candidate in enumerate(fc.shortlist(provisions), start=1):
            rows[str(candidate["provision_id"])] = {"pool": pool, "rank": rank, **candidate}

    lines = [HEADER]
    for position, entry in enumerate(SPECIMENS, start=1):
        provision_id, duty, part_kind, part_text, qualifier, hand_state, verdict = entry
        row = rows[provision_id]
        text = str(row["text"])
        for part_name, quote in (("duty", duty), (part_kind, part_text), ("qualifier", qualifier)):
            if quote not in " ".join(text.split()):
                raise SystemExit(f"{provision_id}: {part_name} quote is not verbatim: {quote!r}")

        computed = str(row["qualifier_determinacy"])
        agreement = (
            "" if computed == hand_state else f" — **computed says `{computed}`, disagrees**"
        )
        bounds = [window for window, has_bound in ceiling_hits(text) if has_bound]
        attach_row = (
            "☐ duty ☐ exception ☐ ceiling" if part_kind == "ceiling?" else "☐ duty ☐ exception"
        )
        part_label = "Ceiling?" if part_kind == "ceiling?" else "Exception"

        lines += [
            "",
            "---",
            "",
            f"## {position}. {provision_id}",
            "",
            f"**{row['document_title']}** — {row['label']}  ",
            f"{row['char_count']} characters · pool {row['pool']} · rank {row['rank']}  ",
            f"<{row['source_url']}>",
            "",
            "### Full text",
            "",
            "```",
            text,
            "```",
            "",
            "### Parts",
            "",
            f"- **Duty:** “{duty}”",
            f"- **{part_label}:** “{part_text}”",
            f"- **Qualifier:** “{qualifier}”",
            "",
            "### Annotation",
            "",
            "| Field | Value |",
            "| --- | --- |",
            f"| Qualifier attaches to | {attach_row} — *to be filled in by hand* |",
            f"| Second part is | {'**ceiling or exception? — to be resolved by hand**' if part_kind == 'ceiling?' else 'exception'} |",
            f"| Qualifier determinacy (read) | `{hand_state}`{agreement} |",
            f"| Qualifier bound found | {', '.join(row['qualifier_specific']) or '-'} |",
            f"| `dock` + bound in text | {bounds[0][:60] + '…' if bounds else '-'} |",
            f"| Provision-level determinacy | `{row['determinacy']}` — not the ladder figure |",
            "",
            f"**Why this one:** {verdict}",
        ]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"SPECIMENS | {len(SPECIMENS)} specimens | {args.out}")


if __name__ == "__main__":
    main()
