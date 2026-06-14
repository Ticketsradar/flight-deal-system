// 機場代碼 → 國家 / 城市 / 國旗(畀卡片標籤用)。涵蓋 routes.yaml 全部目的地 + 3 個出發地。
export interface AirportInfo {
  city: string;
  country: string;
  flag: string;
}

export const AIRPORTS: Record<string, AirportInfo> = {
  // 出發地
  HKG: { city: "香港", country: "香港", flag: "🇭🇰" },
  SZX: { city: "深圳", country: "中國", flag: "🇨🇳" },
  CAN: { city: "廣州", country: "中國", flag: "🇨🇳" },
  // 日本
  CTS: { city: "札幌", country: "日本", flag: "🇯🇵" },
  FUK: { city: "福岡", country: "日本", flag: "🇯🇵" },
  HIJ: { city: "廣島", country: "日本", flag: "🇯🇵" },
  ISG: { city: "石垣", country: "日本", flag: "🇯🇵" },
  KIX: { city: "大阪", country: "日本", flag: "🇯🇵" },
  NGO: { city: "名古屋", country: "日本", flag: "🇯🇵" },
  NRT: { city: "東京", country: "日本", flag: "🇯🇵" },
  OKA: { city: "沖繩", country: "日本", flag: "🇯🇵" },
  SDJ: { city: "仙台", country: "日本", flag: "🇯🇵" },
  TAK: { city: "高松", country: "日本", flag: "🇯🇵" },
  // 東北亞
  CJU: { city: "濟州", country: "南韓", flag: "🇰🇷" },
  ICN: { city: "首爾", country: "南韓", flag: "🇰🇷" },
  KHH: { city: "高雄", country: "台灣", flag: "🇹🇼" },
  PEK: { city: "北京", country: "中國", flag: "🇨🇳" },
  PUS: { city: "釜山", country: "南韓", flag: "🇰🇷" },
  PVG: { city: "上海", country: "中國", flag: "🇨🇳" },
  TPE: { city: "台北", country: "台灣", flag: "🇹🇼" },
  // 東南亞
  BKK: { city: "曼谷", country: "泰國", flag: "🇹🇭" },
  CEB: { city: "宿霧", country: "菲律賓", flag: "🇵🇭" },
  CNX: { city: "清邁", country: "泰國", flag: "🇹🇭" },
  DAD: { city: "峴港", country: "越南", flag: "🇻🇳" },
  DPS: { city: "峇里", country: "印尼", flag: "🇮🇩" },
  HAN: { city: "河內", country: "越南", flag: "🇻🇳" },
  HKT: { city: "布吉", country: "泰國", flag: "🇹🇭" },
  KUL: { city: "吉隆坡", country: "馬來西亞", flag: "🇲🇾" },
  MNL: { city: "馬尼拉", country: "菲律賓", flag: "🇵🇭" },
  PEN: { city: "檳城", country: "馬來西亞", flag: "🇲🇾" },
  SGN: { city: "胡志明市", country: "越南", flag: "🇻🇳" },
  SIN: { city: "新加坡", country: "新加坡", flag: "🇸🇬" },
  // 南亞中東
  DXB: { city: "杜拜", country: "阿聯酋", flag: "🇦🇪" },
  IST: { city: "伊斯坦堡", country: "土耳其", flag: "🇹🇷" },
  MLE: { city: "馬累", country: "馬爾代夫", flag: "🇲🇻" },
  // 歐洲
  AMS: { city: "阿姆斯特丹", country: "荷蘭", flag: "🇳🇱" },
  ATH: { city: "雅典", country: "希臘", flag: "🇬🇷" },
  BCN: { city: "巴塞隆拿", country: "西班牙", flag: "🇪🇸" },
  BUD: { city: "布達佩斯", country: "匈牙利", flag: "🇭🇺" },
  CDG: { city: "巴黎", country: "法國", flag: "🇫🇷" },
  CPH: { city: "哥本哈根", country: "丹麥", flag: "🇩🇰" },
  FCO: { city: "羅馬", country: "意大利", flag: "🇮🇹" },
  HEL: { city: "赫爾辛基", country: "芬蘭", flag: "🇫🇮" },
  LHR: { city: "倫敦", country: "英國", flag: "🇬🇧" },
  LIS: { city: "里斯本", country: "葡萄牙", flag: "🇵🇹" },
  MAD: { city: "馬德里", country: "西班牙", flag: "🇪🇸" },
  MUC: { city: "慕尼黑", country: "德國", flag: "🇩🇪" },
  MXP: { city: "米蘭", country: "意大利", flag: "🇮🇹" },
  PRG: { city: "布拉格", country: "捷克", flag: "🇨🇿" },
  VIE: { city: "維也納", country: "奧地利", flag: "🇦🇹" },
  ZRH: { city: "蘇黎世", country: "瑞士", flag: "🇨🇭" },
  // 美加澳紐
  AKL: { city: "奧克蘭", country: "紐西蘭", flag: "🇳🇿" },
  BNE: { city: "布里斯本", country: "澳洲", flag: "🇦🇺" },
  CHC: { city: "基督城", country: "紐西蘭", flag: "🇳🇿" },
  JFK: { city: "紐約", country: "美國", flag: "🇺🇸" },
  LAX: { city: "洛杉磯", country: "美國", flag: "🇺🇸" },
  MEL: { city: "墨爾本", country: "澳洲", flag: "🇦🇺" },
  SFO: { city: "三藩市", country: "美國", flag: "🇺🇸" },
  SYD: { city: "悉尼", country: "澳洲", flag: "🇦🇺" },
  YVR: { city: "溫哥華", country: "加拿大", flag: "🇨🇦" },
};

export function airportInfo(code: string): AirportInfo {
  return AIRPORTS[code] ?? { city: code, country: "", flag: "✈️" };
}

export const ORIGINS: { code: string; name: string }[] = [
  { code: "HKG", name: "香港" },
  { code: "SZX", name: "深圳" },
  { code: "CAN", name: "廣州" },
];
