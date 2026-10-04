#!/usr/bin/env python3
"""Laeb Haabneeme Kooli EduPage'ist klassi tunniplaani kuupäevade kaupa ja kirjutab selle faili andmed.js.

Kasutamine:  python3 tools/uuenda_andmed.py [KLASS]     (vaikimisi 4B)

EduPage ei luba brauseril andmeid otse teiselt aadressilt lugeda (CORS),
seepärast käivitab GitHub Actions selle skripti regulaarselt
(.github/workflows/uuenda-andmed.yml) ja paneb värske koopia reposse.

Andmed on kuupäevapõhised: kui kool avaldab EduPage'is uue tunniplaani
versiooni, tulevad muudatused järgmise uuendusega kaasa.
"""
import json
import re
import sys
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

KOOL = "https://haabneeme.edupage.org"
KLASS = sys.argv[1] if len(sys.argv) > 1 else "4B"
VALJUND = Path(__file__).resolve().parent.parent / "andmed.js"
NADALAID = 3  # mitu nädalat ette (jooksev nädal kaasa arvatud)

PAEVAD = ["Esmaspäev", "Teisipäev", "Kolmapäev", "Neljapäev", "Reede", "Laupäev", "Pühapäev"]

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


def aine_nimi(lyhend, taisnimi):
    alus = re.sub(r" [LP]$", "", lyhend)
    return AINED.get(lyhend) or AINED.get(alus) or re.sub(r" [LP]$", "", taisnimi)


def main():
    tana = datetime.now(ZoneInfo("Europe/Tallinn")).date()
    aasta = tana.year if tana.month >= 8 else tana.year - 1
    algus = tana - timedelta(days=tana.weekday())  # jooksva nädala esmaspäev
    lopp = algus + timedelta(weeks=NADALAID, days=-1)

    # Nimed (ained, õpetajad, ruumid) tulevad kehtivast põhitunniplaanist
    tt_num = edupage("ttviewer.js?__func=getTTViewerData", [None, aasta])["regular"]["default_num"]
    tabelid = edupage("regulartt.js?__func=regularttGetData", [None, tt_num])["dbiAccessorRes"]["tables"]
    T = {t["id"]: {r["id"]: r for r in t.get("data_rows", [])} for t in tabelid}
    klass = next(c for c in T["classes"].values() if c["name"] == KLASS)

    # Tunnid ise tulevad kuupäevade kaupa (arvestab tunniplaani muudatustega)
    kaardid = edupage("currenttt.js?__func=curentttGetData", [None, {
        "year": aasta, "datefrom": algus.isoformat(), "dateto": lopp.isoformat(),
        "table": "classes", "id": klass["id"], "showColors": True,
        "showIgroupsInClasses": False, "showOrig": True, "log_module": "CurrentTTView",
    }])["ttitems"]

    paevad = {}
    p = algus
    while p <= lopp:
        if p.weekday() < 5:
            paevad[p.isoformat()] = {"kuupaev": p.isoformat(), "nimi": PAEVAD[p.weekday()], "tunnid": []}
        p += timedelta(days=1)

    for k in kaardid:
        if k.get("type") != "card" or k["date"] not in paevad:
            continue
        aine = T["subjects"].get(k["subjectid"], {"short": "?", "name": "?"})
        lyhend = aine["short"]
        tund_algus, tund_lopp = k["starttime"], k["endtime"]

        # "Uj 12.30-13.15" -> ujumine toimub tegelikult teisel ajal kui tunnikell
        aeg = re.search(r"(\d{1,2})\.(\d{2})-(\d{1,2})\.(\d{2})", lyhend)
        if aeg:
            tund_algus, tund_lopp = f"{int(aeg[1]):02}:{aeg[2]}", f"{int(aeg[3]):02}:{aeg[4]}"
            nimi = "Ujumine"
        else:
            nimi = aine_nimi(lyhend, aine["name"])

        grupp = next((g for g in k.get("groupnames", []) if g), None)
        paevad[k["date"]]["tunnid"].append({
            "tund": int(k["uniperiod"]),
            "pikkus": int(k.get("durationperiods") or 1),
            "algus": tund_algus,
            "lopp": tund_lopp,
            "aine": nimi,
            "lyhend": lyhend,
            "opetajad": [T["teachers"][t]["short"] for t in k["teacherids"] if t in T["teachers"]],
            "ruum": ", ".join(T["classrooms"][r]["short"] for r in k["classroomids"] if r in T["classrooms"]),
            "grupp": grupp.replace("Group", "Grupp") if grupp else None,
        })

    for p in paevad.values():
        p["tunnid"].sort(key=lambda t: (t["algus"], t["grupp"] or ""))

    andmed = {
        "kool": "Haabneeme Kool",
        "klass": KLASS,
        "allikas": f"{KOOL}/timetable/",
        "alates": algus.isoformat(),
        "kuni": lopp.isoformat(),
        "paevad": list(paevad.values()),
    }
    if not any(p["tunnid"] for p in andmed["paevad"]):
        sys.exit("EduPage'ist ei tulnud ühtegi tundi, jätan vanad andmed alles.")

    VALJUND.write_text(
        "// Tunniplaani andmed EduPage'ist. Uueneb automaatselt (GitHub Actions).\n"
        "// Käsitsi uuendamiseks: python3 tools/uuenda_andmed.py\n"
        "window.TUNNIPLAAN = " + json.dumps(andmed, ensure_ascii=False, indent=2) + ";\n",
        encoding="utf-8",
    )
    tunde = sum(len(p["tunnid"]) for p in andmed["paevad"])
    print(f"{KLASS}: {algus}..{lopp}, {tunde} tundi -> {VALJUND}")


if __name__ == "__main__":
    main()
