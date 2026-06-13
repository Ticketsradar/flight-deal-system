export default function TelegramCTA() {
  return (
    <a
      href="https://t.me/hkgcheapflightscannerbot"
      target="_blank"
      rel="noopener noreferrer"
      className="glass rounded-xl p-4 flex items-center gap-3 hover:border-white/30 transition"
    >
      <span className="text-2xl">📣</span>
      <div className="min-w-0">
        <div className="font-semibold">Telegram 即時錯價提示</div>
        <div className="text-xs opacity-75">偵測到錯價即刻彈手機,唔使成日 refresh</div>
      </div>
      <span className="ml-auto link-pill whitespace-nowrap">加入 ↗</span>
    </a>
  );
}
