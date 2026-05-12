/**
 * Static SVG connector pinout diagrams.
 * Pin data from: VS050100 v4.5, VS101500 v4.2.
 * No PNs for VIH_2_REEBOX_F or Reebox_Main_F connectors — omitted per policy.
 */

export const APP_CAN_PATH_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 342 96" role="img" aria-label="APP CAN signal path">
  <rect width="342" height="96" rx="6" fill="#0f172a" stroke="#1e293b" stroke-width="1.5"/>
  <text x="171" y="14" text-anchor="middle" fill="#64748b" font-size="9" font-family="ui-monospace,Menlo,monospace" font-weight="600">APP CAN — Signal Path</text>
  <rect x="4" y="22" width="78" height="32" rx="4" fill="#1e293b" stroke="#334155" stroke-width="1"/>
  <text x="43" y="35" text-anchor="middle" fill="#94a3b8" font-size="8.5" font-family="ui-monospace,Menlo,monospace" font-weight="600">REECU X8</text>
  <text x="43" y="47" text-anchor="middle" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">CREECU_1</text>
  <line x1="82" y1="35" x2="106" y2="35" stroke="#eab308" stroke-width="1.5"/>
  <line x1="82" y1="43" x2="106" y2="43" stroke="#9ca3af" stroke-width="1.5"/>
  <circle cx="110" cy="35" r="4" fill="#eab308" stroke="#92400e" stroke-width="1"/>
  <circle cx="110" cy="43" r="4" fill="#6b7280" stroke="#374151" stroke-width="1"/>
  <text x="110" y="56" text-anchor="middle" fill="#334155" font-size="7" font-family="ui-monospace,Menlo,monospace">splice</text>
  <line x1="114" y1="35" x2="134" y2="35" stroke="#eab308" stroke-width="1.5"/>
  <line x1="114" y1="43" x2="134" y2="43" stroke="#9ca3af" stroke-width="1.5"/>
  <rect x="134" y="22" width="94" height="32" rx="4" fill="#1e293b" stroke="#334155" stroke-width="1"/>
  <text x="181" y="35" text-anchor="middle" fill="#94a3b8" font-size="8" font-family="ui-monospace,Menlo,monospace" font-weight="600">VIH_2_REEBOX_F</text>
  <text x="181" y="47" text-anchor="middle" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">pin 1 (H) · pin 2 (L)</text>
  <line x1="228" y1="35" x2="258" y2="35" stroke="#eab308" stroke-width="1.5"/>
  <line x1="228" y1="43" x2="258" y2="43" stroke="#9ca3af" stroke-width="1.5"/>
  <rect x="258" y="22" width="80" height="32" rx="4" fill="#1e293b" stroke="#334155" stroke-width="1"/>
  <text x="298" y="35" text-anchor="middle" fill="#94a3b8" font-size="8" font-family="ui-monospace,Menlo,monospace" font-weight="600">Reebox_Main_F</text>
  <text x="298" y="47" text-anchor="middle" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">pin 1 (H) · pin 2 (L)</text>
  <rect x="10" y="70" width="10" height="6" rx="1" fill="#eab308"/>
  <text x="24" y="77" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">CAN H (Yellow)</text>
  <rect x="120" y="70" width="10" height="6" rx="1" fill="#9ca3af"/>
  <text x="134" y="77" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">CAN L (Gray)</text>
  <circle cx="12" cy="88" r="4" fill="#eab308" stroke="#92400e" stroke-width="1"/>
  <text x="20" y="92" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">splice junction (APP_HIGH/LOW_CAN_S)</text>
</svg>`;

export const VIH_2_REEBOX_F_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 280 186" role="img" aria-label="VIH_2_REEBOX_F connector pinout">
  <rect width="280" height="186" rx="6" fill="#0f172a" stroke="#1e293b" stroke-width="1.5"/>
  <text x="140" y="17" text-anchor="middle" fill="#94a3b8" font-size="11" font-family="ui-monospace,Menlo,monospace" font-weight="600">VIH_2_REEBOX_F · 16-pin &#x2640;</text>
  <text x="140" y="30" text-anchor="middle" fill="#475569" font-size="9" font-family="ui-monospace,Menlo,monospace">Molex 19418-0029 · VS050100 Accessory Harness v4.5</text>
  <text x="140" y="42" text-anchor="middle" fill="#334155" font-size="8" font-family="ui-monospace,Menlo,monospace" font-style="italic">wired pins only &#x2014; 3 of 16 shown</text>
  <rect x="8" y="50" width="264" height="130" rx="4" fill="#0a1628" stroke="#1e3a5f" stroke-width="1"/>
  <rect x="10" y="53" width="260" height="34" rx="3" fill="#451a03" stroke="#92400e" stroke-width="0.5" opacity="0.5"/>
  <circle cx="28" cy="70" r="9" fill="#451a03" stroke="#f59e0b" stroke-width="1.5"/>
  <text x="28" y="70" text-anchor="middle" dominant-baseline="central" fill="#fbbf24" font-size="9" font-family="ui-monospace,Menlo,monospace" font-weight="700">1</text>
  <text x="44" y="65" fill="#fde68a" font-size="10" font-family="ui-monospace,Menlo,monospace" font-weight="600">APP_CAN_H</text>
  <text x="44" y="77" fill="#d97706" font-size="8" font-family="ui-monospace,Menlo,monospace">APP High · splice APP_HIGH_CAN_S</text>
  <rect x="244" y="63" width="22" height="14" rx="2" fill="#eab308"/>
  <text x="255" y="70" text-anchor="middle" dominant-baseline="central" fill="#0f172a" font-size="7" font-family="ui-monospace,Menlo,monospace" font-weight="700">YLW</text>
  <rect x="10" y="89" width="260" height="34" rx="3" fill="#1a1f2e" stroke="#334155" stroke-width="0.5" opacity="0.5"/>
  <circle cx="28" cy="106" r="9" fill="#1a1f2e" stroke="#94a3b8" stroke-width="1.5"/>
  <text x="28" y="106" text-anchor="middle" dominant-baseline="central" fill="#e2e8f0" font-size="9" font-family="ui-monospace,Menlo,monospace" font-weight="700">2</text>
  <text x="44" y="101" fill="#e2e8f0" font-size="10" font-family="ui-monospace,Menlo,monospace" font-weight="600">APP_CAN_L</text>
  <text x="44" y="113" fill="#94a3b8" font-size="8" font-family="ui-monospace,Menlo,monospace">APP Low · splice APP_LOW_CAN_S</text>
  <rect x="244" y="99" width="22" height="14" rx="2" fill="#6b7280"/>
  <text x="255" y="106" text-anchor="middle" dominant-baseline="central" fill="#f8fafc" font-size="7" font-family="ui-monospace,Menlo,monospace" font-weight="700">GRY</text>
  <line x1="20" y1="128" x2="260" y2="128" stroke="#1e3a5f" stroke-width="0.5" stroke-dasharray="3,3"/>
  <text x="140" y="136" text-anchor="middle" fill="#334155" font-size="7.5" font-family="ui-monospace,Menlo,monospace">pins 3&#x2013;14 not wired to this signal</text>
  <circle cx="28" cy="158" r="9" fill="#1e293b" stroke="#334155" stroke-width="1"/>
  <text x="28" y="158" text-anchor="middle" dominant-baseline="central" fill="#64748b" font-size="8" font-family="ui-monospace,Menlo,monospace" font-weight="700">15</text>
  <text x="44" y="153" fill="#94a3b8" font-size="10" font-family="ui-monospace,Menlo,monospace">GND</text>
  <text x="44" y="165" fill="#475569" font-size="8" font-family="ui-monospace,Menlo,monospace">Ground · splice S_GND_SPLICE</text>
  <rect x="244" y="151" width="22" height="14" rx="2" fill="#374151"/>
  <text x="255" y="158" text-anchor="middle" dominant-baseline="central" fill="#9ca3af" font-size="7" font-family="ui-monospace,Menlo,monospace" font-weight="700">BLK</text>
</svg>`;

export const REEBOX_MAIN_F_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 224" role="img" aria-label="Reebox_Main_F 8-pin connector pinout">
  <rect width="320" height="224" rx="6" fill="#0f172a" stroke="#1e293b" stroke-width="1.5"/>
  <text x="160" y="18" text-anchor="middle" fill="#94a3b8" font-size="11" font-family="ui-monospace,Menlo,monospace" font-weight="600">Reebox_Main_F · 8-pin &#x2640;</text>
  <text x="160" y="32" text-anchor="middle" fill="#475569" font-size="9" font-family="ui-monospace,Menlo,monospace">VS101500 Accessory Harness v4.2</text>
  <rect x="8" y="42" width="304" height="178" rx="4" fill="#0a1628" stroke="#1e3a5f" stroke-width="1"/>
  <line x1="160" y1="46" x2="160" y2="216" stroke="#1e3a5f" stroke-width="1"/>
  <rect x="10" y="46" width="148" height="40" rx="3" fill="#451a03" stroke="#92400e" stroke-width="0.5" opacity="0.45"/>
  <circle cx="28" cy="67" r="9" fill="#451a03" stroke="#f59e0b" stroke-width="1.5"/>
  <text x="28" y="67" text-anchor="middle" dominant-baseline="central" fill="#fbbf24" font-size="9" font-family="ui-monospace,Menlo,monospace" font-weight="700">1</text>
  <text x="44" y="62" fill="#fde68a" font-size="10" font-family="ui-monospace,Menlo,monospace" font-weight="600">APP_CAN_H</text>
  <text x="44" y="75" fill="#d97706" font-size="8" font-family="ui-monospace,Menlo,monospace">APP High</text>
  <rect x="142" y="60" width="14" height="14" rx="2" fill="#eab308"/>
  <text x="149" y="67" text-anchor="middle" dominant-baseline="central" fill="#0f172a" font-size="7" font-family="ui-monospace,Menlo,monospace" font-weight="700">H</text>
  <rect x="164" y="60" width="14" height="14" rx="2" fill="#94a3b8"/>
  <text x="171" y="67" text-anchor="middle" dominant-baseline="central" fill="#0f172a" font-size="7" font-family="ui-monospace,Menlo,monospace" font-weight="700">L</text>
  <text x="276" y="62" text-anchor="end" fill="#e2e8f0" font-size="10" font-family="ui-monospace,Menlo,monospace" font-weight="600">APP_CAN_L</text>
  <text x="276" y="75" text-anchor="end" fill="#94a3b8" font-size="8" font-family="ui-monospace,Menlo,monospace">APP Low</text>
  <circle cx="292" cy="67" r="9" fill="#1e293b" stroke="#94a3b8" stroke-width="1"/>
  <text x="292" y="67" text-anchor="middle" dominant-baseline="central" fill="#94a3b8" font-size="9" font-family="ui-monospace,Menlo,monospace" font-weight="700">2</text>
  <rect x="10" y="88" width="148" height="40" rx="3" fill="#052e16" stroke="#166534" stroke-width="0.5" opacity="0.45"/>
  <circle cx="28" cy="109" r="9" fill="#052e16" stroke="#22c55e" stroke-width="1.5"/>
  <text x="28" y="109" text-anchor="middle" dominant-baseline="central" fill="#86efac" font-size="9" font-family="ui-monospace,Menlo,monospace" font-weight="700">3</text>
  <text x="44" y="104" fill="#4ade80" font-size="10" font-family="ui-monospace,Menlo,monospace" font-weight="600">XCP_CAN_H</text>
  <text x="44" y="117" fill="#16a34a" font-size="8" font-family="ui-monospace,Menlo,monospace">XCP High</text>
  <rect x="142" y="102" width="14" height="14" rx="2" fill="#22c55e"/>
  <text x="149" y="109" text-anchor="middle" dominant-baseline="central" fill="#0f172a" font-size="7" font-family="ui-monospace,Menlo,monospace" font-weight="700">H</text>
  <rect x="164" y="102" width="14" height="14" rx="2" fill="#94a3b8"/>
  <text x="171" y="109" text-anchor="middle" dominant-baseline="central" fill="#0f172a" font-size="7" font-family="ui-monospace,Menlo,monospace" font-weight="700">L</text>
  <text x="276" y="104" text-anchor="end" fill="#94a3b8" font-size="10" font-family="ui-monospace,Menlo,monospace">XCP_CAN_L</text>
  <text x="276" y="117" text-anchor="end" fill="#475569" font-size="8" font-family="ui-monospace,Menlo,monospace">XCP Low</text>
  <circle cx="292" cy="109" r="9" fill="#1e293b" stroke="#6b7280" stroke-width="1.5"/>
  <text x="292" y="109" text-anchor="middle" dominant-baseline="central" fill="#9ca3af" font-size="9" font-family="ui-monospace,Menlo,monospace" font-weight="700">4</text>
  <rect x="162" y="130" width="148" height="40" rx="3" fill="#0a1040" stroke="#1e40af" stroke-width="0.5" opacity="0.45"/>
  <circle cx="28" cy="151" r="9" fill="#1e293b" stroke="#9ca3af" stroke-width="1.5"/>
  <text x="28" y="151" text-anchor="middle" dominant-baseline="central" fill="#94a3b8" font-size="9" font-family="ui-monospace,Menlo,monospace" font-weight="700">5</text>
  <text x="44" y="146" fill="#94a3b8" font-size="10" font-family="ui-monospace,Menlo,monospace">SCI_CAN_H</text>
  <text x="44" y="159" fill="#475569" font-size="8" font-family="ui-monospace,Menlo,monospace">SCI High</text>
  <rect x="142" y="144" width="14" height="14" rx="2" fill="#9ca3af"/>
  <text x="149" y="151" text-anchor="middle" dominant-baseline="central" fill="#0f172a" font-size="7" font-family="ui-monospace,Menlo,monospace" font-weight="700">H</text>
  <rect x="164" y="144" width="14" height="14" rx="2" fill="#3b82f6"/>
  <text x="171" y="151" text-anchor="middle" dominant-baseline="central" fill="#f8fafc" font-size="7" font-family="ui-monospace,Menlo,monospace" font-weight="700">L</text>
  <text x="276" y="146" text-anchor="end" fill="#60a5fa" font-size="10" font-family="ui-monospace,Menlo,monospace" font-weight="600">SCI_CAN_L</text>
  <text x="276" y="159" text-anchor="end" fill="#3b82f6" font-size="8" font-family="ui-monospace,Menlo,monospace">SCI Low</text>
  <circle cx="292" cy="151" r="9" fill="#0a1040" stroke="#3b82f6" stroke-width="1.5"/>
  <text x="292" y="151" text-anchor="middle" dominant-baseline="central" fill="#93c5fd" font-size="9" font-family="ui-monospace,Menlo,monospace" font-weight="700">6</text>
  <circle cx="28" cy="193" r="9" fill="#1e293b" stroke="#334155" stroke-width="1"/>
  <text x="28" y="193" text-anchor="middle" dominant-baseline="central" fill="#64748b" font-size="9" font-family="ui-monospace,Menlo,monospace" font-weight="700">7</text>
  <text x="44" y="188" fill="#94a3b8" font-size="10" font-family="ui-monospace,Menlo,monospace">WAKE</text>
  <text x="44" y="201" fill="#475569" font-size="8" font-family="ui-monospace,Menlo,monospace">Wake signal</text>
  <rect x="142" y="186" width="14" height="14" rx="2" fill="#eab308"/>
  <rect x="164" y="186" width="14" height="14" rx="2" fill="#ef4444"/>
  <text x="276" y="188" text-anchor="end" fill="#94a3b8" font-size="10" font-family="ui-monospace,Menlo,monospace">K15</text>
  <text x="276" y="201" text-anchor="end" fill="#475569" font-size="8" font-family="ui-monospace,Menlo,monospace">Ignition</text>
  <circle cx="292" cy="193" r="9" fill="#1e293b" stroke="#334155" stroke-width="1"/>
  <text x="292" y="193" text-anchor="middle" dominant-baseline="central" fill="#64748b" font-size="9" font-family="ui-monospace,Menlo,monospace" font-weight="700">8</text>
</svg>`;

export const WAKE_PATH_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 342 96" role="img" aria-label="WAKE (KL15) signal path">
  <rect width="342" height="96" rx="6" fill="#0f172a" stroke="#1e293b" stroke-width="1.5"/>
  <text x="171" y="14" text-anchor="middle" fill="#64748b" font-size="9" font-family="ui-monospace,Menlo,monospace" font-weight="600">WAKE (KL15) — Signal Path</text>
  <rect x="4" y="22" width="76" height="32" rx="4" fill="#1e293b" stroke="#334155" stroke-width="1"/>
  <text x="42" y="35" text-anchor="middle" fill="#94a3b8" font-size="8.5" font-family="ui-monospace,Menlo,monospace" font-weight="600">KL15 / FMC130</text>
  <text x="42" y="47" text-anchor="middle" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">APCB board</text>
  <line x1="80" y1="38" x2="92" y2="38" stroke="#f97316" stroke-width="2"/>
  <circle cx="96" cy="38" r="4" fill="#f97316" stroke="#c2410c" stroke-width="1"/>
  <text x="96" y="56" text-anchor="middle" fill="#334155" font-size="6.5" font-family="ui-monospace,Menlo,monospace">S12</text>
  <line x1="100" y1="38" x2="112" y2="38" stroke="#f97316" stroke-width="2"/>
  <rect x="112" y="22" width="92" height="32" rx="4" fill="#1e293b" stroke="#334155" stroke-width="1"/>
  <text x="158" y="35" text-anchor="middle" fill="#94a3b8" font-size="8" font-family="ui-monospace,Menlo,monospace" font-weight="600">APCB_2_VIH</text>
  <text x="158" y="47" text-anchor="middle" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">pin 4 (Orange)</text>
  <line x1="204" y1="38" x2="216" y2="38" stroke="#f97316" stroke-width="2"/>
  <circle cx="220" cy="38" r="4" fill="#f97316" stroke="#c2410c" stroke-width="1"/>
  <text x="220" y="56" text-anchor="middle" fill="#334155" font-size="6.5" font-family="ui-monospace,Menlo,monospace">WAKE_S</text>
  <line x1="224" y1="38" x2="238" y2="38" stroke="#f97316" stroke-width="2"/>
  <rect x="238" y="22" width="100" height="32" rx="4" fill="#1e293b" stroke="#334155" stroke-width="1"/>
  <text x="288" y="35" text-anchor="middle" fill="#94a3b8" font-size="8.5" font-family="ui-monospace,Menlo,monospace" font-weight="600">REECU X8 / X9</text>
  <text x="288" y="47" text-anchor="middle" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">CREECU_1 pins 11 &amp; 38</text>
  <rect x="10" y="70" width="10" height="6" rx="1" fill="#f97316"/>
  <text x="24" y="77" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">WAKE / KL15 (Orange — W65, W66)</text>
  <circle cx="12" cy="88" r="4" fill="#f97316" stroke="#c2410c" stroke-width="1"/>
  <text x="20" y="92" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">splice junction (S12 · WAKE_SPLICE in VIH)</text>
</svg>`;

