export type Continent = "亞洲" | "歐洲" | "北美洲" | "大洋洲";

export const CONTINENTS: Continent[] = ["亞洲", "歐洲", "北美洲", "大洋洲"];

// 機場代碼 → 洲份。歐洲(含伊斯坦堡);北美洲 = 美加;大洋洲 = 澳紐;
// 其餘(日本/韓/台/中/東南亞 + 中東杜拜/馬累 + fallback)= 亞洲。
const EUROPE = new Set([
  "AMS", "ATH", "BCN", "BUD", "CDG", "CPH", "FCO", "HEL", "LHR", "LIS",
  "MAD", "MUC", "MXP", "PRG", "VIE", "ZRH", "IST",
]);
const NORTH_AMERICA = new Set(["JFK", "LAX", "SFO", "YVR"]);
const OCEANIA = new Set(["AKL", "BNE", "CHC", "MEL", "SYD"]);

export function continentOf(code: string): Continent {
  if (EUROPE.has(code)) return "歐洲";
  if (NORTH_AMERICA.has(code)) return "北美洲";
  if (OCEANIA.has(code)) return "大洋洲";
  return "亞洲";
}
