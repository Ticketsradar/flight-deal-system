// 全頁背景場景:真·免費授權風景相(Wikimedia Commons),漸變做 fallback(相未 load 都靚)。
export interface Scene {
  name: string;
  img: string;
  css: string;
}

export const SCENES: Scene[] = [
  {
    name: "Petra · 約旦",
    img: "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e8/Al_Deir_Petra.JPG/1920px-Al_Deir_Petra.JPG",
    css: "linear-gradient(135deg,#7c2d12,#c2410c,#f59e0b)",
  },
  {
    name: "Rainbow Mountain · 秘魯",
    img: "https://upload.wikimedia.org/wikipedia/commons/thumb/2/24/Monta%C3%B1aarcoirisperuabanto.jpg/1920px-Monta%C3%B1aarcoirisperuabanto.jpg",
    css: "linear-gradient(135deg,#6d28d9,#db2777,#f59e0b)",
  },
  {
    name: "K2 · 巴基斯坦",
    img: "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c9/Chogori.jpg/1280px-Chogori.jpg",
    css: "linear-gradient(135deg,#0c4a6e,#0e7490,#bae6fd)",
  },
  {
    name: "Moraine Lake · 加拿大",
    img: "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c5/Moraine_Lake_17092005.jpg/1280px-Moraine_Lake_17092005.jpg",
    css: "linear-gradient(135deg,#064e3b,#0d9488,#67e8f9)",
  },
  {
    name: "張掖丹霞 · 中國",
    img: "https://upload.wikimedia.org/wikipedia/commons/thumb/7/74/Zhangye_National_Geopark_5.jpg/1920px-Zhangye_National_Geopark_5.jpg",
    css: "linear-gradient(135deg,#9a3412,#b91c1c,#f59e0b)",
  },
  {
    name: "Salar de Uyuni · 玻利維亞",
    img: "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4a/Salar_Uyuni_au01.jpg/1920px-Salar_Uyuni_au01.jpg",
    css: "linear-gradient(135deg,#1e3a8a,#6366f1,#e0e7ff)",
  },
  {
    name: "Cappadocia · 土耳其",
    img: "https://upload.wikimedia.org/wikipedia/commons/thumb/5/59/Cappadocia_balloon_trip%2C_Ortahisar_Castle_%2811893715185%29.jpg/1920px-Cappadocia_balloon_trip%2C_Ortahisar_Castle_%2811893715185%29.jpg",
    css: "linear-gradient(135deg,#7c2d12,#be123c,#fbbf24)",
  },
  {
    name: "Lofoten · 挪威",
    img: "https://upload.wikimedia.org/wikipedia/commons/thumb/5/59/Moskenes_Reinebringen_lub_2025-07-21_img09_Aussicht.jpg/1280px-Moskenes_Reinebringen_lub_2025-07-21_img09_Aussicht.jpg",
    css: "linear-gradient(135deg,#0f172a,#1e40af,#38bdf8)",
  },
  {
    name: "富士山 · 日本",
    img: "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f8/View_of_Mount_Fuji_from_%C5%8Cwakudani_20211202.jpg/1920px-View_of_Mount_Fuji_from_%C5%8Cwakudani_20211202.jpg",
    css: "linear-gradient(135deg,#1e3a8a,#3b82f6,#e0f2fe)",
  },
];
