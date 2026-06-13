import { ORIGINS } from "@/lib/airports";
import type { Filters as F } from "@/lib/types";

// 純 form(method=get)→ 提交即改 URL searchParams → server 重新篩選。零 client JS。
export default function Filters({
  current,
  regions,
}: {
  current: F;
  regions: string[];
}) {
  return (
    <form method="get" className="glass rounded-xl p-3 flex flex-wrap gap-3 items-end text-sm">
      <label className="flex flex-col gap-1">
        <span className="opacity-70 text-xs">出發地</span>
        <select name="origin" defaultValue={current.origin ?? "HKG"} className="filter-input">
          {ORIGINS.map((o) => (
            <option key={o.code} value={o.code}>
              {o.name}
            </option>
          ))}
        </select>
      </label>

      <label className="flex flex-col gap-1">
        <span className="opacity-70 text-xs">地區</span>
        <select name="region" defaultValue={current.region ?? ""} className="filter-input">
          <option value="">全部</option>
          {regions.map((r) => (
            <option key={r} value={r}>
              {r}
            </option>
          ))}
        </select>
      </label>

      <label className="flex flex-col gap-1">
        <span className="opacity-70 text-xs">預算上限 (HKD)</span>
        <input
          type="number"
          name="maxPrice"
          inputMode="numeric"
          defaultValue={current.maxPrice ?? ""}
          placeholder="例:2000"
          className="filter-input w-28"
        />
      </label>

      <button type="submit" className="filter-btn">
        篩選
      </button>
      <a href="/" className="filter-reset">
        重設
      </a>
    </form>
  );
}
