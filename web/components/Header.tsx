export default function Header({ meta }: { meta: Record<string, string> }) {
  const updated = meta.last_updated_stream_a || meta.last_updated_stream_b || "";
  return (
    <header className="text-center py-10 px-4">
      <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight drop-shadow">
        平機票 ✈️ 雷達
      </h1>
      <p className="mt-3 text-base md:text-lg opacity-85">
        香港 · 深圳 · 廣州 出發 — 自動掃平價 + 偵測錯價
      </p>
      {updated && (
        <p className="mt-2 text-xs opacity-60">最後更新:{updated}</p>
      )}
    </header>
  );
}