export const APCB_2_VIH_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 280 422" role="img" aria-label="APCB_2_VIH connector pinout">
  <rect width="280" height="422" rx="6" fill="#0f172a" stroke="#1e293b" stroke-width="1.5"/>
  <text x="140" y="17" text-anchor="middle" fill="#94a3b8" font-size="11" font-family="ui-monospace,Menlo,monospace" font-weight="600">APCB_2_VIH · 12-pin &#x2640;</text>
  <text x="140" y="30" text-anchor="middle" fill="#475569" font-size="9" font-family="ui-monospace,Menlo,monospace">Molex 469921210 · VS040804 APCB Harness</text>
  <!-- Pin 1: PWR Main -->
  <rect x="8" y="38" width="264" height="30" rx="3" fill="#1a0505" stroke="#7f1d1d" stroke-width="0.5"/>
  <circle cx="26" cy="53" r="9" fill="#1a0505" stroke="#ef4444" stroke-width="1.5"/>
  <text x="26" y="53" text-anchor="middle" dominant-baseline="central" fill="#fca5a5" font-size="9" font-family="ui-monospace,Menlo,monospace" font-weight="700">1</text>
  <text x="42" y="48" fill="#fca5a5" font-size="10" font-family="ui-monospace,Menlo,monospace" font-weight="600">PWR Main</text>
  <text x="42" y="60" fill="#7f1d1d" font-size="8" font-family="ui-monospace,Menlo,monospace">W9 · 0.5 mm&#xB2;</text>
  <rect x="244" y="46" width="22" height="14" rx="2" fill="#ef4444"/>
  <text x="255" y="53" text-anchor="middle" dominant-baseline="central" fill="#0f172a" font-size="7" font-family="ui-monospace,Menlo,monospace" font-weight="700">RED</text>
  <!-- Pin 2: GND Main -->
  <rect x="8" y="70" width="264" height="30" rx="3" fill="#111827" stroke="#374151" stroke-width="0.5"/>
  <circle cx="26" cy="85" r="9" fill="#111827" stroke="#6b7280" stroke-width="1.5"/>
  <text x="26" y="85" text-anchor="middle" dominant-baseline="central" fill="#9ca3af" font-size="9" font-family="ui-monospace,Menlo,monospace" font-weight="700">2</text>
  <text x="42" y="80" fill="#9ca3af" font-size="10" font-family="ui-monospace,Menlo,monospace" font-weight="600">GND Main</text>
  <text x="42" y="92" fill="#4b5563" font-size="8" font-family="ui-monospace,Menlo,monospace">W12 · 0.5 mm&#xB2;</text>
  <rect x="244" y="78" width="22" height="14" rx="2" fill="#374151"/>
  <text x="255" y="85" text-anchor="middle" dominant-baseline="central" fill="#9ca3af" font-size="7" font-family="ui-monospace,Menlo,monospace" font-weight="700">BLK</text>
  <!-- Pin 3: Wire Data -->
  <rect x="8" y="102" width="264" height="30" rx="3" fill="#0f172a" stroke="#334155" stroke-width="0.5"/>
  <circle cx="26" cy="117" r="9" fill="#0f172a" stroke="#64748b" stroke-width="1.5"/>
  <text x="26" y="117" text-anchor="middle" dominant-baseline="central" fill="#94a3b8" font-size="9" font-family="ui-monospace,Menlo,monospace" font-weight="700">3</text>
  <text x="42" y="112" fill="#94a3b8" font-size="10" font-family="ui-monospace,Menlo,monospace" font-weight="600">Wire Data</text>
  <text x="42" y="124" fill="#475569" font-size="8" font-family="ui-monospace,Menlo,monospace">&#x2192; FMC130 pin 2</text>
  <rect x="244" y="110" width="22" height="14" rx="2" fill="#475569"/>
  <text x="255" y="117" text-anchor="middle" dominant-baseline="central" fill="#e2e8f0" font-size="7" font-family="ui-monospace,Menlo,monospace" font-weight="700">SLT</text>
  <!-- Pin 4: REECU WAKE (highlighted) -->
  <rect x="8" y="134" width="264" height="30" rx="3" fill="#431407" stroke="#ea580c" stroke-width="1.2"/>
  <circle cx="26" cy="149" r="9" fill="#431407" stroke="#f97316" stroke-width="1.5"/>
  <text x="26" y="149" text-anchor="middle" dominant-baseline="central" fill="#fb923c" font-size="9" font-family="ui-monospace,Menlo,monospace" font-weight="700">4</text>
  <text x="42" y="144" fill="#fed7aa" font-size="10" font-family="ui-monospace,Menlo,monospace" font-weight="700">REECU WAKE &#x2605;</text>
  <text x="42" y="156" fill="#ea580c" font-size="8" font-family="ui-monospace,Menlo,monospace">W66 · &#x2192; S12 splice · KL15</text>
  <rect x="244" y="142" width="22" height="14" rx="2" fill="#f97316"/>
  <text x="255" y="149" text-anchor="middle" dominant-baseline="central" fill="#0f172a" font-size="7" font-family="ui-monospace,Menlo,monospace" font-weight="700">ORG</text>
  <!-- Pin 5: IPDU WAKE -->
  <rect x="8" y="166" width="264" height="30" rx="3" fill="#0a1a2e" stroke="#1e3a5f" stroke-width="0.5"/>
  <circle cx="26" cy="181" r="9" fill="#0f2744" stroke="#3b82f6" stroke-width="1.5"/>
  <text x="26" y="181" text-anchor="middle" dominant-baseline="central" fill="#93c5fd" font-size="9" font-family="ui-monospace,Menlo,monospace" font-weight="700">5</text>
  <text x="42" y="176" fill="#93c5fd" font-size="10" font-family="ui-monospace,Menlo,monospace" font-weight="600">IPDU WAKE</text>
  <text x="42" y="188" fill="#1e3a5f" font-size="8" font-family="ui-monospace,Menlo,monospace">W8 · &#x2192; S9 splice</text>
  <rect x="244" y="174" width="22" height="14" rx="2" fill="#3b82f6"/>
  <text x="255" y="181" text-anchor="middle" dominant-baseline="central" fill="#0f172a" font-size="7" font-family="ui-monospace,Menlo,monospace" font-weight="700">BLU</text>
  <!-- Pin 6: Spare Digital Input 1 -->
  <rect x="8" y="198" width="264" height="30" rx="3" fill="#0f172a" stroke="#1e293b" stroke-width="0.5"/>
  <circle cx="26" cy="213" r="9" fill="#0f172a" stroke="#334155" stroke-width="1.5"/>
  <text x="26" y="213" text-anchor="middle" dominant-baseline="central" fill="#64748b" font-size="9" font-family="ui-monospace,Menlo,monospace" font-weight="700">6</text>
  <text x="42" y="208" fill="#64748b" font-size="10" font-family="ui-monospace,Menlo,monospace">Spare DI 1</text>
  <text x="42" y="220" fill="#334155" font-size="8" font-family="ui-monospace,Menlo,monospace">Spare Digital Input</text>
  <rect x="244" y="206" width="22" height="14" rx="2" fill="#1e293b"/>
  <text x="255" y="213" text-anchor="middle" dominant-baseline="central" fill="#475569" font-size="7" font-family="ui-monospace,Menlo,monospace" font-weight="700">SLT</text>
  <!-- Pin 7: Spare Digital Input 2 -->
  <rect x="8" y="230" width="264" height="30" rx="3" fill="#0f172a" stroke="#1e293b" stroke-width="0.5"/>
  <circle cx="26" cy="245" r="9" fill="#0f172a" stroke="#334155" stroke-width="1.5"/>
  <text x="26" y="245" text-anchor="middle" dominant-baseline="central" fill="#64748b" font-size="9" font-family="ui-monospace,Menlo,monospace" font-weight="700">7</text>
  <text x="42" y="240" fill="#64748b" font-size="10" font-family="ui-monospace,Menlo,monospace">Spare DI 2</text>
  <text x="42" y="252" fill="#334155" font-size="8" font-family="ui-monospace,Menlo,monospace">Spare Digital Input</text>
  <rect x="244" y="238" width="22" height="14" rx="2" fill="#1e293b"/>
  <text x="255" y="245" text-anchor="middle" dominant-baseline="central" fill="#475569" font-size="7" font-family="ui-monospace,Menlo,monospace" font-weight="700">SLT</text>
  <!-- Pin 8: Spare -->
  <rect x="8" y="262" width="264" height="30" rx="3" fill="#0f172a" stroke="#1e293b" stroke-width="0.5" opacity="0.7"/>
  <circle cx="26" cy="277" r="9" fill="#0f172a" stroke="#1e293b" stroke-width="1.5"/>
  <text x="26" y="277" text-anchor="middle" dominant-baseline="central" fill="#334155" font-size="9" font-family="ui-monospace,Menlo,monospace" font-weight="700">8</text>
  <text x="42" y="272" fill="#334155" font-size="10" font-family="ui-monospace,Menlo,monospace">Spare</text>
  <text x="42" y="284" fill="#1e293b" font-size="8" font-family="ui-monospace,Menlo,monospace">Not documented</text>
  <rect x="244" y="270" width="22" height="14" rx="2" fill="#0f172a" stroke="#1e293b" stroke-width="1"/>
  <text x="255" y="277" text-anchor="middle" dominant-baseline="central" fill="#334155" font-size="7" font-family="ui-monospace,Menlo,monospace" font-weight="700">—</text>
  <!-- Pin 9: Spare -->
  <rect x="8" y="294" width="264" height="30" rx="3" fill="#0f172a" stroke="#1e293b" stroke-width="0.5" opacity="0.7"/>
  <circle cx="26" cy="309" r="9" fill="#0f172a" stroke="#1e293b" stroke-width="1.5"/>
  <text x="26" y="309" text-anchor="middle" dominant-baseline="central" fill="#334155" font-size="9" font-family="ui-monospace,Menlo,monospace" font-weight="700">9</text>
  <text x="42" y="304" fill="#334155" font-size="10" font-family="ui-monospace,Menlo,monospace">Spare</text>
  <text x="42" y="316" fill="#1e293b" font-size="8" font-family="ui-monospace,Menlo,monospace">Not documented</text>
  <rect x="244" y="302" width="22" height="14" rx="2" fill="#0f172a" stroke="#1e293b" stroke-width="1"/>
  <text x="255" y="309" text-anchor="middle" dominant-baseline="central" fill="#334155" font-size="7" font-family="ui-monospace,Menlo,monospace" font-weight="700">—</text>
  <!-- Pin 10: Wire Data (Green) -->
  <rect x="8" y="326" width="264" height="30" rx="3" fill="#052e16" stroke="#166534" stroke-width="0.5"/>
  <circle cx="26" cy="341" r="9" fill="#052e16" stroke="#22c55e" stroke-width="1.5"/>
  <text x="26" y="341" text-anchor="middle" dominant-baseline="central" fill="#86efac" font-size="9" font-family="ui-monospace,Menlo,monospace" font-weight="700">10</text>
  <text x="42" y="336" fill="#86efac" font-size="10" font-family="ui-monospace,Menlo,monospace" font-weight="600">Wire Data</text>
  <text x="42" y="348" fill="#166534" font-size="8" font-family="ui-monospace,Menlo,monospace">W63 · 0.5 mm&#xB2;</text>
  <rect x="244" y="334" width="22" height="14" rx="2" fill="#22c55e"/>
  <text x="255" y="341" text-anchor="middle" dominant-baseline="central" fill="#052e16" font-size="7" font-family="ui-monospace,Menlo,monospace" font-weight="700">GRN</text>
  <!-- Pin 11: S10 (White) -->
  <rect x="8" y="358" width="264" height="30" rx="3" fill="#111827" stroke="#e2e8f0" stroke-width="0.4"/>
  <circle cx="26" cy="373" r="9" fill="#1e293b" stroke="#e2e8f0" stroke-width="1.5"/>
  <text x="26" y="373" text-anchor="middle" dominant-baseline="central" fill="#f1f5f9" font-size="9" font-family="ui-monospace,Menlo,monospace" font-weight="700">11</text>
  <text x="42" y="368" fill="#f1f5f9" font-size="10" font-family="ui-monospace,Menlo,monospace" font-weight="600">S10</text>
  <text x="42" y="380" fill="#64748b" font-size="8" font-family="ui-monospace,Menlo,monospace">W15 · White</text>
  <rect x="244" y="366" width="22" height="14" rx="2" fill="#f1f5f9"/>
  <text x="255" y="373" text-anchor="middle" dominant-baseline="central" fill="#0f172a" font-size="7" font-family="ui-monospace,Menlo,monospace" font-weight="700">WHT</text>
  <!-- Pin 12: Spare -->
  <rect x="8" y="390" width="264" height="28" rx="3" fill="#0f172a" stroke="#1e293b" stroke-width="0.5" opacity="0.7"/>
  <circle cx="26" cy="404" r="9" fill="#0f172a" stroke="#1e293b" stroke-width="1.5"/>
  <text x="26" y="404" text-anchor="middle" dominant-baseline="central" fill="#334155" font-size="9" font-family="ui-monospace,Menlo,monospace" font-weight="700">12</text>
  <text x="42" y="399" fill="#334155" font-size="10" font-family="ui-monospace,Menlo,monospace">Spare</text>
  <text x="42" y="411" fill="#1e293b" font-size="8" font-family="ui-monospace,Menlo,monospace">Not documented</text>
  <rect x="244" y="397" width="22" height="14" rx="2" fill="#0f172a" stroke="#1e293b" stroke-width="1"/>
  <text x="255" y="404" text-anchor="middle" dominant-baseline="central" fill="#334155" font-size="7" font-family="ui-monospace,Menlo,monospace" font-weight="700">—</text>
</svg>`;

export const TS_APP_CAN_PATH_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 380 96" role="img" aria-label="TS APP CAN signal path">
  <rect width="380" height="96" rx="6" fill="#0f172a" stroke="#1e293b" stroke-width="1.5"/>
  <text x="190" y="14" text-anchor="middle" fill="#64748b" font-size="9" font-family="ui-monospace,Menlo,monospace" font-weight="600">APP CAN — Telestation Signal Path</text>
  <rect x="4" y="22" width="78" height="32" rx="4" fill="#1e293b" stroke="#334155" stroke-width="1"/>
  <text x="43" y="35" text-anchor="middle" fill="#94a3b8" font-size="8.5" font-family="ui-monospace,Menlo,monospace" font-weight="600">REECU X8</text>
  <text x="43" y="47" text-anchor="middle" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">CREECU_X9</text>
  <line x1="82" y1="35" x2="102" y2="35" stroke="#eab308" stroke-width="1.5"/>
  <line x1="82" y1="43" x2="102" y2="43" stroke="#9ca3af" stroke-width="1.5"/>
  <rect x="102" y="22" width="88" height="32" rx="4" fill="#1e293b" stroke="#334155" stroke-width="1"/>
  <text x="146" y="35" text-anchor="middle" fill="#94a3b8" font-size="8" font-family="ui-monospace,Menlo,monospace" font-weight="600">TIH_REECU_F</text>
  <text x="146" y="47" text-anchor="middle" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">Integration harness</text>
  <line x1="190" y1="35" x2="210" y2="35" stroke="#eab308" stroke-width="1.5"/>
  <line x1="190" y1="43" x2="210" y2="43" stroke="#9ca3af" stroke-width="1.5"/>
  <rect x="210" y="22" width="80" height="32" rx="4" fill="#1e293b" stroke="#334155" stroke-width="1"/>
  <text x="250" y="35" text-anchor="middle" fill="#94a3b8" font-size="8" font-family="ui-monospace,Menlo,monospace" font-weight="600">TIH_Main_M</text>
  <text x="250" y="47" text-anchor="middle" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">pin 1 (H) · pin 2 (L)</text>
  <line x1="290" y1="35" x2="310" y2="35" stroke="#eab308" stroke-width="1.5"/>
  <line x1="290" y1="43" x2="310" y2="43" stroke="#9ca3af" stroke-width="1.5"/>
  <rect x="310" y="22" width="66" height="32" rx="4" fill="#1e293b" stroke="#334155" stroke-width="1"/>
  <text x="343" y="35" text-anchor="middle" fill="#94a3b8" font-size="8" font-family="ui-monospace,Menlo,monospace" font-weight="600">TIH_Main_F</text>
  <text x="343" y="47" text-anchor="middle" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">vehicle dock</text>
  <rect x="10" y="70" width="10" height="6" rx="1" fill="#eab308"/>
  <text x="24" y="77" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">CAN H (Yellow)</text>
  <rect x="120" y="70" width="10" height="6" rx="1" fill="#9ca3af"/>
  <text x="134" y="77" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">CAN L (Gray)</text>
</svg>`;

