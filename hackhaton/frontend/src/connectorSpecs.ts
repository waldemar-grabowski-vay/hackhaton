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
  <rect x="164" y="60" width="14" height="14" rx="2" fill="#94a3b8"/>
  <text x="276" y="62" text-anchor="end" fill="#e2e8f0" font-size="10" font-family="ui-monospace,Menlo,monospace" font-weight="600">APP_CAN_L</text>
  <text x="276" y="75" text-anchor="end" fill="#94a3b8" font-size="8" font-family="ui-monospace,Menlo,monospace">APP Low</text>
  <circle cx="292" cy="67" r="9" fill="#1e293b" stroke="#94a3b8" stroke-width="1"/>
  <text x="292" y="67" text-anchor="middle" dominant-baseline="central" fill="#94a3b8" font-size="9" font-family="ui-monospace,Menlo,monospace" font-weight="700">2</text>
  <circle cx="28" cy="109" r="9" fill="#1e293b" stroke="#334155" stroke-width="1"/>
  <text x="28" y="109" text-anchor="middle" dominant-baseline="central" fill="#64748b" font-size="9" font-family="ui-monospace,Menlo,monospace" font-weight="700">3</text>
  <text x="44" y="104" fill="#94a3b8" font-size="10" font-family="ui-monospace,Menlo,monospace">XCP_CAN_H</text>
  <text x="44" y="117" fill="#475569" font-size="8" font-family="ui-monospace,Menlo,monospace">XCP High</text>
  <rect x="142" y="102" width="14" height="14" rx="2" fill="#22c55e"/>
  <rect x="164" y="102" width="14" height="14" rx="2" fill="#94a3b8"/>
  <text x="276" y="104" text-anchor="end" fill="#94a3b8" font-size="10" font-family="ui-monospace,Menlo,monospace">XCP_CAN_L</text>
  <text x="276" y="117" text-anchor="end" fill="#475569" font-size="8" font-family="ui-monospace,Menlo,monospace">XCP Low</text>
  <circle cx="292" cy="109" r="9" fill="#1e293b" stroke="#334155" stroke-width="1"/>
  <text x="292" y="109" text-anchor="middle" dominant-baseline="central" fill="#64748b" font-size="9" font-family="ui-monospace,Menlo,monospace" font-weight="700">4</text>
  <circle cx="28" cy="151" r="9" fill="#1e293b" stroke="#334155" stroke-width="1"/>
  <text x="28" y="151" text-anchor="middle" dominant-baseline="central" fill="#64748b" font-size="9" font-family="ui-monospace,Menlo,monospace" font-weight="700">5</text>
  <text x="44" y="146" fill="#94a3b8" font-size="10" font-family="ui-monospace,Menlo,monospace">SCI_CAN_H</text>
  <text x="44" y="159" fill="#475569" font-size="8" font-family="ui-monospace,Menlo,monospace">SCI High</text>
  <rect x="142" y="144" width="14" height="14" rx="2" fill="#9ca3af"/>
  <rect x="164" y="144" width="14" height="14" rx="2" fill="#3b82f6"/>
  <text x="276" y="146" text-anchor="end" fill="#94a3b8" font-size="10" font-family="ui-monospace,Menlo,monospace">SCI_CAN_L</text>
  <text x="276" y="159" text-anchor="end" fill="#475569" font-size="8" font-family="ui-monospace,Menlo,monospace">SCI Low</text>
  <circle cx="292" cy="151" r="9" fill="#1e293b" stroke="#334155" stroke-width="1"/>
  <text x="292" y="151" text-anchor="middle" dominant-baseline="central" fill="#64748b" font-size="9" font-family="ui-monospace,Menlo,monospace" font-weight="700">6</text>
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
