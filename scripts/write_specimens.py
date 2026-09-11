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
from scripts.build_silver import POOLS

# provision_id -> (duty, exception, qualifier, verdict)
# Quotes are verbatim substrings of the provision text; the renderer asserts it.
SPECIMENS: list[tuple[str, str, str, str, str]] = [
    (
        "sfs-2023-560:P15",
        "Granskningsmyndigheten ska inom tre månader från sitt beslut att inleda en granskning enligt 13 eller 14 § besluta att antingen förbjuda eller godkänna investeringen",
        "får granskningsmyndigheten dock meddela beslutet inom sex månader",
        "Om det finns särskilda skäl",
        "The cleanest specimen in the set: one actor, one deadline, one carve-out that replaces the deadline with a longer one, and nothing else in the provision. Both numbers are checkable, so a twin only has to change two figures and a domain.",
    ),
    (
        "sfs-1977-480:P12",
        "ska semesterledigheten förläggas så, att arbetstagaren får en ledighetsperiod av minst fyra veckor under juni-augusti",
        "Även utan stöd av avtal får en sådan semesterperiod förläggas till annan tid",
        "när särskilda skäl föranleder det",
        "Rare and valuable: it carries a qualifier in BOTH structural positions -- `Om inte annat har avtalats` on the duty and `när särskilda skäl` on the exception -- so one passage exercises both halves of the derivation rule.",
    ),
    (
        "sfs-2022-700:K3P9",
        "En utlänning som inte har fyllt 18 år får inte hållas i förvar längre tid än 72 timmar",
        "får utlänningen dock hållas i förvar under ytterligare 72 timmar",
        "Om det finns synnerliga skäl",
        "A prohibition with a hard limit and a `dock` extension, in 214 characters. The two 72-hour figures make qualifier death immediately visible: drop the condition and detention doubles unconditionally.",
    ),
    (
        "sfs-2016-1117:P14",
        "Gåvor får gallras ut tidigast tre år efter att de togs emot",
        "kan en gåva dock gallras ut tidigare",
        "Om det finns särskilda skäl",
        "Low-stakes subject matter, which makes it easy to twin without the fictional version sounding absurd. Same shape as the detention rule above but about museum gifts.",
    ),
    (
        "sfs-1982-673:P12",
        "Alla arbetsgivare som anlitar arbetstagare till arbete annat än tillfälligt skall lämna arbetstagarna besked om ändringar i fråga om den ordinarie arbetstidens och jourtidens förläggning minst två veckor i förväg",
        "Sådant besked får dock lämnas kortare tid i förväg",
        "om verksamhetens art eller händelser som inte har kunnat förutses ger anledning till det",
        "Structurally the closest thing in the corpus to the founding rest-period example: notice duty, fixed period, `dock` escape, condition on the escape. The exception's qualifier is vague rather than numeric, which is itself worth studying.",
    ),
    (
        "sfs-2019-504:P8",
        "Prövning av oredlighet i forskning enligt denna lag får inte grundas på omständigheter som är äldre än tio år när ärendet inleds",
        "Bestämmelsen i första stycket gäller inte",
        "om det finns särskilda skäl för en prövning",
        "Two sentences, one rule each. The limitation period and its disapplication are in separate paragraphs, so the parts are unusually easy to separate mechanically.",
    ),
    (
        "sfs-2026-1281:K10P10",
        "Nätmyndigheten ska ta upp en tvist om vilka kostnader som ska debiteras enligt 6, 7 eller 9 §",
        "En tvist ska dock inte prövas",
        "om ansökan om prövning har kommit in till nätmyndigheten senare än två år efter det att den systemansvariga skickat ett skriftligt ställningstagande till den berörda partens senaste kända adress",
        "The worked example DIRECTION.md is built on. Included so the corpus contains the passage the specification argues from; drop its qualifier and the exception swallows the rule.",
    ),
    (
        "sfs-2026-1281:K9P1",
        "En systemansvarigs nätverksamhet ska för en tillsynsperiod ha en intäktsram som beslutas av nätmyndigheten. Tillsynsperioden ska vara fyra kalenderår",
        "om det inte finns särskilda skäl för en annan tidsperiod",
        "fyra kalenderår",
        "Awkward in an instructive way: the carve-out and the qualifier are the same clause, so annotation has to decide whether `om det inte finns särskilda skäl` is an exception or a condition on the duty. Good test of the slot schema.",
    ),
    (
        "sfs-2022-725:P47",
        "Innan kontrollmyndigheten beslutar om sanktionsavgift ska den som avgiften ska tas ut av få tillfälle att yttra sig",
        "får någon sanktionsavgift inte beslutas",
        "Om så inte har skett inom två år från det att överträdelsen ägde rum",
        "The consequence runs the other way from most specimens here: missing the deadline extinguishes the authority's power rather than excusing it. Useful contrast when checking that direction is computed from structure and not from who benefits.",
    ),
    (
        "sfs-2026-786:K10P20",
        "Den som i en nordisk stat dömts till ett fängelsestraff får utan tillstånd transporteras genom Sverige till en annan nordisk stat för verkställighet av straffet",
        "får Polismyndigheten hålla den som överförs i förvar, dock längst under 48 timmar",
        "Om det är nödvändigt för att transporten ska kunna genomföras",
        "A permission, a power that depends on necessity, and a hard ceiling on that power. Three distinct slots with no overlap.",
    ),
    (
        "sfs-2026-1283:K2P6",
        "Prövningsmyndigheten får, om det finns särskilda skäl, medge att 1. en starkströmsledning eller en transformator- eller kopplingsstation byggs innan det finns en nätkoncession",
        "dock under högst tre år",
        "om det finns särskilda skäl",
        "The qualifier is embedded mid-sentence between commas, unlike most specimens where it trails. Worth having one of these so the annotation format is not accidentally tuned to trailing conditions.",
    ),
    (
        "sfs-2018-1138:K4P8",
        "En licens ska avse en viss tid och får, om inte annat anges i denna lag, ges för högst fem år",
        "ska licensen gälla till dess att spelmyndigheten beslutat om den nya ansökan",
        "Om en ansökan om förnyelse av licensen har getts in senast fyra månader innan giltighetstiden för den gällande licensen går ut",
        "Two deadlines doing different jobs -- a duration cap and a filing cut-off -- which makes it a good check that slots are distinguished by kind and not merely by being numbers.",
    ),
    (
        "sfs-2022-482:K5P37",
        "Regleringsmyndigheten ska i ett ärende enligt 22 § ge berörda parter skälig tid att yttra sig över det erbjudna åtagandet. Tiden ska uppgå till minst 30 dagar",
        "Parterna behöver dock inte ges tillfälle att yttra sig om det är uppenbart att åtagandet inte uppfyller relevanta krav",
        "om det inte finns särskilda skäl mot det",
        "Contains both rungs of the determinacy ladder in one provision: `skälig tid` is vague, `minst 30 dagar` is specific, and they qualify the same duty. The richest specimen here for studying how vagueness and precision degrade differently.",
    ),
    (
        "sfs-2026-1601:K6P8",
        "Ett barn eller en ung person som omfattas av bestämmelserna i 1 § får, i den utsträckning det är lämpligt, vistas utanför det särskilda ungdomshemmet under en på förhand bestämd tid",
        "dock högst fyra veckor",
        "i den utsträckning det är lämpligt",
        "The specimen that motivated the new `i den utsträckning` marker. Its qualifier is vague and its ceiling is specific, sitting on the same permission -- a compact case of a testable limit guarding an untestable one.",
    ),
    (
        "sfs-2024-237:P2",
        "Ett kirurgiskt ingrepp får göras på den som har fyllt 18 år",
        "På en person som är under 23 år får dock könskörtlarna avlägsnas",
        "endast om det finns synnerliga skäl",
        "A permission with an age gate and a narrower rule for a sub-group. Structurally clean; note the subject matter is sensitive, so a fictional twin should move well away from the domain rather than lightly disguise it.",
    ),
    (
        "sfs-1982-80:P32a",
        "En arbetstagare har rätt att kvarstå i anställningen till utgången av den månad då han eller hon fyller 69 år",
        "om inte något annat följer av denna lag",
        "till utgången av den månad då han eller hon fyller 69 år",
        "The shortest specimen at 167 characters, and the thinnest: its exception is an open renvoi to the rest of the statute rather than a substantive carve-out. Included as a deliberate low-content control.",
    ),
    (
        "sfs-2026-408:K8P7",
        "Skjutvapen, ammunition och ljuddämpare som en person vid resa fört med till Sverige för personligt bruk men inte haft rätt att föra in, får föras ut om föremålen anmälts i behörig ordning till Tullverket",
        "tillfaller föremålen staten och ska behandlas som om de hade förverkats",
        "Om föremålen inte förs ut inom fyra månader efter en sådan anmälan eller inom den längre tid som Tullverket bestämmer",
        "The qualifier has an escape hatch of its own -- `eller inom den längre tid som Tullverket bestämmer` -- so the deadline is specific but overridable. A good probe for whether the ladder handles a discretionary extension.",
    ),
    (
        "sfs-2019-742:K10P6",
        "I fråga om uppdragstid för revisorn ska ett tjänstepensionsaktiebolag anses som ett sådant aktiebolag som avses i 9 kap. 21 a § aktiebolagslagen (2005:551)",
        "gäller dock inte uppdrag i ett tjänstepensionsaktiebolag",
        "Möjligheten enligt den paragrafen att förlänga revisionsuppdraget till högst tjugo eller tjugofyra år",
        "Awkward, and included as one: the rule works by cross-reference, so the duty is only legible with another statute open. Worth one specimen of this shape because cross-referential rules are common and may degrade differently.",
    ),
    (
        "sfs-2026-723:P9",
        "En sanktionsavgift får inte dömas ut",
        "om den misstänkte inte har fått ta del av åklagarens yrkande om sanktionsavgift inom fem år",
        "inom fem år från den dag då uppgiften lämnades eller anmälningsskyldigheten uppkom",
        "A single sentence carrying a prohibition whose whole content is a limitation period. Minimal, but the duty and the qualifier are hard to separate, which makes it a useful stress case for the slot schema.",
    ),
    (
        "sfs-2026-578:P19",
        "Marknadsstörningsavgift ska betalas till Konkurrensverket inom 30 dagar från det att beslutet fick laga kraft",
        "ska Konkurrensverket lämna den obetalda avgiften för indrivning enligt lagen (1993:891) om indrivning av statliga fordringar m.m.",
        "eller inom den längre tid som anges i beslutet",
        "Not a carve-out at all on a close reading -- the second sentence is a consequence of breach, not an exception to the duty. Kept as a negative control: if annotation treats it as an exception, the schema is too permissive.",
    ),
]

