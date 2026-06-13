import { getFacets } from "@/lib/data";
import type { Filters as F } from "@/lib/types";

// 純 form(method=get)→ 提交即改 URL searchParams → 頁面 server-side 重新篩選。零 client JS。
export default async function Filters({ current }: { current: F }) {
  const { origins, regions, months } = await getFacets();
  return (
    <form method="get" className="glass rounded-xl p-3 flex flex-wrap gap-3 items-end text-sm">
      <label className="flex flex-col gap-1">
        <span className="opacity-70 text-xs">出發地</span>
        <select name="origin" defaultValue={current.origin ?? ""} className="filter-input">
          <option value="">全部</option>
          {origins.map((o) => (
            <option key={o} value={o}>
              {o}
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
        <span className="opacity-70 text-xs">月份</span>
        <select name="month" defaultValue={current.month ?? ""} className="filter-input">
          <option value="">全部</option>
          {months.map((m) => (
            <option key={m} value={m}>
              {m}
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
