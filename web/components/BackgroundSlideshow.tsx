"use client";

import { useEffect, useState } from "react";
import { SCENES } from "@/lib/backgrounds";

// 全頁背景:每 12 秒慢慢 cross-fade 去下一張風景相 + scrim 暗化保證文字讀到。
// 每層 background = 真相疊喺漸變之上;相 load 唔到就自動見到漸變 fallback。
export default function BackgroundSlideshow() {
  const [i, setI] = useState(0);

  useEffect(() => {
    const t = setInterval(() => setI((p) => (p + 1) % SCENES.length), 12000);
    return () => clearInterval(t);
  }, []);

  return (
    <div aria-hidden className="fixed inset-0 -z-10 overflow-hidden">
      {SCENES.map((s, idx) => (
        <div
          key={s.name}
          className="absolute inset-0 bg-cover bg-center transition-opacity ease-in-out"
          style={{
            backgroundImage: `url("${s.img}"), ${s.css}`,
            opacity: idx === i ? 1 : 0,
            transitionDuration: "2500ms",
          }}
        />
      ))}
      {/* scrim:壓暗背景,玻璃卡上嘅白字先清楚 */}
      <div className="absolute inset-0 bg-slate-950/55" />
      <div className="absolute bottom-2 right-3 text-[10px] tracking-wide text-white/55">
        {SCENES[i].name} · 圖 Wikimedia Commons
      </div>
    </div>
  );
}
