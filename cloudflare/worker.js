// Cloudflare Worker: loeb Haabneeme Kooli EduPage'ist klassi tunniplaani ja annab selle
// äpile JSON-ina (sama kujuga nagu andmed.js). Brauser ise EduPage'ist lugeda ei saa (CORS)
// ja GitHubi serverid on EduPage'i poolt blokeeritud, seepärast käib lugemine siit.
//
// Kasutamine:  GET https://<worker>.workers.dev/            -> 4B
//              GET https://<worker>.workers.dev/?klass=4A
// Vastus on 15 minutit vahemälus, et EduPage'i mitte koormata.

const KOOL = "https://haabneeme.edupage.org";
const NADALAID = 3; // mitu nädalat ette (jooksev nädal kaasa arvatud)
const VAHEMALU_SEK = 15 * 60;

const PAEVAD = ["Esmaspäev", "Teisipäev", "Kolmapäev", "Neljapäev", "Reede", "Laupäev", "Pühapäev"];

// EduPage'i lühendid -> ainete nimed, mida laps ära tunneb
const AINED = {
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
};

const CORS = { "Access-Control-Allow-Origin": "*" };

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (request.method === "OPTIONS") return new Response(null, { headers: { ...CORS, "Access-Control-Allow-Methods": "GET" } });
    if (url.pathname !== "/") return new Response("Ei leitud", { status: 404, headers: CORS });

    const klass = (url.searchParams.get("klass") || "4B").toUpperCase();
    const vahemaluVoti = new Request(`https://vahemalu/${klass}`);
    const vahemalu = caches.default;
    const vana = await vahemalu.match(vahemaluVoti);
    if (vana) return vana;

    try {
      const andmed = await laeTunniplaan(klass);
      const vastus = new Response(JSON.stringify(andmed), {
        headers: { ...CORS, "Content-Type": "application/json; charset=utf-8", "Cache-Control": `public, max-age=${VAHEMALU_SEK}` },
      });
      ctx.waitUntil(vahemalu.put(vahemaluVoti, vastus.clone()));
      return vastus;
    } catch (viga) {
      return new Response(JSON.stringify({ viga: String(viga.message || viga) }), {
        status: 502, headers: { ...CORS, "Content-Type": "application/json; charset=utf-8" },
      });
    }
  },
};

async function edupage(func, args) {
  const r = await fetch(`${KOOL}/timetable/server/${func}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ __args: args, __gsh: "00000000" }),
    signal: AbortSignal.timeout(15000),
  });
  if (!r.ok) throw new Error(`EduPage vastas ${r.status}`);
  return (await r.json()).r;
}

// Tänane kuupäev Eesti ajas kujul "2026-10-05"
function tanaTallinnas() {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "Europe/Tallinn" }).format(new Date());
}

function lisaPaevi(iso, n) {
  const d = new Date(iso + "T12:00:00Z");
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
}

function nadalapaev(iso) {
  return (new Date(iso + "T12:00:00Z").getUTCDay() + 6) % 7; // 0 = esmaspäev
}

async function laeTunniplaan(klassNimi) {
  const tana = tanaTallinnas();
  const [a, k] = tana.split("-").map(Number);
  const aasta = k >= 8 ? a : a - 1;
  const algus = lisaPaevi(tana, -nadalapaev(tana)); // jooksva nädala esmaspäev
  const lopp = lisaPaevi(algus, NADALAID * 7 - 1);

  // Nimed (ained, õpetajad, ruumid) tulevad kehtivast põhitunniplaanist
  const ttNum = (await edupage("ttviewer.js?__func=getTTViewerData", [null, aasta])).regular.default_num;
  const tabelid = (await edupage("regulartt.js?__func=regularttGetData", [null, ttNum])).dbiAccessorRes.tables;
  const T = {};
  for (const t of tabelid) T[t.id] = Object.fromEntries((t.data_rows || []).map((r) => [r.id, r]));
  const klass = Object.values(T.classes).find((c) => c.name === klassNimi);
  if (!klass) throw new Error(`Klassi ${klassNimi} ei leitud`);

  // Tunnid ise tulevad kuupäevade kaupa (arvestab tunniplaani muudatustega)
  const kaardid = (await edupage("currenttt.js?__func=curentttGetData", [null, {
    year: aasta, datefrom: algus, dateto: lopp, table: "classes", id: klass.id, showColors: true,
    showIgroupsInClasses: false, showOrig: true, log_module: "CurrentTTView",
  }])).ttitems;

  const andmed = teisenda(T, kaardid, klassNimi, algus, lopp);
  if (!andmed.paevad.some((p) => p.tunnid.length)) throw new Error("EduPage'ist ei tulnud ühtegi tundi");
  return andmed;
}

function aineNimi(lyhend, taisnimi) {
  const alus = lyhend.replace(/ [LP]$/, "");
  return AINED[lyhend] || AINED[alus] || taisnimi.replace(/ [LP]$/, "");
}

// Teeb EduPage'i andmetest sama kujuga objekti nagu tools/uuenda_andmed.py (andmed.js)
export function teisenda(T, kaardid, klassNimi, algus, lopp) {
  const paevad = {};
  for (let p = algus; p <= lopp; p = lisaPaevi(p, 1)) {
    if (nadalapaev(p) < 5) paevad[p] = { kuupaev: p, nimi: PAEVAD[nadalapaev(p)], tunnid: [] };
  }

  for (const k of kaardid) {
    if (k.type !== "card" || !paevad[k.date]) continue;
    const aine = T.subjects[k.subjectid] || { short: "?", name: "?" };
    const lyhend = aine.short;
    let tundAlgus = k.starttime, tundLopp = k.endtime, nimi;

    // "Uj 12.30-13.15" -> ujumine toimub tegelikult teisel ajal kui tunnikell
    const aeg = lyhend.match(/(\d{1,2})\.(\d{2})-(\d{1,2})\.(\d{2})/);
    if (aeg) {
      tundAlgus = `${aeg[1].padStart(2, "0")}:${aeg[2]}`;
      tundLopp = `${aeg[3].padStart(2, "0")}:${aeg[4]}`;
      nimi = "Ujumine";
    } else {
      nimi = aineNimi(lyhend, aine.name);
    }

    const grupp = (k.groupnames || []).find((g) => g) || null;
    paevad[k.date].tunnid.push({
      tund: Number(k.uniperiod),
      pikkus: Number(k.durationperiods || 1),
      algus: tundAlgus,
      lopp: tundLopp,
      aine: nimi,
      lyhend,
      opetajad: k.teacherids.filter((t) => T.teachers[t]).map((t) => T.teachers[t].short),
      ruum: k.classroomids.filter((r) => T.classrooms[r]).map((r) => T.classrooms[r].short).join(", "),
      grupp: grupp ? grupp.replace("Group", "Grupp") : null,
    });
  }

  for (const p of Object.values(paevad)) {
    p.tunnid.sort((x, y) => x.algus.localeCompare(y.algus) || (x.grupp || "").localeCompare(y.grupp || ""));
  }

  return {
    kool: "Haabneeme Kool",
    klass: klassNimi,
    allikas: `${KOOL}/timetable/`,
    alates: algus,
    kuni: lopp,
    paevad: Object.values(paevad),
  };
}