export const XCP_CAN_PATH_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 342 96" role="img" aria-label="XCP CAN signal path">
  <rect width="342" height="96" rx="6" fill="#0f172a" stroke="#1e293b" stroke-width="1.5"/>
  <text x="171" y="14" text-anchor="middle" fill="#64748b" font-size="9" font-family="ui-monospace,Menlo,monospace" font-weight="600">XCP CAN (CAN 1) &#x2014; Signal Path</text>
  <rect x="4" y="22" width="78" height="32" rx="4" fill="#1e293b" stroke="#334155" stroke-width="1"/>
  <text x="43" y="35" text-anchor="middle" fill="#94a3b8" font-size="8.5" font-family="ui-monospace,Menlo,monospace" font-weight="600">REECU X8</text>
  <text x="43" y="47" text-anchor="middle" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">CREECU_1 (CAN 1)</text>
  <line x1="82" y1="35" x2="106" y2="35" stroke="#22c55e" stroke-width="1.5"/>
  <line x1="82" y1="43" x2="106" y2="43" stroke="#9ca3af" stroke-width="1.5"/>
  <circle cx="110" cy="35" r="4" fill="#22c55e" stroke="#166534" stroke-width="1"/>
  <circle cx="110" cy="43" r="4" fill="#6b7280" stroke="#374151" stroke-width="1"/>
  <text x="110" y="56" text-anchor="middle" fill="#334155" font-size="7" font-family="ui-monospace,Menlo,monospace">splice</text>
  <line x1="114" y1="35" x2="134" y2="35" stroke="#22c55e" stroke-width="1.5"/>
  <line x1="114" y1="43" x2="134" y2="43" stroke="#9ca3af" stroke-width="1.5"/>
  <rect x="134" y="22" width="94" height="32" rx="4" fill="#1e293b" stroke="#334155" stroke-width="1"/>
  <text x="181" y="35" text-anchor="middle" fill="#94a3b8" font-size="8" font-family="ui-monospace,Menlo,monospace" font-weight="600">VIH_2_REEBOX_F</text>
  <text x="181" y="47" text-anchor="middle" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">pin 3 (H) &#xb7; pin 4 (L)</text>
  <line x1="228" y1="35" x2="258" y2="35" stroke="#22c55e" stroke-width="1.5"/>
  <line x1="228" y1="43" x2="258" y2="43" stroke="#9ca3af" stroke-width="1.5"/>
  <rect x="258" y="22" width="80" height="32" rx="4" fill="#1e293b" stroke="#334155" stroke-width="1"/>
  <text x="298" y="35" text-anchor="middle" fill="#94a3b8" font-size="8" font-family="ui-monospace,Menlo,monospace" font-weight="600">Reebox_Main_F</text>
  <text x="298" y="47" text-anchor="middle" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">pin 3 (H) &#xb7; pin 4 (L)</text>
  <rect x="10" y="70" width="10" height="6" rx="1" fill="#22c55e"/>
  <text x="24" y="77" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">CAN H (Green W19)</text>
  <rect x="120" y="70" width="10" height="6" rx="1" fill="#9ca3af"/>
  <text x="134" y="77" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">CAN L (Gray W8)</text>
  <circle cx="12" cy="88" r="4" fill="#22c55e" stroke="#166534" stroke-width="1"/>
  <text x="20" y="92" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">VIH internal splice (XCP path)</text>
</svg>`;

export const SCI_CAN_PATH_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 342 96" role="img" aria-label="SCI CAN signal path">
  <rect width="342" height="96" rx="6" fill="#0f172a" stroke="#1e293b" stroke-width="1.5"/>
  <text x="171" y="14" text-anchor="middle" fill="#64748b" font-size="9" font-family="ui-monospace,Menlo,monospace" font-weight="600">SCI CAN (CAN 2) &#x2014; Signal Path</text>
  <rect x="4" y="22" width="78" height="32" rx="4" fill="#1e293b" stroke="#334155" stroke-width="1"/>
  <text x="43" y="35" text-anchor="middle" fill="#94a3b8" font-size="8.5" font-family="ui-monospace,Menlo,monospace" font-weight="600">REECU X8</text>
  <text x="43" y="47" text-anchor="middle" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">CREECU_1 (CAN 2)</text>
  <line x1="82" y1="35" x2="106" y2="35" stroke="#9ca3af" stroke-width="1.5"/>
  <line x1="82" y1="43" x2="106" y2="43" stroke="#3b82f6" stroke-width="1.5"/>
  <circle cx="110" cy="35" r="4" fill="#6b7280" stroke="#374151" stroke-width="1"/>
  <circle cx="110" cy="43" r="4" fill="#3b82f6" stroke="#1e40af" stroke-width="1"/>
  <text x="110" y="56" text-anchor="middle" fill="#334155" font-size="7" font-family="ui-monospace,Menlo,monospace">splice</text>
  <line x1="114" y1="35" x2="134" y2="35" stroke="#9ca3af" stroke-width="1.5"/>
  <line x1="114" y1="43" x2="134" y2="43" stroke="#3b82f6" stroke-width="1.5"/>
  <rect x="134" y="22" width="94" height="32" rx="4" fill="#1e293b" stroke="#334155" stroke-width="1"/>
  <text x="181" y="35" text-anchor="middle" fill="#94a3b8" font-size="8" font-family="ui-monospace,Menlo,monospace" font-weight="600">VIH_2_REEBOX_F</text>
  <text x="181" y="47" text-anchor="middle" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">pin 5 (H) &#xb7; pin 6 (L)</text>
  <line x1="228" y1="35" x2="258" y2="35" stroke="#9ca3af" stroke-width="1.5"/>
  <line x1="228" y1="43" x2="258" y2="43" stroke="#3b82f6" stroke-width="1.5"/>
  <rect x="258" y="22" width="80" height="32" rx="4" fill="#1e293b" stroke="#334155" stroke-width="1"/>
  <text x="298" y="35" text-anchor="middle" fill="#94a3b8" font-size="8" font-family="ui-monospace,Menlo,monospace" font-weight="600">Reebox_Main_F</text>
  <text x="298" y="47" text-anchor="middle" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">pin 5 (H) &#xb7; pin 6 (L)</text>
  <rect x="10" y="70" width="10" height="6" rx="1" fill="#9ca3af"/>
  <text x="24" y="77" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">CAN H (Gray W21)</text>
  <rect x="120" y="70" width="10" height="6" rx="1" fill="#3b82f6"/>
  <text x="134" y="77" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">CAN L (Blue W20)</text>
  <circle cx="12" cy="88" r="4" fill="#6b7280" stroke="#374151" stroke-width="1"/>
  <text x="20" y="92" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">VIH internal splice (SCI path)</text>
</svg>`;

export const BODY_CAN_PATH_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 342 96" role="img" aria-label="BODY CAN signal path">
  <rect width="342" height="96" rx="6" fill="#0f172a" stroke="#1e293b" stroke-width="1.5"/>
  <text x="171" y="14" text-anchor="middle" fill="#64748b" font-size="9" font-family="ui-monospace,Menlo,monospace" font-weight="600">BODY CAN &#x2014; Signal Path</text>
  <rect x="4" y="22" width="78" height="32" rx="4" fill="#1e293b" stroke="#334155" stroke-width="1"/>
  <text x="43" y="35" text-anchor="middle" fill="#94a3b8" font-size="8.5" font-family="ui-monospace,Menlo,monospace" font-weight="600">REECU X8</text>
  <text x="43" y="47" text-anchor="middle" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">CREECU_1 (BODY)</text>
  <line x1="82" y1="35" x2="106" y2="35" stroke="#ef4444" stroke-width="1.5"/>
  <line x1="82" y1="43" x2="106" y2="43" stroke="#3b82f6" stroke-width="1.5"/>
  <circle cx="110" cy="35" r="4" fill="#ef4444" stroke="#7f1d1d" stroke-width="1"/>
  <circle cx="110" cy="43" r="4" fill="#3b82f6" stroke="#1e40af" stroke-width="1"/>
  <text x="110" y="56" text-anchor="middle" fill="#334155" font-size="7" font-family="ui-monospace,Menlo,monospace">splice</text>
  <line x1="114" y1="35" x2="134" y2="35" stroke="#ef4444" stroke-width="1.5"/>
  <line x1="114" y1="43" x2="134" y2="43" stroke="#3b82f6" stroke-width="1.5"/>
  <rect x="134" y="22" width="94" height="32" rx="4" fill="#1e293b" stroke="#334155" stroke-width="1"/>
  <text x="181" y="35" text-anchor="middle" fill="#94a3b8" font-size="8" font-family="ui-monospace,Menlo,monospace" font-weight="600">VIH_2_KIAFUSEBOX</text>
  <text x="181" y="47" text-anchor="middle" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">splice</text>
  <line x1="228" y1="35" x2="258" y2="35" stroke="#ef4444" stroke-width="1.5"/>
  <line x1="228" y1="43" x2="258" y2="43" stroke="#3b82f6" stroke-width="1.5"/>
  <rect x="258" y="22" width="80" height="32" rx="4" fill="#1e293b" stroke="#334155" stroke-width="1"/>
  <text x="298" y="35" text-anchor="middle" fill="#94a3b8" font-size="8" font-family="ui-monospace,Menlo,monospace" font-weight="600">CIPG_F</text>
  <text x="298" y="47" text-anchor="middle" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">pin 4 (H) &#xb7; pin 3 (L)</text>
  <rect x="10" y="70" width="10" height="6" rx="1" fill="#ef4444"/>
  <text x="24" y="77" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">CAN H (Red W54)</text>
  <rect x="120" y="70" width="10" height="6" rx="1" fill="#3b82f6"/>
  <text x="134" y="77" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">CAN L (Blue W51)</text>
  <circle cx="12" cy="88" r="4" fill="#ef4444" stroke="#7f1d1d" stroke-width="1"/>
  <text x="20" y="92" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">VIH internal splice (BODY path)</text>
</svg>`;

export const CHASSIS_CAN_PATH_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 342 96" role="img" aria-label="CHASSIS CAN signal path">
  <rect width="342" height="96" rx="6" fill="#0f172a" stroke="#1e293b" stroke-width="1.5"/>
  <text x="171" y="14" text-anchor="middle" fill="#64748b" font-size="9" font-family="ui-monospace,Menlo,monospace" font-weight="600">CHASSIS CAN &#x2014; Signal Path</text>
  <rect x="4" y="22" width="78" height="32" rx="4" fill="#1e293b" stroke="#334155" stroke-width="1"/>
  <text x="43" y="35" text-anchor="middle" fill="#94a3b8" font-size="8.5" font-family="ui-monospace,Menlo,monospace" font-weight="600">REECU X8</text>
  <text x="43" y="47" text-anchor="middle" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">CREECU_1 (CHASSIS)</text>
  <line x1="82" y1="35" x2="106" y2="35" stroke="#e2e8f0" stroke-width="1.5"/>
  <line x1="82" y1="43" x2="106" y2="43" stroke="#b45309" stroke-width="1.5"/>
  <circle cx="110" cy="35" r="4" fill="#e2e8f0" stroke="#94a3b8" stroke-width="1"/>
  <circle cx="110" cy="43" r="4" fill="#b45309" stroke="#78350f" stroke-width="1"/>
  <text x="110" y="56" text-anchor="middle" fill="#334155" font-size="7" font-family="ui-monospace,Menlo,monospace">splice</text>
  <line x1="114" y1="35" x2="134" y2="35" stroke="#e2e8f0" stroke-width="1.5"/>
  <line x1="114" y1="43" x2="134" y2="43" stroke="#b45309" stroke-width="1.5"/>
  <rect x="134" y="22" width="94" height="32" rx="4" fill="#1e293b" stroke="#334155" stroke-width="1"/>
  <text x="181" y="35" text-anchor="middle" fill="#94a3b8" font-size="8" font-family="ui-monospace,Menlo,monospace" font-weight="600">VIH_2_KIAFUSEBOX</text>
  <text x="181" y="47" text-anchor="middle" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">splice</text>
  <line x1="228" y1="35" x2="258" y2="35" stroke="#e2e8f0" stroke-width="1.5"/>
  <line x1="228" y1="43" x2="258" y2="43" stroke="#b45309" stroke-width="1.5"/>
  <rect x="258" y="22" width="80" height="32" rx="4" fill="#1e293b" stroke="#334155" stroke-width="1"/>
  <text x="298" y="35" text-anchor="middle" fill="#94a3b8" font-size="8" font-family="ui-monospace,Menlo,monospace" font-weight="600">CIPG_F</text>
  <text x="298" y="47" text-anchor="middle" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">pin 5 (H) &#xb7; pin 6 (L)</text>
  <rect x="10" y="70" width="10" height="6" rx="1" fill="#e2e8f0"/>
  <text x="24" y="77" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">CAN H (White W55)</text>
  <rect x="120" y="70" width="10" height="6" rx="1" fill="#b45309"/>
  <text x="134" y="77" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">CAN L (Brown W58)</text>
  <circle cx="12" cy="88" r="4" fill="#e2e8f0" stroke="#94a3b8" stroke-width="1"/>
  <text x="20" y="92" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">VIH internal splice (CHASSIS path)</text>
</svg>`;

export const POWERTRAIN_CAN_PATH_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 342 96" role="img" aria-label="POWERTRAIN CAN signal path">
  <rect width="342" height="96" rx="6" fill="#0f172a" stroke="#1e293b" stroke-width="1.5"/>
  <text x="171" y="14" text-anchor="middle" fill="#64748b" font-size="9" font-family="ui-monospace,Menlo,monospace" font-weight="600">POWERTRAIN CAN &#x2014; Signal Path</text>
  <rect x="4" y="22" width="78" height="32" rx="4" fill="#1e293b" stroke="#334155" stroke-width="1"/>
  <text x="43" y="35" text-anchor="middle" fill="#94a3b8" font-size="8.5" font-family="ui-monospace,Menlo,monospace" font-weight="600">REECU X8</text>
  <text x="43" y="47" text-anchor="middle" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">CREECU_0 / CREECU_1</text>
  <line x1="82" y1="35" x2="106" y2="35" stroke="#8b5cf6" stroke-width="1.5"/>
  <line x1="82" y1="43" x2="106" y2="43" stroke="#c4b5fd" stroke-width="1.5"/>
  <circle cx="110" cy="35" r="4" fill="#8b5cf6" stroke="#5b21b6" stroke-width="1"/>
  <circle cx="110" cy="43" r="4" fill="#c4b5fd" stroke="#7c3aed" stroke-width="1"/>
  <text x="110" y="56" text-anchor="middle" fill="#334155" font-size="7" font-family="ui-monospace,Menlo,monospace">splice</text>
  <line x1="114" y1="35" x2="134" y2="35" stroke="#8b5cf6" stroke-width="1.5"/>
  <line x1="114" y1="43" x2="134" y2="43" stroke="#c4b5fd" stroke-width="1.5"/>
  <rect x="134" y="22" width="94" height="32" rx="4" fill="#1e293b" stroke="#334155" stroke-width="1"/>
  <text x="181" y="35" text-anchor="middle" fill="#94a3b8" font-size="8" font-family="ui-monospace,Menlo,monospace" font-weight="600">CTR_CONSOLE</text>
  <text x="181" y="47" text-anchor="middle" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">via VIH splice</text>
  <line x1="228" y1="35" x2="258" y2="35" stroke="#8b5cf6" stroke-width="1.5"/>
  <line x1="228" y1="43" x2="258" y2="43" stroke="#c4b5fd" stroke-width="1.5"/>
  <rect x="258" y="22" width="80" height="32" rx="4" fill="#1e293b" stroke="#334155" stroke-width="1"/>
  <text x="298" y="35" text-anchor="middle" fill="#94a3b8" font-size="8" font-family="ui-monospace,Menlo,monospace" font-weight="600">SBW ECU</text>
  <text x="298" y="47" text-anchor="middle" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">Center Console harn.</text>
  <rect x="10" y="70" width="10" height="6" rx="1" fill="#8b5cf6"/>
  <text x="24" y="77" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">CAN H (Powertrain)</text>
  <rect x="120" y="70" width="10" height="6" rx="1" fill="#c4b5fd"/>
  <text x="134" y="77" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">CAN L (Powertrain)</text>
  <circle cx="12" cy="88" r="4" fill="#8b5cf6" stroke="#5b21b6" stroke-width="1"/>
  <text x="20" y="92" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">VIH internal splice (Powertrain path)</text>
