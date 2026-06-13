// Phase 3 checkpoint 1:用「場景漸變」做背景(每個 evoke 對應景點嘅色調),
// 100% render 到、零 broken image。下一步換成真·免費授權風景相(Unsplash/Pexels/Wikimedia)。
export interface Scene {
  name: string;
  css: string;
}

export const SCENES: Scene[] = [
  { name: "Petra · 約旦", css: "linear-gradient(135deg,#7c2d12,#c2410c,#f59e0b)" },
  { name: "Rainbow Mountain · 秘魯", css: "linear-gradient(135deg,#6d28d9,#db2777,#f59e0b)" },
  { name: "K2 · 巴基斯坦", css: "linear-gradient(135deg,#0c4a6e,#0e7490,#bae6fd)" },
  { name: "Moraine Lake · 加拿大", css: "linear-gradient(135deg,#064e3b,#0d9488,#67e8f9)" },
  { name: "張掖丹霞 · 中國", css: "linear-gradient(135deg,#9a3412,#b91c1c,#f59e0b)" },
  { name: "Salar de Uyuni · 玻利維亞", css: "linear-gradient(135deg,#1e3a8a,#6366f1,#e0e7ff)" },
  { name: "Cappadocia · 土耳其", css: "linear-gradient(135deg,#7c2d12,#be123c,#fbbf24)" },
  { name: "Lofoten · 挪威", css: "linear-gradient(135deg,#0f172a,#1e40af,#38bdf8)" },
];
