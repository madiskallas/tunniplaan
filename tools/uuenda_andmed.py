#!/usr/bin/env python3
"""Laeb Haabneeme Kooli EduPage'ist klassi tunniplaani ja kirjutab selle faili andmed.js.

Kasutamine:  python3 tools/uuenda_andmed.py [KLASS]     (vaikimisi 4B)

EduPage ei luba brauseril andmeid otse teiselt aadressilt lugeda (CORS),
seepärast hoiame tunniplaani koopiat siinsamas repos.
"""
import json
import re
import sys
import urllib.request
from datetime import date
from pathlib import Path

KOOL = "https://haabneeme.edupage.org"
KLASS = sys.argv[1] if len(sys.argv) > 1 else "4B"
VALJUND = Path(__file__).resolve().parent.parent / "andmed.js"

PAEVAD = ["Esmaspäev", "Teisipäev", "Kolmapäev", "Neljapäev", "Reede"]

# EduPage'i lühendid -> ainete nimed, mida laps ära tunneb
AINED = {
    "Kk": "Kehaline kasvatus",
    "Mat": "Matemaatika",
    "Ek": "Eesti keel",
    "Ik": "Inglise keel",
    "Inglise": "Inglise keel",
    "InÕ": "Inimeseõpetus",
    "Loodus": "Loodusõpetus",
    "Kunst": "Kunstiõpetus",
    "Mu": "Muusika",
    "Tehno": "Tehnoloogiaõpetus",
    "Kt": "Käsitöö",
    "Jalgrt": "Jalgrattakoolitus",
    "Kl juh RT": "Klassijuhatajatund",
    "Ringitund MUK": "Mudilaskoor (ringitund)",
    "Tantsuline liikumine": "Tantsuline liikumine",
}


def edupage(func, args):
    url = f"{KOOL}/timetable/server/{func}"
    body = json.dumps({"__args": args, "__gsh": "00000000"}).encode()
    req = urllib.request.Request(url, body, {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)["r"]


def main():
    aasta = date.today().year if date.today().month >= 8 else date.today().year - 1
    tt_num = edupage("ttviewer.js?__func=getTTViewerData", [None, aasta])["regular"]["default_num"]
    tabelid = edupage("regulartt.js?__func=regularttGetData", [None, tt_num])["dbiAccessorRes"]["tables"]
    T = {t["id"]: {r["id"]: r for r in t.get("data_rows", [])} for t in tabelid}

    klass = next(c for c in T["classes"].values() if c["name"] == KLASS)
    ajad = {p["period"]: (p["starttime"], p["endtime"]) for p in T["periods"].values()}

    paevad = [{"nimi": n, "tunnid": []} for n in PAEVAD]
    for kaart in T["cards"].values():
        tund = T["lessons"][kaart["lessonid"]]
        if klass["id"] not in tund["classids"] or "1" not in kaart["days"]:
            continue
        aine = T["subjects"][tund["subjectid"]]
        lyhend = aine["short"]
        nr = int(kaart["period"])
        pikkus = int(tund["durationperiods"])
        algus, lopp = ajad[str(nr)][0], ajad[str(nr + pikkus - 1)][1]

        # "Uj 12.30-13.15" -> ujumine toimub tegelikult teisel ajal kui tunnikell
        aeg = re.search(r"(\d{1,2})\.(\d{2})-(\d{1,2})\.(\d{2})", lyhend)
        if aeg:
            algus = f"{int(aeg[1]):02}:{aeg[2]}"
            lopp = f"{int(aeg[3]):02}:{aeg[4]}"
            nimi = "Ujumine"
        else:
            alus = re.sub(r" [LP]$", "", lyhend)
            nimi = AINED.get(lyhend) or AINED.get(alus) or re.sub(r" [LP]$", "", aine["name"])

        grupid = {T["groups"][g]["name"] for g in tund["groupids"]} - {"Terve klass"}
        paevad[kaart["days"].index("1")]["tunnid"].append({
            "tund": nr,
            "pikkus": pikkus,
            "algus": algus,
            "lopp": lopp,
            "aine": nimi,
            "lyhend": lyhend,
            "opetajad": [T["teachers"][t]["short"] for t in tund["teacherids"]],
            "ruum": ", ".join(T["classrooms"][r]["short"] for r in kaart["classroomids"] if r in T["classrooms"]),
            "grupp": sorted(grupid)[0].replace("Group", "Grupp") if grupid else None,
        })

    for p in paevad:
        p["tunnid"].sort(key=lambda t: (t["tund"], t["grupp"] or ""))

    andmed = {
        "kool": "Haabneeme Kool",
        "klass": KLASS,
        "allikas": f"{KOOL}/timetable/",
        "uuendatud": date.today().isoformat(),
        "tunnikell": [{"tund": int(k), "algus": a, "lopp": l} for k, (a, l) in sorted(ajad.items(), key=lambda x: int(x[0]))],
        "paevad": paevad,
    }
    VALJUND.write_text(
        "// Tunniplaani andmed. Uuendamiseks: python3 tools/uuenda_andmed.py\n"
        "window.TUNNIPLAAN = " + json.dumps(andmed, ensure_ascii=False, indent=2) + ";\n",
        encoding="utf-8",
    )
    print(f"{KLASS}: {sum(len(p['tunnid']) for p in paevad)} tundi -> {VALJUND}")


if __name__ == "__main__":
    main()