</svg>`;

export const DIAG_CAN_PATH_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 342 96" role="img" aria-label="DIAG CAN signal path">
  <rect width="342" height="96" rx="6" fill="#0f172a" stroke="#1e293b" stroke-width="1.5"/>
  <text x="171" y="14" text-anchor="middle" fill="#64748b" font-size="9" font-family="ui-monospace,Menlo,monospace" font-weight="600">DIAG CAN &#x2014; Signal Path</text>
  <rect x="4" y="22" width="78" height="32" rx="4" fill="#1e293b" stroke="#334155" stroke-width="1"/>
  <text x="43" y="35" text-anchor="middle" fill="#94a3b8" font-size="8.5" font-family="ui-monospace,Menlo,monospace" font-weight="600">REECU X8</text>
  <text x="43" y="47" text-anchor="middle" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">CREECU_1 (DIAG)</text>
  <line x1="82" y1="35" x2="106" y2="35" stroke="#eab308" stroke-width="1.5"/>
  <line x1="82" y1="43" x2="106" y2="43" stroke="#22c55e" stroke-width="1.5"/>
  <circle cx="110" cy="35" r="4" fill="#eab308" stroke="#92400e" stroke-width="1"/>
  <circle cx="110" cy="43" r="4" fill="#22c55e" stroke="#166534" stroke-width="1"/>
  <text x="110" y="56" text-anchor="middle" fill="#334155" font-size="7" font-family="ui-monospace,Menlo,monospace">splice</text>
  <line x1="114" y1="35" x2="134" y2="35" stroke="#eab308" stroke-width="1.5"/>
  <line x1="114" y1="43" x2="134" y2="43" stroke="#22c55e" stroke-width="1.5"/>
  <rect x="134" y="22" width="94" height="32" rx="4" fill="#1e293b" stroke="#334155" stroke-width="1"/>
  <text x="181" y="35" text-anchor="middle" fill="#94a3b8" font-size="8" font-family="ui-monospace,Menlo,monospace" font-weight="600">VIH_2_KIAFUSEBOX</text>
  <text x="181" y="47" text-anchor="middle" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">splice</text>
  <line x1="228" y1="35" x2="258" y2="35" stroke="#eab308" stroke-width="1.5"/>
  <line x1="228" y1="43" x2="258" y2="43" stroke="#22c55e" stroke-width="1.5"/>
  <rect x="258" y="22" width="80" height="32" rx="4" fill="#1e293b" stroke="#334155" stroke-width="1"/>
  <text x="298" y="35" text-anchor="middle" fill="#94a3b8" font-size="8" font-family="ui-monospace,Menlo,monospace" font-weight="600">IPF_F</text>
  <text x="298" y="47" text-anchor="middle" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">pin 26 (H) &#xb7; pin 27 (L)</text>
  <rect x="10" y="70" width="10" height="6" rx="1" fill="#eab308"/>
  <text x="24" y="77" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">CAN H (Yellow W63)</text>
  <rect x="120" y="70" width="10" height="6" rx="1" fill="#22c55e"/>
  <text x="134" y="77" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">CAN L (Green W64)</text>
  <circle cx="12" cy="88" r="4" fill="#eab308" stroke="#92400e" stroke-width="1"/>
  <text x="20" y="92" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">VIH internal splice (DIAG path)</text>
</svg>`;

export const DEPB_CAN_PATH_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 342 96" role="img" aria-label="DEPB CAN signal path">
  <rect width="342" height="96" rx="6" fill="#0f172a" stroke="#1e293b" stroke-width="1.5"/>
  <text x="171" y="14" text-anchor="middle" fill="#64748b" font-size="9" font-family="ui-monospace,Menlo,monospace" font-weight="600">DEPB CAN &#x2014; Signal Path</text>
  <rect x="4" y="22" width="78" height="32" rx="4" fill="#1e293b" stroke="#334155" stroke-width="1"/>
  <text x="43" y="35" text-anchor="middle" fill="#94a3b8" font-size="8.5" font-family="ui-monospace,Menlo,monospace" font-weight="600">REECU X8</text>
  <text x="43" y="47" text-anchor="middle" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">CREECU_1 (DEPB)</text>
  <line x1="82" y1="35" x2="106" y2="35" stroke="#14b8a6" stroke-width="1.5"/>
  <line x1="82" y1="43" x2="106" y2="43" stroke="#06b6d4" stroke-width="1.5"/>
  <circle cx="110" cy="35" r="4" fill="#14b8a6" stroke="#0f766e" stroke-width="1"/>
  <circle cx="110" cy="43" r="4" fill="#06b6d4" stroke="#0e7490" stroke-width="1"/>
  <text x="110" y="56" text-anchor="middle" fill="#334155" font-size="7" font-family="ui-monospace,Menlo,monospace">splice</text>
  <line x1="114" y1="35" x2="134" y2="35" stroke="#14b8a6" stroke-width="1.5"/>
  <line x1="114" y1="43" x2="134" y2="43" stroke="#06b6d4" stroke-width="1.5"/>
  <rect x="134" y="22" width="94" height="32" rx="4" fill="#1e293b" stroke="#334155" stroke-width="1"/>
  <text x="181" y="35" text-anchor="middle" fill="#94a3b8" font-size="8" font-family="ui-monospace,Menlo,monospace" font-weight="600">Reebox_DEPB_M</text>
  <text x="181" y="47" text-anchor="middle" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">IPDU VS101400</text>
  <line x1="228" y1="35" x2="258" y2="35" stroke="#14b8a6" stroke-width="1.5"/>
  <line x1="228" y1="43" x2="258" y2="43" stroke="#06b6d4" stroke-width="1.5"/>
  <rect x="258" y="22" width="80" height="32" rx="4" fill="#1e293b" stroke="#334155" stroke-width="1"/>
  <text x="298" y="35" text-anchor="middle" fill="#94a3b8" font-size="8" font-family="ui-monospace,Menlo,monospace" font-weight="600">EPB_M</text>
  <text x="298" y="47" text-anchor="middle" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">pin 3 (H) &#xb7; pin 4 (L)</text>
  <rect x="10" y="70" width="10" height="6" rx="1" fill="#14b8a6"/>
  <text x="24" y="77" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">CAN H (Teal)</text>
  <rect x="120" y="70" width="10" height="6" rx="1" fill="#06b6d4"/>
  <text x="134" y="77" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">CAN L (Cyan)</text>
  <circle cx="12" cy="88" r="4" fill="#14b8a6" stroke="#0f766e" stroke-width="1"/>
  <text x="20" y="92" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">VIH &#x2192; IPDU &#x2192; DEPB extension harness</text>
</svg>`;

export const ESTOP_PATH_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 342 110" role="img" aria-label="E-Stop safety loop circuit">
  <rect width="342" height="110" rx="6" fill="#0f172a" stroke="#1e293b" stroke-width="1.5"/>
  <text x="171" y="14" text-anchor="middle" fill="#64748b" font-size="9" font-family="ui-monospace,Menlo,monospace" font-weight="600">E-Stop Safety Loops</text>
  <rect x="4" y="22" width="78" height="44" rx="4" fill="#1e293b" stroke="#334155" stroke-width="1"/>
  <text x="43" y="36" text-anchor="middle" fill="#94a3b8" font-size="8.5" font-family="ui-monospace,Menlo,monospace" font-weight="600">E-Stop Button</text>
  <text x="43" y="50" text-anchor="middle" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">NC contact</text>
  <line x1="82" y1="32" x2="134" y2="32" stroke="#22c55e" stroke-width="1.5"/>
  <line x1="82" y1="40" x2="134" y2="40" stroke="#e2e8f0" stroke-width="1.5"/>
  <line x1="82" y1="48" x2="134" y2="48" stroke="#3b82f6" stroke-width="1.5"/>
  <rect x="134" y="22" width="94" height="44" rx="4" fill="#1e293b" stroke="#334155" stroke-width="1"/>
  <text x="181" y="36" text-anchor="middle" fill="#94a3b8" font-size="8" font-family="ui-monospace,Menlo,monospace" font-weight="600">VS030812</text>
  <text x="181" y="50" text-anchor="middle" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">Loopback Harness</text>
  <line x1="228" y1="32" x2="258" y2="32" stroke="#22c55e" stroke-width="1.5"/>
  <line x1="228" y1="40" x2="258" y2="40" stroke="#e2e8f0" stroke-width="1.5"/>
  <line x1="228" y1="48" x2="258" y2="48" stroke="#3b82f6" stroke-width="1.5"/>
  <rect x="258" y="22" width="80" height="44" rx="4" fill="#1e293b" stroke="#334155" stroke-width="1"/>
  <text x="298" y="36" text-anchor="middle" fill="#94a3b8" font-size="8" font-family="ui-monospace,Menlo,monospace" font-weight="600">REECU Safety</text>
  <text x="298" y="50" text-anchor="middle" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">Relay Input</text>
  <rect x="10" y="74" width="10" height="6" rx="1" fill="#22c55e"/>
  <text x="24" y="80" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">Loop 1 (Green W1)</text>
  <rect x="120" y="74" width="10" height="6" rx="1" fill="#e2e8f0"/>
  <text x="134" y="80" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">Loop 2 (White W2)</text>
  <rect x="220" y="74" width="10" height="6" rx="1" fill="#3b82f6"/>
  <text x="234" y="80" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">Loop 3 (Blue W3)</text>
  <text x="171" y="99" text-anchor="middle" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">All 3 loops must be closed &#x2014; any open loop trips E-Stop</text>
</svg>`;

export const TIH_PATH_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 342 96" role="img" aria-label="Telestation Integration Harness path">
  <rect width="342" height="96" rx="6" fill="#0f172a" stroke="#1e293b" stroke-width="1.5"/>
  <text x="171" y="14" text-anchor="middle" fill="#64748b" font-size="9" font-family="ui-monospace,Menlo,monospace" font-weight="600">Telestation Integration Harness</text>
  <rect x="4" y="22" width="78" height="32" rx="4" fill="#1e293b" stroke="#334155" stroke-width="1"/>
  <text x="43" y="35" text-anchor="middle" fill="#94a3b8" font-size="8.5" font-family="ui-monospace,Menlo,monospace" font-weight="600">REECU X8</text>
  <text x="43" y="47" text-anchor="middle" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">CREECU_X9</text>
  <line x1="82" y1="35" x2="106" y2="35" stroke="#eab308" stroke-width="1.5"/>
  <line x1="82" y1="43" x2="106" y2="43" stroke="#9ca3af" stroke-width="1.5"/>
  <circle cx="110" cy="35" r="4" fill="#eab308" stroke="#92400e" stroke-width="1"/>
  <circle cx="110" cy="43" r="4" fill="#6b7280" stroke="#374151" stroke-width="1"/>
  <text x="110" y="56" text-anchor="middle" fill="#334155" font-size="7" font-family="ui-monospace,Menlo,monospace">splice</text>
  <line x1="114" y1="35" x2="134" y2="35" stroke="#eab308" stroke-width="1.5"/>
  <line x1="114" y1="43" x2="134" y2="43" stroke="#9ca3af" stroke-width="1.5"/>
  <rect x="134" y="22" width="94" height="32" rx="4" fill="#1e293b" stroke="#334155" stroke-width="1"/>
  <text x="181" y="35" text-anchor="middle" fill="#94a3b8" font-size="8" font-family="ui-monospace,Menlo,monospace" font-weight="600">TIH_REECU_F</text>
  <text x="181" y="47" text-anchor="middle" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">harness entry</text>
  <line x1="228" y1="35" x2="258" y2="35" stroke="#eab308" stroke-width="1.5"/>
  <line x1="228" y1="43" x2="258" y2="43" stroke="#9ca3af" stroke-width="1.5"/>
  <rect x="258" y="22" width="80" height="32" rx="4" fill="#1e293b" stroke="#334155" stroke-width="1"/>
  <text x="298" y="35" text-anchor="middle" fill="#94a3b8" font-size="8" font-family="ui-monospace,Menlo,monospace" font-weight="600">TIH_Main_M</text>
  <text x="298" y="47" text-anchor="middle" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">vehicle docking</text>
  <rect x="10" y="70" width="10" height="6" rx="1" fill="#eab308"/>
  <text x="24" y="77" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">APP CAN H (Yellow)</text>
  <rect x="120" y="70" width="10" height="6" rx="1" fill="#9ca3af"/>
  <text x="134" y="77" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">APP CAN L (Gray)</text>
  <text x="171" y="92" text-anchor="middle" fill="#334155" font-size="7" font-family="ui-monospace,Menlo,monospace">+ XCP &#xb7; SCI &#xb7; WAKE &#xb7; USB &#xb7; GND in bundle</text>
</svg>`;

export const TS_POWER_PATH_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 342 96" role="img" aria-label="TS power chain">
  <rect width="342" height="96" rx="6" fill="#0f172a" stroke="#1e293b" stroke-width="1.5"/>
  <text x="171" y="14" text-anchor="middle" fill="#64748b" font-size="9" font-family="ui-monospace,Menlo,monospace" font-weight="600">TS Power Chain &#x2014; 12 V DC</text>
  <rect x="4" y="22" width="82" height="32" rx="4" fill="#1e293b" stroke="#334155" stroke-width="1"/>
  <text x="45" y="35" text-anchor="middle" fill="#94a3b8" font-size="8.5" font-family="ui-monospace,Menlo,monospace" font-weight="600">Mains AC</text>
  <text x="45" y="47" text-anchor="middle" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">IEC input</text>
  <line x1="86" y1="39" x2="130" y2="39" stroke="#f97316" stroke-width="2.5"/>
  <rect x="130" y="22" width="84" height="32" rx="4" fill="#1e293b" stroke="#334155" stroke-width="1"/>
  <text x="172" y="35" text-anchor="middle" fill="#94a3b8" font-size="8" font-family="ui-monospace,Menlo,monospace" font-weight="600">AC/DC PSU</text>
  <text x="172" y="47" text-anchor="middle" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">ts-acdc-eu / us</text>
  <line x1="214" y1="39" x2="254" y2="39" stroke="#f97316" stroke-width="2.5"/>
  <rect x="254" y="22" width="84" height="32" rx="4" fill="#1e293b" stroke="#334155" stroke-width="1"/>
  <text x="296" y="35" text-anchor="middle" fill="#94a3b8" font-size="8" font-family="ui-monospace,Menlo,monospace" font-weight="600">REECU_POWER</text>
  <text x="296" y="47" text-anchor="middle" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">12 V rail</text>
  <rect x="10" y="64" width="10" height="6" rx="1" fill="#f97316"/>
  <text x="24" y="77" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">12 V DC (Orange)</text>
  <text x="171" y="92" text-anchor="middle" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">Also feeds: display, Peplink router, fans</text>
</svg>`;

export const TS_XCP_CAN_PATH_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 342 96" role="img" aria-label="TS XCP CAN signal path">
  <rect width="342" height="96" rx="6" fill="#0f172a" stroke="#1e293b" stroke-width="1.5"/>
  <text x="171" y="14" text-anchor="middle" fill="#64748b" font-size="9" font-family="ui-monospace,Menlo,monospace" font-weight="600">XCP CAN (TS) &#x2014; Signal Path</text>
  <rect x="4" y="22" width="78" height="32" rx="4" fill="#1e293b" stroke="#334155" stroke-width="1"/>
  <text x="43" y="35" text-anchor="middle" fill="#94a3b8" font-size="8.5" font-family="ui-monospace,Menlo,monospace" font-weight="600">REECU X8</text>
  <text x="43" y="47" text-anchor="middle" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">CREECU_X9 (CAN 1)</text>
  <line x1="82" y1="35" x2="106" y2="35" stroke="#22c55e" stroke-width="1.5"/>
  <line x1="82" y1="43" x2="106" y2="43" stroke="#9ca3af" stroke-width="1.5"/>
  <circle cx="110" cy="35" r="4" fill="#22c55e" stroke="#166534" stroke-width="1"/>
  <circle cx="110" cy="43" r="4" fill="#6b7280" stroke="#374151" stroke-width="1"/>
  <text x="110" y="56" text-anchor="middle" fill="#334155" font-size="7" font-family="ui-monospace,Menlo,monospace">splice</text>
  <line x1="114" y1="35" x2="134" y2="35" stroke="#22c55e" stroke-width="1.5"/>
  <line x1="114" y1="43" x2="134" y2="43" stroke="#9ca3af" stroke-width="1.5"/>
  <rect x="134" y="22" width="94" height="32" rx="4" fill="#1e293b" stroke="#334155" stroke-width="1"/>
  <text x="181" y="35" text-anchor="middle" fill="#94a3b8" font-size="8" font-family="ui-monospace,Menlo,monospace" font-weight="600">TIH_REECU_F</text>
  <text x="181" y="47" text-anchor="middle" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">integration harness</text>
  <line x1="228" y1="35" x2="258" y2="35" stroke="#22c55e" stroke-width="1.5"/>
  <line x1="228" y1="43" x2="258" y2="43" stroke="#9ca3af" stroke-width="1.5"/>
  <rect x="258" y="22" width="80" height="32" rx="4" fill="#1e293b" stroke="#334155" stroke-width="1"/>
  <text x="298" y="35" text-anchor="middle" fill="#94a3b8" font-size="8" font-family="ui-monospace,Menlo,monospace" font-weight="600">TIH_Main_M</text>
  <text x="298" y="47" text-anchor="middle" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">vehicle docking</text>
  <rect x="10" y="70" width="10" height="6" rx="1" fill="#22c55e"/>
  <text x="24" y="77" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">CAN H (Green)</text>
  <rect x="120" y="70" width="10" height="6" rx="1" fill="#9ca3af"/>
  <text x="134" y="77" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">CAN L (Gray)</text>
  <circle cx="12" cy="88" r="4" fill="#22c55e" stroke="#166534" stroke-width="1"/>
  <text x="20" y="92" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">TIH internal junction</text>
