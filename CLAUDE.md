# 4B tunniplaan

Ehitame seda äppi **otse klassi ees koos 4B klassi lastega** (10-aastased, 20 last). Kõik, mida kirjutad, on suurel ekraanil näha.

## Kuidas lastega suhelda
- Kirjuta **lühidalt ja lihtsas eesti keeles**, nii et 10-aastane saab aru. Ära kasuta žargooni; kui pead, seleta ühe lausega.
- Enne tööd ütle ühe lausega, mida teed. Pärast tööd ütle ühe-kahe lausega, mis muutus ja kuhu vaadata.
- Tee **väikseid ja kiireid samme**. Iga muudatus peab valmima umbes minutiga. Ära lisa asju, mida ei küsitud.
- Ära küsi üleliigseid täpsustusi: vali mõistlik variant ja ütle, mille valisid.

## Tehnika (ära muuda ilma küsimata)
- Kogu äpp on **üks fail `index.html`** (HTML + CSS + JavaScript ühes failis). Ei mingit build'i, npm'i ega väliseid teeke.
- Andmed on failis `andmed.js` (`window.TUNNIPLAAN`), mida laeb `<script src="andmed.js">`. **Ära muuda seda faili käsitsi.** Uuendamiseks: `python3 tools/uuenda_andmed.py` (laeb EduPage'ist värsked andmed).
- `andmed.js` on **kuupäevapõhine**: `paevad[]` = kõik tööpäevad vahemikus `alates`..`kuni` (jooksev nädal + 2 järgmist). Igal päeval on `kuupaev` (`"2026-10-05"`), `nimi` (`"Esmaspäev"`) ja `tunnid[]` väljadega `tund, pikkus, algus, lopp, aine, lyhend, opetajad[], ruum, grupp`. Päeva leia **kuupäeva järgi**, mitte nädalapäeva järgi.
- Kui `grupp` on `"Grupp 1"`/`"Grupp 2"`, käib tund pool klassi kaupa ja samal ajal on teine tund teisele grupile. Näita neid kõrvuti/koos, mitte eraldi tundidena.
- Ära kustuta faili `CNAME` ega kausta `.github`.
- Äpp peab töötama eelkõige **telefonis** (kitsas ekraan, suur kiri, vajutatav pöidlaga).

## Mis päeva näidata (põhireegel)
- Kasuta Eesti aega (`Europe/Tallinn`).
- Näita **tänast** päeva, kuni **1 tund pärast tänase viimase tunni lõppu**.
- Pärast seda näita **järgmise koolipäeva** tunniplaani = järgmine kuupäev andmetes, millel on tunde. (Reede õhtul, laupäeval ja pühapäeval on see tavaliselt esmaspäev.)
- Kui sobivat päeva andmetes ei ole (andmed on vanad), näita sõbralikku teadet ja linki kooli tunniplaanile (`allikas`). Ära kunagi näita vale päeva tunde.
- **Päeva nimi** (nt "Esmaspäev" ja kuupäev) peab olema suur ja selgelt näha.
- Kui näidatakse järgmist päeva, siis peab üleval olema **selgelt nähtav teade** (nt "Tänased tunnid on läbi! Näitan homset.").
- Testimiseks: URL-i parameeter `?aeg=2026-10-09T17:00` paneb äpi arvama, et kell on just see. See peab alati töötama, sest näitame seda lastele.

## Avaldamine
- Kood läheb veebi `git push`-iga harusse `main` → GitHub Actions „Avalda“ → https://tunniplaan.orkestraator.ee (umbes 1 minut).
- **Enne push'i tee alati `git pull --rebase`**, sest andmed võivad vahepeal uuenenud olla.
- Commit'i sõnum kirjuta eesti keeles ja lühidalt (nt "Lisasime ainete emojid").
- Kohalikuks vaatamiseks: `python3 -m http.server 8000` ja ava http://localhost:8000
