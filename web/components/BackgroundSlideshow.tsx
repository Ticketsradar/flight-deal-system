"use client";

import { useEffect, useState } from "react";
import { SCENES } from "@/lib/backgrounds";

// 全頁背景:每張慢慢 zoom + 12 秒後 cross-fade 去「隨機」另一張。scrim 暗化保證文字讀到。
export default function BackgroundSlideshow() {
  const [i, setI] = useState(0);

  useEffect(() => {
    setI(Math.floor(Math.random() * SCENES.length)); // 隨機起始
    const t = setInterval(() => {
      setI((prev) => {
        if (SCENES.length <= 1) return prev;
        let n = prev;
        while (n === prev) n = Math.floor(Math.random() * SCENES.length); // 隨機下一張,唔即時重複
        return n;
      });
    }, 12000);
    return () => clearInterval(t);
  }, []);

  return (
    <div aria-hidden className="fixed inset-0 -z-10 overflow-hidden">
      {SCENES.map((s, idx) => (
        <div
          key={s.name}
          className="absolute inset-0 transition-opacity ease-in-out"
          style={{ opacity: idx === i ? 1 : 0, transitionDuration: "2500ms" }}
        >
          <div
            className="absolute inset-0 bg-cover bg-center kenburns"
            style={{ backgroundImage: `url("${s.img}"), ${s.css}` }}
          />
        </div>
      ))}
      {/* scrim:壓暗背景,玻璃卡上嘅白字先清楚 */}
      <div className="absolute inset-0 bg-slate-950/55" />
      <div className="absolute bottom-2 right-3 text-[10px] tracking-wide text-white/55">
        {SCENES[i].name} · 圖 Wikimedia Commons
      </div>
    </div>
  );
}