</svg>`;

export const TS_SCI_CAN_PATH_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 342 96" role="img" aria-label="TS SCI CAN signal path">
  <rect width="342" height="96" rx="6" fill="#0f172a" stroke="#1e293b" stroke-width="1.5"/>
  <text x="171" y="14" text-anchor="middle" fill="#64748b" font-size="9" font-family="ui-monospace,Menlo,monospace" font-weight="600">SCI CAN (TS) &#x2014; Signal Path</text>
  <rect x="4" y="22" width="78" height="32" rx="4" fill="#1e293b" stroke="#334155" stroke-width="1"/>
  <text x="43" y="35" text-anchor="middle" fill="#94a3b8" font-size="8.5" font-family="ui-monospace,Menlo,monospace" font-weight="600">REECU X8</text>
  <text x="43" y="47" text-anchor="middle" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">CREECU_X9 (CAN 2)</text>
  <line x1="82" y1="35" x2="106" y2="35" stroke="#9ca3af" stroke-width="1.5"/>
  <line x1="82" y1="43" x2="106" y2="43" stroke="#3b82f6" stroke-width="1.5"/>
  <circle cx="110" cy="35" r="4" fill="#6b7280" stroke="#374151" stroke-width="1"/>
  <circle cx="110" cy="43" r="4" fill="#3b82f6" stroke="#1e40af" stroke-width="1"/>
  <text x="110" y="56" text-anchor="middle" fill="#334155" font-size="7" font-family="ui-monospace,Menlo,monospace">splice</text>
  <line x1="114" y1="35" x2="134" y2="35" stroke="#9ca3af" stroke-width="1.5"/>
  <line x1="114" y1="43" x2="134" y2="43" stroke="#3b82f6" stroke-width="1.5"/>
  <rect x="134" y="22" width="94" height="32" rx="4" fill="#1e293b" stroke="#334155" stroke-width="1"/>
  <text x="181" y="35" text-anchor="middle" fill="#94a3b8" font-size="8" font-family="ui-monospace,Menlo,monospace" font-weight="600">TIH_REECU_F</text>
  <text x="181" y="47" text-anchor="middle" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">integration harness</text>
  <line x1="228" y1="35" x2="258" y2="35" stroke="#9ca3af" stroke-width="1.5"/>
  <line x1="228" y1="43" x2="258" y2="43" stroke="#3b82f6" stroke-width="1.5"/>
  <rect x="258" y="22" width="80" height="32" rx="4" fill="#1e293b" stroke="#334155" stroke-width="1"/>
  <text x="298" y="35" text-anchor="middle" fill="#94a3b8" font-size="8" font-family="ui-monospace,Menlo,monospace" font-weight="600">TIH_Main_M</text>
  <text x="298" y="47" text-anchor="middle" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">vehicle docking</text>
  <rect x="10" y="70" width="10" height="6" rx="1" fill="#9ca3af"/>
  <text x="24" y="77" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">CAN H (Gray)</text>
  <rect x="120" y="70" width="10" height="6" rx="1" fill="#3b82f6"/>
  <text x="134" y="77" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">CAN L (Blue)</text>
  <circle cx="12" cy="88" r="4" fill="#6b7280" stroke="#374151" stroke-width="1"/>
  <text x="20" y="92" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">TIH internal junction</text>
</svg>`;

export const CIPG_F_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 230" role="img" aria-label="CIPG_F connector pinout">
  <rect width="320" height="230" rx="6" fill="#0f172a" stroke="#1e293b" stroke-width="1.5"/>
  <text x="160" y="18" text-anchor="middle" fill="#94a3b8" font-size="11" font-family="ui-monospace,Menlo,monospace" font-weight="600">CIPG_F &#xb7; 16-pin &#x2640;</text>
  <text x="160" y="31" text-anchor="middle" fill="#475569" font-size="9" font-family="ui-monospace,Menlo,monospace">TE 2005076-1 &#xb7; KIAFUSEBOX harness VS051800 v1.4</text>
  <text x="160" y="43" text-anchor="middle" fill="#334155" font-size="8" font-family="ui-monospace,Menlo,monospace" font-style="italic">CAN pins only &#x2014; 4 of 16 shown</text>
  <rect x="8" y="50" width="304" height="172" rx="4" fill="#0a1628" stroke="#1e3a5f" stroke-width="1"/>
  <rect x="10" y="54" width="300" height="36" rx="3" fill="#0a1040" stroke="#1e3a8f" stroke-width="0.5"/>
  <circle cx="28" cy="72" r="9" fill="#0a1040" stroke="#3b82f6" stroke-width="1.5"/>
  <text x="28" y="72" text-anchor="middle" dominant-baseline="central" fill="#93c5fd" font-size="9" font-family="ui-monospace,Menlo,monospace" font-weight="700">3</text>
  <text x="44" y="67" fill="#93c5fd" font-size="10" font-family="ui-monospace,Menlo,monospace" font-weight="600">BODY_CAN_L</text>
  <text x="44" y="79" fill="#3b82f6" font-size="8" font-family="ui-monospace,Menlo,monospace">BODY CAN Low &#xb7; Blue W51</text>
  <rect x="284" y="65" width="22" height="14" rx="2" fill="#3b82f6"/>
  <text x="295" y="72" text-anchor="middle" dominant-baseline="central" fill="#0f172a" font-size="7" font-family="ui-monospace,Menlo,monospace" font-weight="700">BLU</text>
  <rect x="10" y="94" width="300" height="36" rx="3" fill="#1a0505" stroke="#7f1d1d" stroke-width="0.5" opacity="0.9"/>
  <circle cx="28" cy="112" r="9" fill="#1a0505" stroke="#ef4444" stroke-width="1.5"/>
  <text x="28" y="112" text-anchor="middle" dominant-baseline="central" fill="#fca5a5" font-size="9" font-family="ui-monospace,Menlo,monospace" font-weight="700">4</text>
  <text x="44" y="107" fill="#fca5a5" font-size="10" font-family="ui-monospace,Menlo,monospace" font-weight="600">BODY_CAN_H</text>
  <text x="44" y="119" fill="#ef4444" font-size="8" font-family="ui-monospace,Menlo,monospace">BODY CAN High &#xb7; Red W54</text>
  <rect x="284" y="105" width="22" height="14" rx="2" fill="#ef4444"/>
  <text x="295" y="112" text-anchor="middle" dominant-baseline="central" fill="#0f172a" font-size="7" font-family="ui-monospace,Menlo,monospace" font-weight="700">RED</text>
  <rect x="10" y="134" width="300" height="36" rx="3" fill="#111827" stroke="#e2e8f0" stroke-width="0.4"/>
  <circle cx="28" cy="152" r="9" fill="#111827" stroke="#e2e8f0" stroke-width="1.5"/>
  <text x="28" y="152" text-anchor="middle" dominant-baseline="central" fill="#f1f5f9" font-size="9" font-family="ui-monospace,Menlo,monospace" font-weight="700">5</text>
  <text x="44" y="147" fill="#f1f5f9" font-size="10" font-family="ui-monospace,Menlo,monospace" font-weight="600">CHASSIS_CAN_H</text>
  <text x="44" y="159" fill="#94a3b8" font-size="8" font-family="ui-monospace,Menlo,monospace">CHASSIS CAN High &#xb7; White W55</text>
  <rect x="284" y="145" width="22" height="14" rx="2" fill="#f1f5f9"/>
  <text x="295" y="152" text-anchor="middle" dominant-baseline="central" fill="#0f172a" font-size="7" font-family="ui-monospace,Menlo,monospace" font-weight="700">WHT</text>
  <rect x="10" y="174" width="300" height="36" rx="3" fill="#1c0f00" stroke="#92400e" stroke-width="0.5"/>
  <circle cx="28" cy="192" r="9" fill="#1c0f00" stroke="#b45309" stroke-width="1.5"/>
  <text x="28" y="192" text-anchor="middle" dominant-baseline="central" fill="#fbbf24" font-size="9" font-family="ui-monospace,Menlo,monospace" font-weight="700">6</text>
  <text x="44" y="187" fill="#d97706" font-size="10" font-family="ui-monospace,Menlo,monospace" font-weight="600">CHASSIS_CAN_L</text>
  <text x="44" y="199" fill="#92400e" font-size="8" font-family="ui-monospace,Menlo,monospace">CHASSIS CAN Low &#xb7; Brown W58</text>
  <rect x="284" y="185" width="22" height="14" rx="2" fill="#b45309"/>
  <text x="295" y="192" text-anchor="middle" dominant-baseline="central" fill="#f1f5f9" font-size="7" font-family="ui-monospace,Menlo,monospace" font-weight="700">BRN</text>
  <text x="160" y="222" text-anchor="middle" fill="#334155" font-size="7.5" font-family="ui-monospace,Menlo,monospace">pins 1&#x2013;2, 7&#x2013;16: other vehicle signals</text>
</svg>`;

export const IPF_F_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 280 150" role="img" aria-label="IPF_F connector pinout">
  <rect width="280" height="150" rx="6" fill="#0f172a" stroke="#1e293b" stroke-width="1.5"/>
  <text x="140" y="16" text-anchor="middle" fill="#94a3b8" font-size="11" font-family="ui-monospace,Menlo,monospace" font-weight="600">IPF_F &#xb7; 40-pin (abbreviated)</text>
  <text x="140" y="29" text-anchor="middle" fill="#475569" font-size="9" font-family="ui-monospace,Menlo,monospace">Youye YY8401064 &#xb7; KIAFUSEBOX harness VS051800</text>
  <rect x="8" y="36" width="264" height="16" rx="3" fill="#0a1628" stroke="#334155" stroke-dasharray="4,3" stroke-width="1"/>
  <text x="140" y="47" text-anchor="middle" fill="#334155" font-size="8" font-family="ui-monospace,Menlo,monospace">&#xb7; &#xb7; &#xb7; pins 1 &#x2013; 25 &#xb7; &#xb7; &#xb7;</text>
  <rect x="8" y="54" width="264" height="36" rx="3" fill="#451a03" stroke="#92400e" stroke-width="0.5"/>
  <circle cx="26" cy="72" r="9" fill="#451a03" stroke="#f59e0b" stroke-width="1.5"/>
  <text x="26" y="72" text-anchor="middle" dominant-baseline="central" fill="#fbbf24" font-size="9" font-family="ui-monospace,Menlo,monospace" font-weight="700">26</text>
  <text x="42" y="67" fill="#fde68a" font-size="10" font-family="ui-monospace,Menlo,monospace" font-weight="600">DIAG_CAN_H</text>
  <text x="42" y="79" fill="#d97706" font-size="8" font-family="ui-monospace,Menlo,monospace">Diagnostic CAN High &#xb7; Yellow W63</text>
  <rect x="244" y="65" width="22" height="14" rx="2" fill="#eab308"/>
  <text x="255" y="72" text-anchor="middle" dominant-baseline="central" fill="#0f172a" font-size="7" font-family="ui-monospace,Menlo,monospace" font-weight="700">YLW</text>
  <rect x="8" y="92" width="264" height="36" rx="3" fill="#052e16" stroke="#166534" stroke-width="0.5"/>
  <circle cx="26" cy="110" r="9" fill="#052e16" stroke="#22c55e" stroke-width="1.5"/>
  <text x="26" y="110" text-anchor="middle" dominant-baseline="central" fill="#86efac" font-size="9" font-family="ui-monospace,Menlo,monospace" font-weight="700">27</text>
  <text x="42" y="105" fill="#86efac" font-size="10" font-family="ui-monospace,Menlo,monospace" font-weight="600">DIAG_CAN_L</text>
  <text x="42" y="117" fill="#166534" font-size="8" font-family="ui-monospace,Menlo,monospace">Diagnostic CAN Low &#xb7; Green W64</text>
  <rect x="244" y="103" width="22" height="14" rx="2" fill="#22c55e"/>
  <text x="255" y="110" text-anchor="middle" dominant-baseline="central" fill="#0f172a" font-size="7" font-family="ui-monospace,Menlo,monospace" font-weight="700">GRN</text>
  <rect x="8" y="130" width="264" height="16" rx="3" fill="#0a1628" stroke="#334155" stroke-dasharray="4,3" stroke-width="1"/>
  <text x="140" y="141" text-anchor="middle" fill="#334155" font-size="8" font-family="ui-monospace,Menlo,monospace">&#xb7; &#xb7; &#xb7; pins 28 &#x2013; 40 &#xb7; &#xb7; &#xb7;</text>
</svg>`;

export const EPB_M_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 280 180" role="img" aria-label="EPB_M connector pinout">
  <rect width="280" height="180" rx="6" fill="#0f172a" stroke="#1e293b" stroke-width="1.5"/>
  <text x="140" y="16" text-anchor="middle" fill="#94a3b8" font-size="11" font-family="ui-monospace,Menlo,monospace" font-weight="600">EPB_M &#xb7; 4-pin &#x2642;</text>
  <text x="140" y="29" text-anchor="middle" fill="#475569" font-size="9" font-family="ui-monospace,Menlo,monospace">KET MG651747-5 &#xb7; DEPB Extension harness VS051000</text>
  <rect x="8" y="36" width="264" height="136" rx="4" fill="#0a1628" stroke="#1e3a5f" stroke-width="1"/>
  <rect x="8" y="38" width="264" height="34" rx="3" fill="#1a0505" stroke="#7f1d1d" stroke-width="0.5"/>
  <circle cx="26" cy="55" r="9" fill="#1a0505" stroke="#ef4444" stroke-width="1.5"/>
  <text x="26" y="55" text-anchor="middle" dominant-baseline="central" fill="#fca5a5" font-size="9" font-family="ui-monospace,Menlo,monospace" font-weight="700">1</text>
  <text x="42" y="50" fill="#fca5a5" font-size="10" font-family="ui-monospace,Menlo,monospace" font-weight="600">Motor +</text>
  <text x="42" y="62" fill="#ef4444" font-size="8" font-family="ui-monospace,Menlo,monospace">1.5 mm&#xb2; &#xb7; Red &#xb7; W1/W2</text>
  <rect x="244" y="48" width="22" height="14" rx="2" fill="#ef4444"/>
  <text x="255" y="55" text-anchor="middle" dominant-baseline="central" fill="#0f172a" font-size="7" font-family="ui-monospace,Menlo,monospace" font-weight="700">RED</text>
  <rect x="8" y="74" width="264" height="34" rx="3" fill="#111217" stroke="#374151" stroke-width="0.5"/>
  <circle cx="26" cy="91" r="9" fill="#111217" stroke="#94a3b8" stroke-width="1.5"/>
  <text x="26" y="91" text-anchor="middle" dominant-baseline="central" fill="#94a3b8" font-size="9" font-family="ui-monospace,Menlo,monospace" font-weight="700">2</text>
  <text x="42" y="86" fill="#94a3b8" font-size="10" font-family="ui-monospace,Menlo,monospace" font-weight="600">Motor GND</text>
  <text x="42" y="98" fill="#64748b" font-size="8" font-family="ui-monospace,Menlo,monospace">1.5 mm&#xb2; &#xb7; Black &#xb7; W3/W4</text>
  <rect x="244" y="84" width="22" height="14" rx="2" fill="#374151"/>
  <text x="255" y="91" text-anchor="middle" dominant-baseline="central" fill="#9ca3af" font-size="7" font-family="ui-monospace,Menlo,monospace" font-weight="700">BLK</text>
  <rect x="8" y="110" width="264" height="34" rx="3" fill="#0a2020" stroke="#0f766e" stroke-width="0.5"/>
  <circle cx="26" cy="127" r="9" fill="#0a2020" stroke="#14b8a6" stroke-width="1.5"/>
  <text x="26" y="127" text-anchor="middle" dominant-baseline="central" fill="#5eead4" font-size="9" font-family="ui-monospace,Menlo,monospace" font-weight="700">3</text>
  <text x="42" y="122" fill="#5eead4" font-size="10" font-family="ui-monospace,Menlo,monospace" font-weight="600">DEPB_CAN_H</text>
  <text x="42" y="134" fill="#14b8a6" font-size="8" font-family="ui-monospace,Menlo,monospace">DEPB CAN High</text>
  <rect x="244" y="120" width="22" height="14" rx="2" fill="#14b8a6"/>
  <text x="255" y="127" text-anchor="middle" dominant-baseline="central" fill="#0f172a" font-size="7" font-family="ui-monospace,Menlo,monospace" font-weight="700">TEL</text>
  <rect x="8" y="146" width="264" height="34" rx="3" fill="#071c20" stroke="#0e7490" stroke-width="0.5"/>
  <circle cx="26" cy="163" r="9" fill="#071c20" stroke="#06b6d4" stroke-width="1.5"/>
  <text x="26" y="163" text-anchor="middle" dominant-baseline="central" fill="#67e8f9" font-size="9" font-family="ui-monospace,Menlo,monospace" font-weight="700">4</text>
  <text x="42" y="158" fill="#67e8f9" font-size="10" font-family="ui-monospace,Menlo,monospace" font-weight="600">DEPB_CAN_L</text>
  <text x="42" y="170" fill="#06b6d4" font-size="8" font-family="ui-monospace,Menlo,monospace">DEPB CAN Low</text>
  <rect x="244" y="156" width="22" height="14" rx="2" fill="#06b6d4"/>
  <text x="255" y="163" text-anchor="middle" dominant-baseline="central" fill="#0f172a" font-size="7" font-family="ui-monospace,Menlo,monospace" font-weight="700">CYN</text>
