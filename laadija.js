// Laeb tunniplaani andmed.
// 1) Proovib värskeid andmeid aadressilt /api/tunniplaan (loeb otse kooli EduPage'ist, vt cloudflare/worker.js).
// 2) Kui see ei õnnesta (internet, Worker maas), kasutab repo koopiat failist andmed.js.
//
// Kasutamine:  const andmed = await laeTunniplaan();
//              andmed.varske === true, kui andmed tulid otse EduPage'ist

const VARSKE_ANDMED_URL = "/api/tunniplaan"; // Cloudflare Pages'i funktsioon (functions/api/tunniplaan.js)

async function laeTunniplaan() {
  if (VARSKE_ANDMED_URL) {
    try {
      const vastus = await fetch(VARSKE_ANDMED_URL, { signal: AbortSignal.timeout(5000) });
      if (vastus.ok) {
        const andmed = await vastus.json();
        if (andmed.paevad && andmed.paevad.some((p) => p.tunnid.length)) return { ...andmed, varske: true };
      }
    } catch (e) {
      console.warn("Värskeid andmeid ei saanud, kasutan koopiat:", e);
    }
  }
  return { ...window.TUNNIPLAAN, varske: false };
}
