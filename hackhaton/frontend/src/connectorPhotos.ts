/**
 * Central connector photo / product-page URL registry.
 *
 * Keyed by manufacturer part number (exactly as stored in harness_db.json).
 * URL patterns per manufacturer:
 *   Molex      — molex.com/en-us/products/part-detail/{PN_no_dashes}
 *   TE         — te.com/en/product-{PN}.html
 *   KET        — ketconn.com/en/product/?keyword={PN}
 *   Hirose     — hirose.com/en/product/search?type=number&keyword={PN}
 *   Mouser     — mouser.com/Search/Refine?Keyword={PN}  (fallback for uncommon mfrs)
 *
 * Add entries here whenever a new PN is confirmed. Call `photoUrlForPN(pn)`
 * to get the link, or `null` if none is registered.
 */

const MOLEX = (pn: string) =>
  `https://www.molex.com/en-us/products/part-detail/${pn.replace(/-/g, "")}`;

const TE = (pn: string) =>
  `https://www.te.com/en/product-${pn}.html`;

const KET = (pn: string) =>
  `https://www.ketconn.com/en/product/?keyword=${encodeURIComponent(pn)}`;

const HIROSE = (pn: string) =>
  `https://www.hirose.com/en/product/search?type=number&keyword=${encodeURIComponent(pn)}`;

const MOUSER = (pn: string) =>
  `https://www.mouser.com/Search/Refine?Keyword=${encodeURIComponent(pn)}`;

/** PN → { label, url } */
const REGISTRY: Record<string, { label: string; url: string }> = {
  // ── Molex ────────────────────────────────────────────────────────────────
  "19418-0029":   { label: "Molex 19418-0029",   url: MOLEX("19418-0029") },
  "19419-0020":   { label: "Molex 19419-0020",   url: MOLEX("19419-0020") },
  "43025-1200":   { label: "Molex 43025-1200",   url: MOLEX("43025-1200") },
  "469921210":    { label: "Molex 469921210",     url: MOLEX("469921210") },
  "355070800":    { label: "Molex 355070800",     url: MOLEX("355070800") },
  "355071100":    { label: "Molex 355071100",     url: MOLEX("355071100") },
  "347910041":    { label: "Molex 347910041",     url: MOLEX("347910041") },
  "46993-0410":   { label: "Molex 46993-0410",   url: MOLEX("46993-0410") },
  "504693-0604":  { label: "Molex 504693-0604",  url: MOLEX("504693-0604") },
  "504693-0403":  { label: "Molex 504693-0403",  url: MOLEX("504693-0403") },
  // ── TE Connectivity ──────────────────────────────────────────────────────
  "2005076-1":    { label: "TE 2005076-1",       url: TE("2005076-1") },
  "2005079-1":    { label: "TE 2005079-1",       url: TE("2005079-1") },
  "1473410-1":    { label: "TE 1473410-1",       url: TE("1473410-1") },
  "1318386-1":    { label: "TE 1318386-1",       url: TE("1318386-1") },
  // ── KET ──────────────────────────────────────────────────────────────────
  "MG610376-4":   { label: "KET MG610376-4",     url: KET("MG610376-4") },
  "MG654102":     { label: "KET MG654102",       url: KET("MG654102") },
  "MG644152":     { label: "KET MG644152",       url: KET("MG644152") },
  "MG651747-5":   { label: "KET MG651747-5",     url: KET("MG651747-5") },
  "MG641744-5":   { label: "KET MG641744-5",     url: KET("MG641744-5") },
  // ── Hirose ───────────────────────────────────────────────────────────────
  "CL6424-0076-05": { label: "Hirose CL6424-0076-05", url: HIROSE("CL6424-0076-05") },
  // ── Youye (via Mouser search — no direct product pages in English) ────────
  "YY8401064":    { label: "Youye YY8401064",    url: MOUSER("YY8401064") },
  "YY940107K":    { label: "Youye YY940107K",    url: MOUSER("YY940107K") },
  "YY920812":     { label: "Youye YY920812",     url: MOUSER("YY920812") },
  // ── Anderson Power ───────────────────────────────────────────────────────
  "6319G1":       { label: "Anderson Power 6319G1", url: MOUSER("Anderson 6319G1") },
  // ── Panduit ──────────────────────────────────────────────────────────────
  "LCMA6-6-C":    { label: "Panduit LCMA6-6-C",  url: MOUSER("Panduit LCMA6-6-C") },
  // ── Phoenix Contact ──────────────────────────────────────────────────────
  "3240096":      { label: "Phoenix Contact 3240096", url: MOUSER("Phoenix Contact 3240096") },
  // ── Amphenol ─────────────────────────────────────────────────────────────
  "RL00571-16BK": { label: "Amphenol RL00571-16BK", url: MOUSER("Amphenol RL00571-16BK") },
};

/** Returns { label, url } for a given PN, or null if not in registry. */
export function photoForPN(pn: string): { label: string; url: string } | null {
  return REGISTRY[pn] ?? null;
}

/** Convenience: build ConnectorPhoto[] from a list of PNs. Skips unknown PNs. */
export function photosForPNs(pns: string[]): { label: string; url: string }[] {
  return pns.flatMap((pn) => {
    const entry = REGISTRY[pn];
    return entry ? [entry] : [];
  });
}