</svg>`;

export const E_STOP_F_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 280 210" role="img" aria-label="E_Stop_F connector pinout">
  <rect width="280" height="210" rx="6" fill="#0f172a" stroke="#1e293b" stroke-width="1.5"/>
  <text x="140" y="16" text-anchor="middle" fill="#94a3b8" font-size="11" font-family="ui-monospace,Menlo,monospace" font-weight="600">E_Stop_F &#xb7; 16-pin &#x2640;</text>
  <text x="140" y="29" text-anchor="middle" fill="#475569" font-size="9" font-family="ui-monospace,Menlo,monospace">TE 1473410-1 &#xb7; E-Stop loopback harness VS030812</text>
  <text x="140" y="41" text-anchor="middle" fill="#334155" font-size="8" font-family="ui-monospace,Menlo,monospace" font-style="italic">safety loop wires only &#x2014; 6 of 16 pins shown</text>
  <rect x="8" y="46" width="264" height="156" rx="4" fill="#0a1628" stroke="#1e3a5f" stroke-width="1"/>
  <rect x="8" y="48" width="264" height="24" rx="3" fill="#052e16" stroke="#166534" stroke-width="0.5"/>
  <circle cx="26" cy="60" r="8" fill="#052e16" stroke="#22c55e" stroke-width="1.5"/>
  <text x="26" y="60" text-anchor="middle" dominant-baseline="central" fill="#86efac" font-size="8" font-family="ui-monospace,Menlo,monospace" font-weight="700">A</text>
  <text x="40" y="56" fill="#86efac" font-size="9" font-family="ui-monospace,Menlo,monospace" font-weight="600">L1_OUT</text>
  <text x="40" y="67" fill="#166534" font-size="7.5" font-family="ui-monospace,Menlo,monospace">Green W1 &#xb7; Loop 1 out</text>
  <rect x="244" y="53" width="22" height="14" rx="2" fill="#22c55e"/>
  <text x="255" y="60" text-anchor="middle" dominant-baseline="central" fill="#0f172a" font-size="7" font-family="ui-monospace,Menlo,monospace" font-weight="700">GRN</text>
  <rect x="8" y="74" width="264" height="24" rx="3" fill="#052e16" stroke="#166534" stroke-width="0.5"/>
  <circle cx="26" cy="86" r="8" fill="#052e16" stroke="#22c55e" stroke-width="1.5"/>
  <text x="26" y="86" text-anchor="middle" dominant-baseline="central" fill="#86efac" font-size="8" font-family="ui-monospace,Menlo,monospace" font-weight="700">B</text>
  <text x="40" y="82" fill="#86efac" font-size="9" font-family="ui-monospace,Menlo,monospace" font-weight="600">L1_RTN</text>
  <text x="40" y="93" fill="#166534" font-size="7.5" font-family="ui-monospace,Menlo,monospace">Green W1 &#xb7; Loop 1 return</text>
  <rect x="244" y="79" width="22" height="14" rx="2" fill="#22c55e"/>
  <text x="255" y="86" text-anchor="middle" dominant-baseline="central" fill="#0f172a" font-size="7" font-family="ui-monospace,Menlo,monospace" font-weight="700">GRN</text>
  <rect x="8" y="100" width="264" height="24" rx="3" fill="#111827" stroke="#e2e8f0" stroke-width="0.4"/>
  <circle cx="26" cy="112" r="8" fill="#111827" stroke="#e2e8f0" stroke-width="1.5"/>
  <text x="26" y="112" text-anchor="middle" dominant-baseline="central" fill="#f1f5f9" font-size="8" font-family="ui-monospace,Menlo,monospace" font-weight="700">C</text>
  <text x="40" y="108" fill="#f1f5f9" font-size="9" font-family="ui-monospace,Menlo,monospace" font-weight="600">L2_OUT</text>
  <text x="40" y="119" fill="#94a3b8" font-size="7.5" font-family="ui-monospace,Menlo,monospace">White W2 &#xb7; Loop 2 out</text>
  <rect x="244" y="105" width="22" height="14" rx="2" fill="#e2e8f0"/>
  <text x="255" y="112" text-anchor="middle" dominant-baseline="central" fill="#0f172a" font-size="7" font-family="ui-monospace,Menlo,monospace" font-weight="700">WHT</text>
  <rect x="8" y="126" width="264" height="24" rx="3" fill="#111827" stroke="#e2e8f0" stroke-width="0.4"/>
  <circle cx="26" cy="138" r="8" fill="#111827" stroke="#e2e8f0" stroke-width="1.5"/>
  <text x="26" y="138" text-anchor="middle" dominant-baseline="central" fill="#f1f5f9" font-size="8" font-family="ui-monospace,Menlo,monospace" font-weight="700">D</text>
  <text x="40" y="134" fill="#f1f5f9" font-size="9" font-family="ui-monospace,Menlo,monospace" font-weight="600">L2_RTN</text>
  <text x="40" y="145" fill="#94a3b8" font-size="7.5" font-family="ui-monospace,Menlo,monospace">White W2 &#xb7; Loop 2 return</text>
  <rect x="244" y="131" width="22" height="14" rx="2" fill="#e2e8f0"/>
  <text x="255" y="138" text-anchor="middle" dominant-baseline="central" fill="#0f172a" font-size="7" font-family="ui-monospace,Menlo,monospace" font-weight="700">WHT</text>
  <rect x="8" y="152" width="264" height="24" rx="3" fill="#0a1040" stroke="#1e3a8f" stroke-width="0.5"/>
  <circle cx="26" cy="164" r="8" fill="#0a1040" stroke="#3b82f6" stroke-width="1.5"/>
  <text x="26" y="164" text-anchor="middle" dominant-baseline="central" fill="#93c5fd" font-size="8" font-family="ui-monospace,Menlo,monospace" font-weight="700">E</text>
  <text x="40" y="160" fill="#93c5fd" font-size="9" font-family="ui-monospace,Menlo,monospace" font-weight="600">L3_OUT</text>
  <text x="40" y="171" fill="#3b82f6" font-size="7.5" font-family="ui-monospace,Menlo,monospace">Blue W3 &#xb7; Loop 3 out</text>
  <rect x="244" y="157" width="22" height="14" rx="2" fill="#3b82f6"/>
  <text x="255" y="164" text-anchor="middle" dominant-baseline="central" fill="#0f172a" font-size="7" font-family="ui-monospace,Menlo,monospace" font-weight="700">BLU</text>
  <rect x="8" y="178" width="264" height="24" rx="3" fill="#0a1040" stroke="#1e3a8f" stroke-width="0.5"/>
  <circle cx="26" cy="190" r="8" fill="#0a1040" stroke="#3b82f6" stroke-width="1.5"/>
  <text x="26" y="190" text-anchor="middle" dominant-baseline="central" fill="#93c5fd" font-size="8" font-family="ui-monospace,Menlo,monospace" font-weight="700">F</text>
  <text x="40" y="186" fill="#93c5fd" font-size="9" font-family="ui-monospace,Menlo,monospace" font-weight="600">L3_RTN</text>
  <text x="40" y="197" fill="#3b82f6" font-size="7.5" font-family="ui-monospace,Menlo,monospace">Blue W3 &#xb7; Loop 3 return</text>
  <rect x="244" y="183" width="22" height="14" rx="2" fill="#3b82f6"/>
  <text x="255" y="190" text-anchor="middle" dominant-baseline="central" fill="#0f172a" font-size="7" font-family="ui-monospace,Menlo,monospace" font-weight="700">BLU</text>
  <text x="140" y="207" text-anchor="middle" fill="#334155" font-size="7.5" font-family="ui-monospace,Menlo,monospace">&lt; 1 &#x3a9; across each loop when E-Stop released</text>
</svg>`;

export const TIH_MAIN_M_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 280 220" role="img" aria-label="TIH_Main_M connector pinout">
  <rect width="280" height="220" rx="6" fill="#0f172a" stroke="#1e293b" stroke-width="1.5"/>
  <text x="140" y="16" text-anchor="middle" fill="#94a3b8" font-size="11" font-family="ui-monospace,Menlo,monospace" font-weight="600">TIH_Main_M &#xb7; Docking Connector</text>
  <text x="140" y="29" text-anchor="middle" fill="#475569" font-size="9" font-family="ui-monospace,Menlo,monospace">Telestation Integration Harness (TIH)</text>
  <text x="140" y="41" text-anchor="middle" fill="#334155" font-size="8" font-family="ui-monospace,Menlo,monospace">APP CAN / XCP / SCI / WAKE signal pins</text>
  <rect x="8" y="46" width="264" height="158" rx="4" fill="#0a1628" stroke="#1e3a5f" stroke-width="1"/>
  <rect x="8" y="48" width="264" height="24" rx="3" fill="#451a03" stroke="#92400e" stroke-width="0.5"/>
  <circle cx="26" cy="60" r="8" fill="#451a03" stroke="#f59e0b" stroke-width="1.5"/>
  <text x="26" y="60" text-anchor="middle" dominant-baseline="central" fill="#fbbf24" font-size="8" font-family="ui-monospace,Menlo,monospace" font-weight="700">1</text>
  <text x="40" y="56" fill="#fde68a" font-size="9" font-family="ui-monospace,Menlo,monospace" font-weight="600">APP_CAN_H</text>
  <text x="40" y="67" fill="#d97706" font-size="7.5" font-family="ui-monospace,Menlo,monospace">APP CAN High &#xb7; Yellow</text>
  <rect x="244" y="53" width="22" height="14" rx="2" fill="#eab308"/>
  <text x="255" y="60" text-anchor="middle" dominant-baseline="central" fill="#0f172a" font-size="7" font-family="ui-monospace,Menlo,monospace" font-weight="700">YLW</text>
  <rect x="8" y="74" width="264" height="24" rx="3" fill="#1a1f2e" stroke="#334155" stroke-width="0.5"/>
  <circle cx="26" cy="86" r="8" fill="#1a1f2e" stroke="#94a3b8" stroke-width="1.5"/>
  <text x="26" y="86" text-anchor="middle" dominant-baseline="central" fill="#94a3b8" font-size="8" font-family="ui-monospace,Menlo,monospace" font-weight="700">2</text>
  <text x="40" y="82" fill="#cbd5e1" font-size="9" font-family="ui-monospace,Menlo,monospace" font-weight="600">APP_CAN_L</text>
  <text x="40" y="93" fill="#64748b" font-size="7.5" font-family="ui-monospace,Menlo,monospace">APP CAN Low &#xb7; Gray</text>
  <rect x="244" y="79" width="22" height="14" rx="2" fill="#9ca3af"/>
  <text x="255" y="86" text-anchor="middle" dominant-baseline="central" fill="#0f172a" font-size="7" font-family="ui-monospace,Menlo,monospace" font-weight="700">GRY</text>
  <rect x="8" y="100" width="264" height="24" rx="3" fill="#052e16" stroke="#166534" stroke-width="0.5"/>
  <circle cx="26" cy="112" r="8" fill="#052e16" stroke="#22c55e" stroke-width="1.5"/>
  <text x="26" y="112" text-anchor="middle" dominant-baseline="central" fill="#86efac" font-size="8" font-family="ui-monospace,Menlo,monospace" font-weight="700">3</text>
  <text x="40" y="108" fill="#86efac" font-size="9" font-family="ui-monospace,Menlo,monospace" font-weight="600">XCP_CAN_H</text>
  <text x="40" y="119" fill="#166534" font-size="7.5" font-family="ui-monospace,Menlo,monospace">XCP CAN High &#xb7; Green W19</text>
  <rect x="244" y="105" width="22" height="14" rx="2" fill="#22c55e"/>
  <text x="255" y="112" text-anchor="middle" dominant-baseline="central" fill="#0f172a" font-size="7" font-family="ui-monospace,Menlo,monospace" font-weight="700">GRN</text>
  <rect x="8" y="126" width="264" height="24" rx="3" fill="#1a1f2e" stroke="#334155" stroke-width="0.5"/>
  <circle cx="26" cy="138" r="8" fill="#1a1f2e" stroke="#94a3b8" stroke-width="1.5"/>
  <text x="26" y="138" text-anchor="middle" dominant-baseline="central" fill="#94a3b8" font-size="8" font-family="ui-monospace,Menlo,monospace" font-weight="700">4</text>
  <text x="40" y="134" fill="#cbd5e1" font-size="9" font-family="ui-monospace,Menlo,monospace" font-weight="600">XCP_CAN_L</text>
  <text x="40" y="145" fill="#64748b" font-size="7.5" font-family="ui-monospace,Menlo,monospace">XCP CAN Low &#xb7; Gray W8</text>
  <rect x="244" y="131" width="22" height="14" rx="2" fill="#9ca3af"/>
  <text x="255" y="138" text-anchor="middle" dominant-baseline="central" fill="#0f172a" font-size="7" font-family="ui-monospace,Menlo,monospace" font-weight="700">GRY</text>
  <rect x="8" y="152" width="264" height="24" rx="3" fill="#111827" stroke="#475569" stroke-width="0.4"/>
  <circle cx="26" cy="164" r="8" fill="#111827" stroke="#9ca3af" stroke-width="1.5"/>
  <text x="26" y="164" text-anchor="middle" dominant-baseline="central" fill="#94a3b8" font-size="8" font-family="ui-monospace,Menlo,monospace" font-weight="700">5</text>
  <text x="40" y="160" fill="#cbd5e1" font-size="9" font-family="ui-monospace,Menlo,monospace" font-weight="600">SCI_CAN_H</text>
  <text x="40" y="171" fill="#64748b" font-size="7.5" font-family="ui-monospace,Menlo,monospace">SCI CAN High &#xb7; Gray W21</text>
  <rect x="244" y="157" width="22" height="14" rx="2" fill="#9ca3af"/>
  <text x="255" y="164" text-anchor="middle" dominant-baseline="central" fill="#0f172a" font-size="7" font-family="ui-monospace,Menlo,monospace" font-weight="700">GRY</text>
  <rect x="8" y="178" width="264" height="24" rx="3" fill="#0a1040" stroke="#1e3a8f" stroke-width="0.5"/>
  <circle cx="26" cy="190" r="8" fill="#0a1040" stroke="#3b82f6" stroke-width="1.5"/>
  <text x="26" y="190" text-anchor="middle" dominant-baseline="central" fill="#93c5fd" font-size="8" font-family="ui-monospace,Menlo,monospace" font-weight="700">6</text>
  <text x="40" y="186" fill="#93c5fd" font-size="9" font-family="ui-monospace,Menlo,monospace" font-weight="600">SCI_CAN_L</text>
  <text x="40" y="197" fill="#3b82f6" font-size="7.5" font-family="ui-monospace,Menlo,monospace">SCI CAN Low &#xb7; Blue W20</text>
  <rect x="244" y="183" width="22" height="14" rx="2" fill="#3b82f6"/>
  <text x="255" y="190" text-anchor="middle" dominant-baseline="central" fill="#0f172a" font-size="7" font-family="ui-monospace,Menlo,monospace" font-weight="700">BLU</text>
  <text x="140" y="212" text-anchor="middle" fill="#334155" font-size="7.5" font-family="ui-monospace,Menlo,monospace">other pins: WAKE &#xb7; USB &#xb7; GND &#xb7; spare</text>
</svg>`;

// ---------------------------------------------------------------------------
// Focused connector variants — one signal pair per diagram
// ---------------------------------------------------------------------------

export const REEBOX_MAIN_F_XCP_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 130" role="img" aria-label="Reebox_Main_F XCP CAN pins 3 and 4">
  <rect width="320" height="130" rx="6" fill="#0f172a" stroke="#1e293b" stroke-width="1.5"/>
  <text x="160" y="17" text-anchor="middle" fill="#94a3b8" font-size="11" font-family="ui-monospace,Menlo,monospace" font-weight="600">Reebox_Main_F &#xb7; XCP CAN (pins 3 &amp; 4)</text>
  <text x="160" y="30" text-anchor="middle" fill="#475569" font-size="9" font-family="ui-monospace,Menlo,monospace">VS101500 Accessory Harness &#xb7; 8-pin</text>
  <rect x="8" y="36" width="304" height="82" rx="4" fill="#0a1628" stroke="#1e3a5f" stroke-width="1"/>
  <rect x="10" y="38" width="300" height="36" rx="3" fill="#052e16" stroke="#22c55e" stroke-width="1.5"/>
  <circle cx="28" cy="56" r="9" fill="#052e16" stroke="#22c55e" stroke-width="1.5"/>
  <text x="28" y="56" text-anchor="middle" dominant-baseline="central" fill="#86efac" font-size="9" font-family="ui-monospace,Menlo,monospace" font-weight="700">3</text>
  <text x="44" y="51" fill="#86efac" font-size="10" font-family="ui-monospace,Menlo,monospace" font-weight="600">XCP_CAN_H</text>
  <text x="44" y="63" fill="#166534" font-size="8" font-family="ui-monospace,Menlo,monospace">XCP CAN High &#xb7; Green W19</text>
  <rect x="284" y="49" width="22" height="14" rx="2" fill="#22c55e"/>
  <text x="295" y="56" text-anchor="middle" dominant-baseline="central" fill="#052e16" font-size="7" font-family="ui-monospace,Menlo,monospace" font-weight="700">GRN</text>
  <rect x="10" y="76" width="300" height="36" rx="3" fill="#1a2030" stroke="#6b7280" stroke-width="1"/>
  <circle cx="28" cy="94" r="9" fill="#1a2030" stroke="#9ca3af" stroke-width="1.5"/>
  <text x="28" y="94" text-anchor="middle" dominant-baseline="central" fill="#e2e8f0" font-size="9" font-family="ui-monospace,Menlo,monospace" font-weight="700">4</text>
  <text x="44" y="89" fill="#e2e8f0" font-size="10" font-family="ui-monospace,Menlo,monospace" font-weight="600">XCP_CAN_L</text>
  <text x="44" y="101" fill="#94a3b8" font-size="8" font-family="ui-monospace,Menlo,monospace">XCP CAN Low &#xb7; Gray W8</text>
  <rect x="284" y="87" width="22" height="14" rx="2" fill="#6b7280"/>
  <text x="295" y="94" text-anchor="middle" dominant-baseline="central" fill="#f8fafc" font-size="7" font-family="ui-monospace,Menlo,monospace" font-weight="700">GRY</text>
  <text x="160" y="126" text-anchor="middle" fill="#334155" font-size="7.5" font-family="ui-monospace,Menlo,monospace">pins 1&#x2013;2: APP CAN &#xb7; pins 5&#x2013;6: SCI CAN &#xb7; pins 7&#x2013;8: WAKE / K15</text>
</svg>`;

