import { describe, it, expect } from "vitest";
import { AIRPORTS } from "@/lib/airports";
import { CONTINENTS, continentOf } from "@/lib/continents";

describe("continents", () => {
  it("has exactly the 4 expected continents", () => {
    expect(CONTINENTS).toEqual(["亞洲", "歐洲", "美洲", "大洋洲"]);
  });

  it("maps every airport in AIRPORTS to one of the 4 continents", () => {
    for (const code of Object.keys(AIRPORTS)) {
      expect(CONTINENTS).toContain(continentOf(code));
    }
  });

  it("places key edge cases correctly", () => {
    expect(continentOf("IST")).toBe("歐洲"); // 伊斯坦堡
    expect(continentOf("DXB")).toBe("亞洲"); // 杜拜
    expect(continentOf("MLE")).toBe("亞洲"); // 馬累
    expect(continentOf("NRT")).toBe("亞洲"); // 東京
    expect(continentOf("LHR")).toBe("歐洲"); // 倫敦
    expect(continentOf("JFK")).toBe("美洲"); // 紐約
    expect(continentOf("YVR")).toBe("美洲"); // 溫哥華
    expect(continentOf("SYD")).toBe("大洋洲"); // 悉尼
    expect(continentOf("AKL")).toBe("大洋洲"); // 奧克蘭
  });

  it("falls back to 亞洲 for unknown codes", () => {
    expect(continentOf("ZZZ")).toBe("亞洲");
  });
});
