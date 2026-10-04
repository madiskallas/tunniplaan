// Cloudflare Pages'i funktsioon: https://tunniplaan.orkestraator.ee/api/tunniplaan
// Kogu loogika on failis cloudflare/worker.js
import { vasta } from "../../cloudflare/worker.js";

export const onRequest = (context) => vasta(context.request, context);