export const REEBOX_MAIN_F_SCI_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 130" role="img" aria-label="Reebox_Main_F SCI CAN pins 5 and 6">
  <rect width="320" height="130" rx="6" fill="#0f172a" stroke="#1e293b" stroke-width="1.5"/>
  <text x="160" y="17" text-anchor="middle" fill="#94a3b8" font-size="11" font-family="ui-monospace,Menlo,monospace" font-weight="600">Reebox_Main_F &#xb7; SCI CAN (pins 5 &amp; 6)</text>
  <text x="160" y="30" text-anchor="middle" fill="#475569" font-size="9" font-family="ui-monospace,Menlo,monospace">VS101500 Accessory Harness &#xb7; 8-pin</text>
  <rect x="8" y="36" width="304" height="82" rx="4" fill="#0a1628" stroke="#1e3a5f" stroke-width="1"/>
  <rect x="10" y="38" width="300" height="36" rx="3" fill="#1a2030" stroke="#9ca3af" stroke-width="1.5"/>
  <circle cx="28" cy="56" r="9" fill="#1a2030" stroke="#cbd5e1" stroke-width="1.5"/>
  <text x="28" y="56" text-anchor="middle" dominant-baseline="central" fill="#e2e8f0" font-size="9" font-family="ui-monospace,Menlo,monospace" font-weight="700">5</text>
  <text x="44" y="51" fill="#e2e8f0" font-size="10" font-family="ui-monospace,Menlo,monospace" font-weight="600">SCI_CAN_H</text>
  <text x="44" y="63" fill="#94a3b8" font-size="8" font-family="ui-monospace,Menlo,monospace">SCI CAN High &#xb7; Gray W21</text>
  <rect x="284" y="49" width="22" height="14" rx="2" fill="#9ca3af"/>
  <text x="295" y="56" text-anchor="middle" dominant-baseline="central" fill="#0f172a" font-size="7" font-family="ui-monospace,Menlo,monospace" font-weight="700">GRY</text>
  <rect x="10" y="76" width="300" height="36" rx="3" fill="#0a1040" stroke="#3b82f6" stroke-width="1.5"/>
  <circle cx="28" cy="94" r="9" fill="#0a1040" stroke="#3b82f6" stroke-width="1.5"/>
  <text x="28" y="94" text-anchor="middle" dominant-baseline="central" fill="#93c5fd" font-size="9" font-family="ui-monospace,Menlo,monospace" font-weight="700">6</text>
  <text x="44" y="89" fill="#93c5fd" font-size="10" font-family="ui-monospace,Menlo,monospace" font-weight="600">SCI_CAN_L</text>
  <text x="44" y="101" fill="#3b82f6" font-size="8" font-family="ui-monospace,Menlo,monospace">SCI CAN Low &#xb7; Blue W20</text>
  <rect x="284" y="87" width="22" height="14" rx="2" fill="#3b82f6"/>
  <text x="295" y="94" text-anchor="middle" dominant-baseline="central" fill="#0f172a" font-size="7" font-family="ui-monospace,Menlo,monospace" font-weight="700">BLU</text>
  <text x="160" y="126" text-anchor="middle" fill="#334155" font-size="7.5" font-family="ui-monospace,Menlo,monospace">pins 1&#x2013;2: APP CAN &#xb7; pins 3&#x2013;4: XCP CAN &#xb7; pins 7&#x2013;8: WAKE / K15</text>
</svg>`;

export const CIPG_F_BODY_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 130" role="img" aria-label="CIPG_F BODY CAN pins 4 and 3">
  <rect width="320" height="130" rx="6" fill="#0f172a" stroke="#1e293b" stroke-width="1.5"/>
  <text x="160" y="17" text-anchor="middle" fill="#94a3b8" font-size="11" font-family="ui-monospace,Menlo,monospace" font-weight="600">CIPG_F &#xb7; BODY CAN (pins 4 &amp; 3)</text>
  <text x="160" y="30" text-anchor="middle" fill="#475569" font-size="9" font-family="ui-monospace,Menlo,monospace">TE 2005076-1 &#xb7; KIAFUSEBOX harness VS051800</text>
  <rect x="8" y="36" width="304" height="82" rx="4" fill="#0a1628" stroke="#1e3a5f" stroke-width="1"/>
  <rect x="10" y="38" width="300" height="36" rx="3" fill="#1a0505" stroke="#ef4444" stroke-width="1.5"/>
  <circle cx="28" cy="56" r="9" fill="#1a0505" stroke="#ef4444" stroke-width="1.5"/>
  <text x="28" y="56" text-anchor="middle" dominant-baseline="central" fill="#fca5a5" font-size="9" font-family="ui-monospace,Menlo,monospace" font-weight="700">4</text>
  <text x="44" y="51" fill="#fca5a5" font-size="10" font-family="ui-monospace,Menlo,monospace" font-weight="600">BODY_CAN_H</text>
  <text x="44" y="63" fill="#ef4444" font-size="8" font-family="ui-monospace,Menlo,monospace">BODY CAN High &#xb7; Red W54</text>
  <rect x="284" y="49" width="22" height="14" rx="2" fill="#ef4444"/>
  <text x="295" y="56" text-anchor="middle" dominant-baseline="central" fill="#0f172a" font-size="7" font-family="ui-monospace,Menlo,monospace" font-weight="700">RED</text>
  <rect x="10" y="76" width="300" height="36" rx="3" fill="#0a1040" stroke="#3b82f6" stroke-width="1.5"/>
  <circle cx="28" cy="94" r="9" fill="#0a1040" stroke="#3b82f6" stroke-width="1.5"/>
  <text x="28" y="94" text-anchor="middle" dominant-baseline="central" fill="#93c5fd" font-size="9" font-family="ui-monospace,Menlo,monospace" font-weight="700">3</text>
  <text x="44" y="89" fill="#93c5fd" font-size="10" font-family="ui-monospace,Menlo,monospace" font-weight="600">BODY_CAN_L</text>
  <text x="44" y="101" fill="#3b82f6" font-size="8" font-family="ui-monospace,Menlo,monospace">BODY CAN Low &#xb7; Blue W51</text>
  <rect x="284" y="87" width="22" height="14" rx="2" fill="#3b82f6"/>
  <text x="295" y="94" text-anchor="middle" dominant-baseline="central" fill="#0f172a" font-size="7" font-family="ui-monospace,Menlo,monospace" font-weight="700">BLU</text>
  <text x="160" y="126" text-anchor="middle" fill="#334155" font-size="7.5" font-family="ui-monospace,Menlo,monospace">pin 5: CHASSIS CAN H (White) &#xb7; pin 6: CHASSIS CAN L (Brown)</text>
</svg>`;

export const CIPG_F_CHASSIS_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 130" role="img" aria-label="CIPG_F CHASSIS CAN pins 5 and 6">
  <rect width="320" height="130" rx="6" fill="#0f172a" stroke="#1e293b" stroke-width="1.5"/>
  <text x="160" y="17" text-anchor="middle" fill="#94a3b8" font-size="11" font-family="ui-monospace,Menlo,monospace" font-weight="600">CIPG_F &#xb7; CHASSIS CAN (pins 5 &amp; 6)</text>
  <text x="160" y="30" text-anchor="middle" fill="#475569" font-size="9" font-family="ui-monospace,Menlo,monospace">TE 2005076-1 &#xb7; KIAFUSEBOX harness VS051800</text>
  <rect x="8" y="36" width="304" height="82" rx="4" fill="#0a1628" stroke="#1e3a5f" stroke-width="1"/>
  <rect x="10" y="38" width="300" height="36" rx="3" fill="#111827" stroke="#e2e8f0" stroke-width="1.2"/>
  <circle cx="28" cy="56" r="9" fill="#1e293b" stroke="#e2e8f0" stroke-width="1.5"/>
  <text x="28" y="56" text-anchor="middle" dominant-baseline="central" fill="#f1f5f9" font-size="9" font-family="ui-monospace,Menlo,monospace" font-weight="700">5</text>
  <text x="44" y="51" fill="#f1f5f9" font-size="10" font-family="ui-monospace,Menlo,monospace" font-weight="600">CHASSIS_CAN_H</text>
  <text x="44" y="63" fill="#94a3b8" font-size="8" font-family="ui-monospace,Menlo,monospace">CHASSIS CAN High &#xb7; White W55</text>
  <rect x="284" y="49" width="22" height="14" rx="2" fill="#f1f5f9"/>
  <text x="295" y="56" text-anchor="middle" dominant-baseline="central" fill="#0f172a" font-size="7" font-family="ui-monospace,Menlo,monospace" font-weight="700">WHT</text>
  <rect x="10" y="76" width="300" height="36" rx="3" fill="#1c0f00" stroke="#b45309" stroke-width="1.5"/>
  <circle cx="28" cy="94" r="9" fill="#1c0f00" stroke="#b45309" stroke-width="1.5"/>
  <text x="28" y="94" text-anchor="middle" dominant-baseline="central" fill="#fbbf24" font-size="9" font-family="ui-monospace,Menlo,monospace" font-weight="700">6</text>
  <text x="44" y="89" fill="#d97706" font-size="10" font-family="ui-monospace,Menlo,monospace" font-weight="600">CHASSIS_CAN_L</text>
  <text x="44" y="101" fill="#92400e" font-size="8" font-family="ui-monospace,Menlo,monospace">CHASSIS CAN Low &#xb7; Brown W58</text>
  <rect x="284" y="87" width="22" height="14" rx="2" fill="#b45309"/>
  <text x="295" y="94" text-anchor="middle" dominant-baseline="central" fill="#f1f5f9" font-size="7" font-family="ui-monospace,Menlo,monospace" font-weight="700">BRN</text>
  <text x="160" y="126" text-anchor="middle" fill="#334155" font-size="7.5" font-family="ui-monospace,Menlo,monospace">pin 4: BODY CAN H (Red) &#xb7; pin 3: BODY CAN L (Blue)</text>