HEADER = """\
# Specimen sheet

Twenty candidates to pick a twinned corpus from, drawn from both pools and
capped at two per statute so no single law dominates the way Elmarknadslag once
contributed 72 of 460 candidates. Nineteen documents are represented.

Every specimen is `determinacy = specific` and under 400 characters: a checkable
qualifier makes qualifier death observable, and a short passage can be hand
twinned without rewriting a page of prose.

**Ordered best-first.** "Best" here means, in order: all three parts present and
separable; the qualifier numeric and therefore testable; one coherent rule
rather than a bundle; and subject matter that can be moved to a fictional domain
without the twin sounding absurd. The last four are deliberately awkward -- two
thin ones, one cross-referential, and one negative control -- because a corpus of
only clean cases will not tell you where the schema breaks.

**Qualifier attachment is left blank on purpose.** Which part a qualifier hangs
on decides the sign of its removal, and `DIRECTION.md` assigns that call to hand
annotation. Filling it in from a heuristic would put a guess exactly where the
measurement belongs.

All twenty survive the `om inte` fix proposed in `REVIEW.md`, so this sheet does
not depend on that decision.
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
    for position, (provision_id, duty, exception, qualifier, verdict) in enumerate(
        SPECIMENS, start=1
    ):
        row = rows[provision_id]
        text = str(row["text"])
        for part_name, quote in (
            ("duty", duty),
            ("exception", exception),
            ("qualifier", qualifier),
        ):
            if quote not in " ".join(text.split()):
                raise SystemExit(f"{provision_id}: {part_name} quote is not verbatim: {quote!r}")

        determinacy_note = ", ".join(row["specific_qualifiers"]) or "-"
        vague_note = ", ".join(row["vague_qualifiers"])
        lines += [
            "",
            "---",
            "",
            f"## {position}. {provision_id}",
            "",
            f"**{row['document_title']}** — {row['label']}  ",
            f"{row['char_count']} characters · pool {row['pool']} · rank {rows[provision_id].get('rank', '-')}  ",
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
            f"- **Exception:** “{exception}”",
            f"- **Qualifier:** “{qualifier}”",
            "",
            "### Annotation",
            "",
            "| Field | Value |",
            "| --- | --- |",
            "| Qualifier attaches to | ☐ duty ☐ exception — *to be filled in by hand* |",
            f"| Determinacy (specific) | {determinacy_note} |",
            f"| Determinacy (vague) | {vague_note or '-'} |",
            f"| Markers fired | duty {row['duty_markers']}, exception {row['exception_markers']}, qualifier {row['qualifier_markers']} |",
            "",
            f"**Why this one:** {verdict}",
        ]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"SPECIMENS | {len(SPECIMENS)} specimens | {args.out}")


if __name__ == "__main__":
    main()