</svg>`;

// ---------------------------------------------------------------------------
// CAN Bus system-map overview
// ---------------------------------------------------------------------------

export const CAN_BUS_OVERVIEW_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 510" role="img" aria-label="CAN bus system overview">
  <rect width="800" height="510" rx="6" fill="#0f172a" stroke="#1e293b" stroke-width="1.5"/>

  <!-- ═══ LEVEL 1: REECU (y=10 h=62) ═══ -->
  <rect x="10" y="10" width="780" height="62" rx="6" fill="#1e293b" stroke="#334155" stroke-width="1"/>
  <text x="400" y="30" text-anchor="middle" fill="#94a3b8" font-size="11" font-family="ui-monospace,Menlo,monospace" font-weight="600">REECU &#xb7; X8 / X9 Connector (CREECU_0 / CREECU_1)</text>
  <!-- Signal labels row 1 (y=50) and row 2 (y=61) -->
  <text x="60"  y="50" text-anchor="middle" fill="#eab308" font-size="7" font-family="ui-monospace,Menlo,monospace" font-weight="600">CAN 0</text>
  <text x="60"  y="61" text-anchor="middle" fill="#eab308" font-size="7" font-family="ui-monospace,Menlo,monospace" font-weight="600">APP</text>
  <text x="110" y="50" text-anchor="middle" fill="#22c55e" font-size="7" font-family="ui-monospace,Menlo,monospace" font-weight="600">CAN 1</text>
  <text x="110" y="61" text-anchor="middle" fill="#22c55e" font-size="7" font-family="ui-monospace,Menlo,monospace" font-weight="600">XCP</text>
  <text x="160" y="50" text-anchor="middle" fill="#9ca3af" font-size="7" font-family="ui-monospace,Menlo,monospace" font-weight="600">CAN 2</text>
  <text x="160" y="61" text-anchor="middle" fill="#9ca3af" font-size="7" font-family="ui-monospace,Menlo,monospace" font-weight="600">SCI</text>
  <text x="260" y="50" text-anchor="middle" fill="#ef4444" font-size="7" font-family="ui-monospace,Menlo,monospace" font-weight="600">BODY</text>
  <text x="260" y="61" text-anchor="middle" fill="#ef4444" font-size="7" font-family="ui-monospace,Menlo,monospace" font-weight="600">CAN</text>
  <text x="330" y="50" text-anchor="middle" fill="#e2e8f0" font-size="7" font-family="ui-monospace,Menlo,monospace" font-weight="600">CHSS</text>
  <text x="330" y="61" text-anchor="middle" fill="#e2e8f0" font-size="7" font-family="ui-monospace,Menlo,monospace" font-weight="600">CAN</text>
  <text x="455" y="50" text-anchor="middle" fill="#f59e0b" font-size="7" font-family="ui-monospace,Menlo,monospace" font-weight="600">DIAG</text>
  <text x="455" y="61" text-anchor="middle" fill="#f59e0b" font-size="7" font-family="ui-monospace,Menlo,monospace" font-weight="600">CAN</text>
  <text x="572" y="50" text-anchor="middle" fill="#8b5cf6" font-size="7" font-family="ui-monospace,Menlo,monospace" font-weight="600">PT</text>
  <text x="572" y="61" text-anchor="middle" fill="#8b5cf6" font-size="7" font-family="ui-monospace,Menlo,monospace" font-weight="600">CAN</text>
  <text x="705" y="50" text-anchor="middle" fill="#14b8a6" font-size="7" font-family="ui-monospace,Menlo,monospace" font-weight="600">DEPB</text>
  <text x="705" y="61" text-anchor="middle" fill="#14b8a6" font-size="7" font-family="ui-monospace,Menlo,monospace" font-weight="600">CAN</text>
  <!-- Exit dots at y=72 -->
  <circle cx="60"  cy="72" r="3" fill="#eab308"/>
  <circle cx="110" cy="72" r="3" fill="#22c55e"/>
  <circle cx="160" cy="72" r="3" fill="#9ca3af"/>
  <circle cx="260" cy="72" r="3" fill="#ef4444"/>
  <circle cx="330" cy="72" r="3" fill="#e2e8f0"/>
  <circle cx="455" cy="72" r="3" fill="#f59e0b"/>
  <circle cx="572" cy="72" r="3" fill="#8b5cf6"/>
  <circle cx="705" cy="72" r="3" fill="#14b8a6"/>

  <!-- ═══ LEVEL 1→2 lines (y=72–115) ═══ -->
  <line x1="60"  y1="72" x2="60"  y2="115" stroke="#eab308" stroke-width="2"/>
  <line x1="110" y1="72" x2="110" y2="115" stroke="#22c55e" stroke-width="2"/>
  <line x1="160" y1="72" x2="160" y2="115" stroke="#9ca3af" stroke-width="2"/>
  <line x1="260" y1="72" x2="260" y2="115" stroke="#ef4444" stroke-width="2"/>
  <line x1="330" y1="72" x2="330" y2="115" stroke="#e2e8f0" stroke-width="2"/>
  <line x1="455" y1="72" x2="455" y2="115" stroke="#f59e0b" stroke-width="2"/>
  <line x1="572" y1="72" x2="572" y2="115" stroke="#8b5cf6" stroke-width="2"/>
  <line x1="705" y1="72" x2="705" y2="115" stroke="#14b8a6" stroke-width="2"/>

  <!-- ═══ LEVEL 2: VIH (y=115 h=72) ═══ -->
  <rect x="10" y="115" width="780" height="72" rx="6" fill="#1e293b" stroke="#334155" stroke-width="1"/>
  <text x="400" y="133" text-anchor="middle" fill="#94a3b8" font-size="11" font-family="ui-monospace,Menlo,monospace" font-weight="600">Vehicle Integration Harness (VIH &#xb7; VS050100)</text>
  <text x="400" y="147" text-anchor="middle" fill="#475569" font-size="9"  font-family="ui-monospace,Menlo,monospace">internal splice routing</text>
  <!-- Splice name labels at y=155 (font-size=6) -->
  <text x="60"  y="155" text-anchor="middle" fill="#eab308" font-size="6" font-family="ui-monospace,Menlo,monospace">S&#xb7;APP</text>
  <text x="110" y="155" text-anchor="middle" fill="#22c55e" font-size="6" font-family="ui-monospace,Menlo,monospace">S&#xb7;XCP</text>
  <text x="160" y="155" text-anchor="middle" fill="#9ca3af" font-size="6" font-family="ui-monospace,Menlo,monospace">S&#xb7;SCI</text>
  <text x="260" y="155" text-anchor="middle" fill="#ef4444" font-size="6" font-family="ui-monospace,Menlo,monospace">S&#xb7;BOD</text>
  <text x="330" y="155" text-anchor="middle" fill="#e2e8f0" font-size="6" font-family="ui-monospace,Menlo,monospace">S&#xb7;CHS</text>
  <text x="455" y="155" text-anchor="middle" fill="#f59e0b" font-size="6" font-family="ui-monospace,Menlo,monospace">S&#xb7;DIG</text>
  <text x="572" y="155" text-anchor="middle" fill="#8b5cf6" font-size="6" font-family="ui-monospace,Menlo,monospace">S&#xb7;PT</text>
  <text x="705" y="155" text-anchor="middle" fill="#14b8a6" font-size="6" font-family="ui-monospace,Menlo,monospace">S&#xb7;DE</text>
  <!-- Splice circles r=6 at cy=165 -->
  <circle cx="60"  cy="165" r="6" fill="#eab308" stroke="#0f172a" stroke-width="1"/>
  <circle cx="110" cy="165" r="6" fill="#22c55e" stroke="#0f172a" stroke-width="1"/>
  <circle cx="160" cy="165" r="6" fill="#9ca3af" stroke="#0f172a" stroke-width="1"/>
  <circle cx="260" cy="165" r="6" fill="#ef4444" stroke="#0f172a" stroke-width="1"/>
  <circle cx="330" cy="165" r="6" fill="#e2e8f0" stroke="#0f172a" stroke-width="1"/>
  <circle cx="455" cy="165" r="6" fill="#f59e0b" stroke="#0f172a" stroke-width="1"/>
  <circle cx="572" cy="165" r="6" fill="#8b5cf6" stroke="#0f172a" stroke-width="1"/>
  <circle cx="705" cy="165" r="6" fill="#14b8a6" stroke="#0f172a" stroke-width="1"/>
  <!-- Zone exit labels at y=180 -->
  <text x="110" y="180" text-anchor="middle" fill="#475569" font-size="7" font-family="ui-monospace,Menlo,monospace">VIH_2_REEBOX_F</text>
  <text x="295" y="180" text-anchor="middle" fill="#475569" font-size="7" font-family="ui-monospace,Menlo,monospace">VIH_2_KIAFUSE / CIPG</text>
  <text x="455" y="180" text-anchor="middle" fill="#475569" font-size="7" font-family="ui-monospace,Menlo,monospace">VIH_2_KIAFUSE / IPF</text>
  <text x="572" y="180" text-anchor="middle" fill="#475569" font-size="7" font-family="ui-monospace,Menlo,monospace">VIH_2_CTR_CONSOLE</text>
  <text x="705" y="180" text-anchor="middle" fill="#475569" font-size="7" font-family="ui-monospace,Menlo,monospace">VIH &#x2192; IPDU</text>

  <!-- ═══ LEVEL 2→3 lines (y=187–220) ═══ -->
  <line x1="60"  y1="187" x2="60"  y2="220" stroke="#eab308" stroke-width="2"/>
  <line x1="110" y1="187" x2="110" y2="220" stroke="#22c55e" stroke-width="2"/>
  <line x1="160" y1="187" x2="160" y2="220" stroke="#9ca3af" stroke-width="2"/>
  <line x1="260" y1="187" x2="260" y2="220" stroke="#ef4444" stroke-width="2"/>
  <line x1="330" y1="187" x2="330" y2="220" stroke="#e2e8f0" stroke-width="2"/>
  <line x1="455" y1="187" x2="455" y2="220" stroke="#f59e0b" stroke-width="2"/>
  <line x1="572" y1="187" x2="572" y2="220" stroke="#8b5cf6" stroke-width="2"/>
  <line x1="705" y1="187" x2="705" y2="220" stroke="#14b8a6" stroke-width="2"/>

  <!-- ═══ LEVEL 3: Harnesses (y=220 h=38) ═══ -->
  <!-- Harness 1: Accessory -->
  <rect x="10" y="220" width="200" height="38" rx="4" fill="#1a2535" stroke="#475569" stroke-width="1"/>
  <text x="110" y="234" text-anchor="middle" fill="#64748b" font-size="8" font-family="ui-monospace,Menlo,monospace" font-weight="600">Accessory Harness</text>
  <text x="110" y="247" text-anchor="middle" fill="#334155" font-size="7.5" font-family="ui-monospace,Menlo,monospace">VS101500 v4.2</text>
  <!-- Harness 2: KIAFUSEBOX -->
  <rect x="220" y="220" width="300" height="38" rx="4" fill="#1a2535" stroke="#475569" stroke-width="1"/>
  <text x="370" y="234" text-anchor="middle" fill="#64748b" font-size="8" font-family="ui-monospace,Menlo,monospace" font-weight="600">KIAFUSEBOX Harness</text>
  <text x="370" y="247" text-anchor="middle" fill="#334155" font-size="7.5" font-family="ui-monospace,Menlo,monospace">VS051800 v1.4</text>
  <!-- Harness 3: Center Console -->
  <rect x="530" y="220" width="92" height="38" rx="4" fill="#1a2535" stroke="#475569" stroke-width="1"/>
  <text x="576" y="234" text-anchor="middle" fill="#64748b" font-size="8" font-family="ui-monospace,Menlo,monospace" font-weight="600">Ctr Console</text>
  <text x="576" y="247" text-anchor="middle" fill="#334155" font-size="7.5" font-family="ui-monospace,Menlo,monospace">VS050900</text>
  <!-- Harness 4: IPDU + DEPB -->
  <rect x="632" y="220" width="158" height="38" rx="4" fill="#1a2535" stroke="#475569" stroke-width="1"/>
  <text x="711" y="234" text-anchor="middle" fill="#64748b" font-size="8" font-family="ui-monospace,Menlo,monospace" font-weight="600">IPDU + DEPB Ext.</text>
  <text x="711" y="247" text-anchor="middle" fill="#334155" font-size="7.5" font-family="ui-monospace,Menlo,monospace">VS101400 + VS051000</text>

  <!-- ═══ LEVEL 3→4 lines (y=258–290) ═══ -->
  <line x1="60"  y1="258" x2="60"  y2="290" stroke="#eab308" stroke-width="2"/>
  <line x1="110" y1="258" x2="110" y2="290" stroke="#22c55e" stroke-width="2"/>
  <line x1="160" y1="258" x2="160" y2="290" stroke="#9ca3af" stroke-width="2"/>
  <!-- BODY CAN → CIPG_F (x=260) AND CIPG_M (x=347) -->
  <line x1="260" y1="258" x2="260" y2="268" stroke="#ef4444" stroke-width="2"/>
  <line x1="260" y1="268" x2="347" y2="268" stroke="#ef4444" stroke-width="2"/>
  <circle cx="260" cy="268" r="3" fill="#ef4444" stroke="#0f172a" stroke-width="1"/>
  <line x1="260" y1="268" x2="260" y2="290" stroke="#ef4444" stroke-width="2"/>
  <line x1="347" y1="268" x2="347" y2="290" stroke="#ef4444" stroke-width="2"/>
  <!-- CHASSIS CAN → CIPG_F (x=262) AND CIPG_M (x=349) -->
  <line x1="330" y1="258" x2="330" y2="278" stroke="#e2e8f0" stroke-width="2"/>
  <line x1="262" y1="278" x2="349" y2="278" stroke="#e2e8f0" stroke-width="2"/>
  <circle cx="330" cy="278" r="3" fill="#e2e8f0" stroke="#0f172a" stroke-width="1"/>
  <line x1="262" y1="278" x2="262" y2="290" stroke="#e2e8f0" stroke-width="2"/>
  <line x1="349" y1="278" x2="349" y2="290" stroke="#e2e8f0" stroke-width="2"/>
  <line x1="455" y1="258" x2="455" y2="290" stroke="#f59e0b" stroke-width="2"/>
  <line x1="572" y1="258" x2="572" y2="290" stroke="#8b5cf6" stroke-width="2"/>
  <line x1="705" y1="258" x2="705" y2="290" stroke="#14b8a6" stroke-width="2"/>

  <!-- ═══ LEVEL 4: Terminal connectors (y=290 h=195) ═══ -->

  <!-- Block 1: Reebox_Main_F -->
  <rect x="10" y="290" width="200" height="195" rx="6" fill="#1e293b" stroke="#eab308" stroke-width="1"/>
  <text x="110" y="308" text-anchor="middle" fill="#94a3b8" font-size="10" font-family="ui-monospace,Menlo,monospace" font-weight="600">Reebox_Main_F</text>
  <text x="110" y="320" text-anchor="middle" fill="#475569" font-size="8"  font-family="ui-monospace,Menlo,monospace">Accessory VS101500</text>
  <!-- APP CAN: H=yellow p1, L=gray p2 -->
  <circle cx="26" cy="337" r="4" fill="#eab308"/><text x="33" y="341" fill="#eab308" font-size="7.5" font-family="ui-monospace,Menlo,monospace">p1&#xb7;H</text>
  <circle cx="88" cy="337" r="4" fill="#9ca3af"/><text x="95" y="341" fill="#9ca3af" font-size="7.5" font-family="ui-monospace,Menlo,monospace">p2&#xb7;L</text>
  <text x="152" y="341" fill="#64748b" font-size="7.5" font-family="ui-monospace,Menlo,monospace">APP CAN</text>
  <!-- XCP CAN: H=green p3, L=gray p4 -->
  <circle cx="26" cy="355" r="4" fill="#22c55e"/><text x="33" y="359" fill="#22c55e" font-size="7.5" font-family="ui-monospace,Menlo,monospace">p3&#xb7;H</text>
  <circle cx="88" cy="355" r="4" fill="#9ca3af"/><text x="95" y="359" fill="#9ca3af" font-size="7.5" font-family="ui-monospace,Menlo,monospace">p4&#xb7;L</text>
  <text x="152" y="359" fill="#64748b" font-size="7.5" font-family="ui-monospace,Menlo,monospace">XCP CAN</text>
  <!-- SCI CAN: H=gray p5, L=blue p6 -->
  <circle cx="26" cy="373" r="4" fill="#9ca3af"/><text x="33" y="377" fill="#9ca3af" font-size="7.5" font-family="ui-monospace,Menlo,monospace">p5&#xb7;H</text>
  <circle cx="88" cy="373" r="4" fill="#3b82f6"/><text x="95" y="377" fill="#3b82f6" font-size="7.5" font-family="ui-monospace,Menlo,monospace">p6&#xb7;L</text>
  <text x="152" y="377" fill="#64748b" font-size="7.5" font-family="ui-monospace,Menlo,monospace">SCI CAN</text>
  <!-- WAKE / K15 -->
  <circle cx="26" cy="391" r="4" fill="#f97316"/><text x="33" y="395" fill="#f97316" font-size="7.5" font-family="ui-monospace,Menlo,monospace">p7&#xb7;WK</text>
  <circle cx="88" cy="391" r="4" fill="#ef4444"/><text x="95" y="395" fill="#ef4444" font-size="7.5" font-family="ui-monospace,Menlo,monospace">p8&#xb7;K15</text>

  <!-- Block 2a: CIPG_F -->
  <rect x="218" y="290" width="84" height="195" rx="6" fill="#1e293b" stroke="#ef4444" stroke-width="1"/>
  <text x="260" y="308" text-anchor="middle" fill="#94a3b8" font-size="10" font-family="ui-monospace,Menlo,monospace" font-weight="600">CIPG_F</text>
  <text x="260" y="320" text-anchor="middle" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">VS051800</text>
  <!-- BODY: H=red(p4,W54), L=blue(p3,W51) -->
  <circle cx="228" cy="337" r="3.5" fill="#ef4444"/><text x="234" y="341" fill="#ef4444" font-size="7" font-family="ui-monospace,Menlo,monospace">p4&#xb7;H</text>
  <circle cx="261" cy="337" r="3.5" fill="#3b82f6"/><text x="267" y="341" fill="#3b82f6" font-size="7" font-family="ui-monospace,Menlo,monospace">p3&#xb7;L</text>
  <text x="260" y="351" text-anchor="middle" fill="#64748b" font-size="6.5" font-family="ui-monospace,Menlo,monospace">BODY CAN</text>
  <!-- CHASSIS: H=white(p5,W55), L=brown(p6,W58) -->
  <circle cx="228" cy="367" r="3.5" fill="#e2e8f0"/><text x="234" y="371" fill="#e2e8f0" font-size="7" font-family="ui-monospace,Menlo,monospace">p5&#xb7;H</text>
  <circle cx="261" cy="367" r="3.5" fill="#b45309"/><text x="267" y="371" fill="#b45309" font-size="7" font-family="ui-monospace,Menlo,monospace">p6&#xb7;L</text>
  <text x="260" y="381" text-anchor="middle" fill="#64748b" font-size="6.5" font-family="ui-monospace,Menlo,monospace">CHASSIS</text>
  <!-- Block 2b: CIPG_M -->
  <rect x="305" y="290" width="84" height="195" rx="6" fill="#1e293b" stroke="#e2e8f0" stroke-width="1"/>
  <text x="347" y="308" text-anchor="middle" fill="#94a3b8" font-size="10" font-family="ui-monospace,Menlo,monospace" font-weight="600">CIPG_M</text>
  <text x="347" y="320" text-anchor="middle" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">VS051800</text>
  <!-- BODY: H=red(p4,W53), L=blue(p3,W52) -->
  <circle cx="315" cy="337" r="3.5" fill="#ef4444"/><text x="321" y="341" fill="#ef4444" font-size="7" font-family="ui-monospace,Menlo,monospace">p4&#xb7;H</text>
  <circle cx="348" cy="337" r="3.5" fill="#3b82f6"/><text x="354" y="341" fill="#3b82f6" font-size="7" font-family="ui-monospace,Menlo,monospace">p3&#xb7;L</text>
  <text x="347" y="351" text-anchor="middle" fill="#64748b" font-size="6.5" font-family="ui-monospace,Menlo,monospace">BODY CAN</text>
  <!-- CHASSIS: H=white(p5,W56), L=brown(p6,W57) -->
  <circle cx="315" cy="367" r="3.5" fill="#e2e8f0"/><text x="321" y="371" fill="#e2e8f0" font-size="7" font-family="ui-monospace,Menlo,monospace">p5&#xb7;H</text>
  <circle cx="348" cy="367" r="3.5" fill="#b45309"/><text x="354" y="371" fill="#b45309" font-size="7" font-family="ui-monospace,Menlo,monospace">p6&#xb7;L</text>
  <text x="347" y="381" text-anchor="middle" fill="#64748b" font-size="6.5" font-family="ui-monospace,Menlo,monospace">CHASSIS</text>

  <!-- Block 3: IPF_F -->
  <rect x="400" y="290" width="120" height="195" rx="6" fill="#1e293b" stroke="#eab308" stroke-width="1"/>
  <text x="460" y="308" text-anchor="middle" fill="#94a3b8" font-size="10" font-family="ui-monospace,Menlo,monospace" font-weight="600">IPF_F</text>
  <text x="460" y="320" text-anchor="middle" fill="#475569" font-size="8"  font-family="ui-monospace,Menlo,monospace">KIAFUSEBOX VS051800</text>
  <text x="460" y="332" text-anchor="middle" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">40-pin</text>
  <!-- DIAG: H=yellow(p26,W63), L=green(p27,W64) -->
  <circle cx="420" cy="348" r="4" fill="#eab308"/><text x="427" y="352" fill="#eab308" font-size="8" font-family="ui-monospace,Menlo,monospace">p26&#xb7;H</text>
  <circle cx="475" cy="348" r="4" fill="#22c55e"/><text x="482" y="352" fill="#22c55e" font-size="8" font-family="ui-monospace,Menlo,monospace">p27&#xb7;L</text>
  <text x="460" y="366" text-anchor="middle" fill="#64748b" font-size="7.5" font-family="ui-monospace,Menlo,monospace">DIAG CAN</text>

  <!-- Block 4: SBW ECU -->
  <rect x="530" y="290" width="92" height="195" rx="6" fill="#1e293b" stroke="#8b5cf6" stroke-width="1"/>
  <text x="576" y="308" text-anchor="middle" fill="#94a3b8" font-size="10" font-family="ui-monospace,Menlo,monospace" font-weight="600">SBW ECU</text>
  <text x="576" y="320" text-anchor="middle" fill="#475569" font-size="8"  font-family="ui-monospace,Menlo,monospace">Center Console</text>
  <text x="576" y="332" text-anchor="middle" fill="#475569" font-size="7.5" font-family="ui-monospace,Menlo,monospace">VS050900</text>
  <!-- PT CAN: H=purple, L=light-purple -->
  <circle cx="548" cy="348" r="4" fill="#8b5cf6"/><text x="555" y="352" fill="#8b5cf6" font-size="8" font-family="ui-monospace,Menlo,monospace">H</text>
  <circle cx="580" cy="348" r="4" fill="#c4b5fd"/><text x="587" y="352" fill="#c4b5fd" font-size="8" font-family="ui-monospace,Menlo,monospace">L</text>
  <text x="576" y="366" text-anchor="middle" fill="#64748b" font-size="8" font-family="ui-monospace,Menlo,monospace">PT CAN</text>

  <!-- Block 5: IPDU→EPB_M -->
  <rect x="632" y="290" width="158" height="195" rx="6" fill="#1e293b" stroke="#14b8a6" stroke-width="1"/>
  <text x="711" y="308" text-anchor="middle" fill="#94a3b8" font-size="10" font-family="ui-monospace,Menlo,monospace" font-weight="600">Reebox_DEPB_M</text>
  <text x="711" y="320" text-anchor="middle" fill="#475569" font-size="8"  font-family="ui-monospace,Menlo,monospace">IPDU VS101400</text>
  <text x="711" y="332" text-anchor="middle" fill="#334155" font-size="7"  font-family="ui-monospace,Menlo,monospace">&#x2192; EPB_M &#xb7; DEPB Ext VS051000</text>
  <!-- DEPB CAN: H=teal(p3), L=cyan(p4) via EPB_M -->
  <circle cx="655" cy="348" r="4" fill="#14b8a6"/><text x="662" y="352" fill="#14b8a6" font-size="8" font-family="ui-monospace,Menlo,monospace">p3&#xb7;H</text>
  <circle cx="710" cy="348" r="4" fill="#06b6d4"/><text x="717" y="352" fill="#06b6d4" font-size="8" font-family="ui-monospace,Menlo,monospace">p4&#xb7;L</text>
  <text x="711" y="366" text-anchor="middle" fill="#64748b" font-size="8" font-family="ui-monospace,Menlo,monospace">DEPB CAN</text>

  <!-- ═══ Footer legend (y=500) ═══ -->
  <circle cx="20" cy="500" r="5" fill="#eab308" stroke="#0f172a" stroke-width="1"/>
  <text x="30" y="504" fill="#334155" font-size="7.5" font-family="ui-monospace,Menlo,monospace">= splice junction inside VIH</text>
</svg>`;
