"use client";
import { useState, useEffect, useRef } from "react";
import { useTranslations, useLocale } from "next-intl";
import { useRouter } from "next/navigation";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import Header from "@/components/Header";
import { fetchSafety, fetchScreen, streamPlan, fetchProfile } from "@/lib/api";
import { supabase } from "@/lib/supabase";

// VIXバナーの色
const LEVEL_STYLES: Record<string, string> = {
  safe:    "bg-green-900 border-green-700 text-green-200",
  caution: "bg-yellow-900 border-yellow-700 text-yellow-200",
  warning: "bg-orange-900 border-orange-700 text-orange-200",
  danger:  "bg-red-900   border-red-700   text-red-200",
  unknown: "bg-gray-800  border-gray-700  text-gray-400",
};

// セクション別の左ボーダー色（AIの出力の見出しに使う）
const SECTION_BORDER: Record<string, string> = {
  "📋": "border-blue-500",
  "🌡️": "border-yellow-500",
  "🎯": "border-green-500",
  "⚠️": "border-orange-500",
};

// ──────────────── ツールチップ ────────────────
function Tooltip({ tip, children }: { tip: string; children: React.ReactNode }) {
  return (
    <span className="group relative inline-flex items-center gap-1 cursor-help">
      {children}
      <span className="text-gray-500 text-xs">?</span>
      <span className="pointer-events-none absolute hidden group-hover:block bottom-full left-1/2 -translate-x-1/2 mb-1.5 w-56 bg-gray-700 border border-gray-600 text-gray-200 text-xs rounded-lg px-2.5 py-2 z-20 leading-relaxed shadow-xl text-center">
        {tip}
      </span>
    </span>
  );
}

// ──────────────── AIプランの Markdown レンダラー ────────────────
function PlanOutput({ text }: { text: string }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        h3: ({ children }) => {
          const raw = String(children);
          const emoji = raw.match(/^(📋|🌡️|🎯|⚠️)/)?.[0] ?? "";
          const border = SECTION_BORDER[emoji] ?? "border-gray-600";
          return (
            <div className={`mt-5 mb-2 border-l-4 pl-3 ${border}`}>
              <h3 className="text-sm font-bold text-gray-100">{children}</h3>
            </div>
          );
        },
        h4: ({ children }) => (
          <h4 className="text-sm font-semibold text-gray-200 mt-3 mb-1">{children}</h4>
        ),
        strong: ({ children }) => (
          <strong className="font-semibold text-white">{children}</strong>
        ),
        p: ({ children }) => (
          <p className="text-sm text-gray-300 my-1 leading-relaxed">{children}</p>
        ),
        ul: ({ children }) => (
          <ul className="list-disc ml-5 space-y-0.5 my-1">{children}</ul>
        ),
        ol: ({ children }) => (
          <ol className="list-decimal ml-5 space-y-0.5 my-1">{children}</ol>
        ),
        li: ({ children }) => (
          <li className="text-sm text-gray-300">{children}</li>
        ),
        hr: () => <hr className="border-gray-700 my-3" />,
        blockquote: ({ children }) => (
          <blockquote className="border-l-2 border-gray-600 pl-3 text-gray-400 italic text-sm my-2">{children}</blockquote>
        ),
      }}
    >
      {text}
    </ReactMarkdown>
  );
}

export default function DashboardPage() {
  const t      = useTranslations("dashboard");
  const tl     = useTranslations("landing");
  const tg     = useTranslations("glossary");
  const locale = useLocale();
  const router = useRouter();

  const [authed,    setAuthed]    = useState<boolean | null>(null);
  const [profile,   setProfile]   = useState<{ credits: number; plan: string; language: string } | null>(null);
  const [safety,    setSafety]    = useState<{ level: string; message: string; vix: number | null } | null>(null);
  const [stocks,    setStocks]    = useState<object[] | null>(null);
  const [screening,   setScreening]   = useState(false);
  const [screenError, setScreenError] = useState("");
  const [showVixGuide,   setShowVixGuide]   = useState(false);
  const [showGlossary,   setShowGlossary]   = useState(false);

  // スクリーニング設定
  const [minVol, setMinVol] = useState(2000);
  const [maxAtr, setMaxAtr] = useState(4.0);
  const [trend,  setTrend]  = useState("any");

  // プランフォーム
  const [budget,        setBudget]        = useState(100000);
  const [holdingPeriod, setHoldingPeriod] = useState("period_week");
  const [risk,          setRisk]          = useState("risk_mid");
  const [review,        setReview]        = useState("");

  // 生成
  const [generating, setGenerating] = useState(false);
  const [planText,   setPlanText]   = useState("");
  const planRef = useRef<HTMLDivElement>(null);

  // 認証チェック
  useEffect(() => {
    supabase.auth.getUser().then(({ data }) => {
      setAuthed(!!data.user);
      if (data.user) {
        fetchProfile().then(setProfile).catch(() => {});
        fetchSafety().then(setSafety).catch(() => {});
      }
    });
  }, []);

  if (authed === null) return null;
  if (!authed) return <LandingPage locale={locale} tl={tl} />;

  const runScreening = async () => {
    setScreening(true);
    setStocks(null);
    setScreenError("");
    try {
      const res = await fetchScreen({ min_volume_k: minVol, max_atr_pct: maxAtr, trend });
      setStocks(res.stocks);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setScreenError(msg);
      setStocks([]);
    } finally {
      setScreening(false);
    }
  };

  const generate = async () => {
    if (!stocks || stocks.length === 0 || !safety) return;
    setPlanText("");
    setGenerating(true);
    planRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    try {
      const req = {
        budget,
        holding_period: t(`plan_form.${holdingPeriod}`),
        risk_tolerance: t(`plan_form.${risk}`),
        review_note: review,
        watchlist: stocks,
        vix_info: safety,
        language: locale === "ja" ? "ja" : "en",
      };
      for await (const chunk of streamPlan(req)) {
        setPlanText(p => p + chunk);
      }
      fetchProfile().then(setProfile).catch(() => {});
    } catch (e: unknown) {
      if (e instanceof Error) {
        if (e.message.includes("402")) {
          alert(locale === "ja" ? "クレジットが不足しています" : "Insufficient credits");
          router.push(`/${locale}/settings`);
        } else if (e.message.includes("429")) {
          alert(locale === "ja" ? "本日の利用上限（3回）に達しました。明日またお試しください。" : "Daily limit reached (3 runs/day). Please try again tomorrow.");
        }
      }
    } finally {
      setGenerating(false);
    }
  };

  // テーブルのカラム定義（ラベルとツールチップキー）
  const columns = [
    { key: "code",       tipKey: "col_code" },
    { key: "name",       tipKey: "col_name" },
    { key: "sector",     tipKey: "col_sector" },
    { key: "price",      tipKey: "col_price" },
    { key: "day_change", tipKey: "col_day_change" },
    { key: "avg_vol_k",  tipKey: "col_avg_vol" },
    { key: "atr14_pct",  tipKey: "col_atr14" },
    { key: "ma25_diff",  tipKey: "col_ma25" },
    { key: "range_pos",  tipKey: "col_range" },
  ] as const;

  return (
    <div className="flex flex-col min-h-screen">
      <Header />
      <main className="flex-1 max-w-5xl mx-auto w-full px-4 py-6 space-y-6">

        {/* クレジット表示 */}
        {profile && profile.plan !== "monthly" && (
          <div className="flex justify-end">
            <span className="text-sm text-gray-400">
              {t("credits.remaining", { count: profile.credits })}
              {profile.credits < 2 && (
                <button
                  onClick={() => router.push(`/${locale}/settings#billing`)}
                  className="ml-2 text-indigo-400 hover:underline text-xs"
                >
                  {t("credits.buy")}
                </button>
              )}
            </span>
          </div>
        )}

        {/* VIXバナー + 解説 */}
        {safety && (
          <div>
            <div className={`border rounded-lg px-4 py-3 text-sm flex items-center justify-between ${LEVEL_STYLES[safety.level] ?? LEVEL_STYLES.unknown}`}>
              <div>
                <span className="font-semibold mr-2">{t(`safety.${safety.level}`)}</span>
                {safety.message}
              </div>
              <button
                onClick={() => setShowVixGuide(v => !v)}
                className="ml-3 shrink-0 text-xs underline opacity-70 hover:opacity-100"
              >
                {showVixGuide ? tg("hide") : tg("vix_what")}
              </button>
            </div>
            {showVixGuide && (
              <div className="mt-2 bg-gray-900 border border-gray-800 rounded-lg p-4 text-sm space-y-2">
                <p className="font-semibold text-gray-200">{tg("vix_title")}</p>
                <p className="text-gray-400 text-xs">{tg("vix_desc")}</p>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-2">
                  {(["safe","caution","warning","danger"] as const).map(lv => (
                    <div key={lv} className={`rounded px-2 py-1.5 text-xs border ${LEVEL_STYLES[lv]}`}>
                      <div className="font-semibold mb-0.5">{tg(`vix_${lv}_label`)}</div>
                      <div className="opacity-80">{tg(`vix_${lv}_desc`)}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* スクリーニング */}
        <section className="bg-gray-900 rounded-xl border border-gray-800 p-5">
          <h2 className="font-semibold mb-1">{t("screening.title")}</h2>
          <p className="text-xs text-gray-500 mb-4">{tg("screening_desc")}</p>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-4">
            <label className="block">
              <Tooltip tip={tg("col_avg_vol")}>
                <span className="text-xs text-gray-400">{t("screening.min_volume")}</span>
              </Tooltip>
              <input type="number" value={minVol} onChange={e => setMinVol(+e.target.value)} step={500}
                className="mt-1 w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm" />
            </label>
            <label className="block">
              <Tooltip tip={tg("col_atr14")}>
                <span className="text-xs text-gray-400">{t("screening.max_atr")}</span>
              </Tooltip>
              <input type="number" value={maxAtr} onChange={e => setMaxAtr(+e.target.value)} step={0.5} min={1} max={8}
                className="mt-1 w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm" />
            </label>
            <label className="block">
              <Tooltip tip={tg("col_ma25")}>
                <span className="text-xs text-gray-400">{t("screening.trend")}</span>
              </Tooltip>
              <select value={trend} onChange={e => setTrend(e.target.value)}
                className="mt-1 w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm">
                {["any", "uptrend", "downtrend"].map(v => (
                  <option key={v} value={v}>{t(`screening.trend_${v === "any" ? "any" : v === "uptrend" ? "up" : "down"}`)}</option>
                ))}
              </select>
            </label>
          </div>

          <button onClick={runScreening} disabled={screening}
            className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 rounded-lg px-4 py-2 text-sm font-medium transition">
            {screening ? t("screening.running") : t("screening.run")}
          </button>

          {screenError && (
            <p className="mt-4 text-sm text-red-400 break-all">Error: {screenError}</p>
          )}

          {stocks !== null && (
            stocks.length === 0
              ? <p className="mt-4 text-sm text-gray-500">{t("screening.no_result")}</p>
              : (
                <div className="mt-4">
                  <p className="text-xs text-gray-500 mb-2">{t("screening.result", { count: stocks.length })}</p>
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs text-left border-collapse">
                      <thead>
                        <tr className="border-b border-gray-700 text-gray-400">
                          {columns.map(({ key, tipKey }) => (
                            <th key={key} className="py-2 pr-4 whitespace-nowrap font-medium">
                              <Tooltip tip={tg(tipKey)}>{key}</Tooltip>
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {(stocks as Record<string, unknown>[]).map((s, i) => (
                          <tr key={i} className="border-b border-gray-800 hover:bg-gray-800/50">
                            <td className="py-2 pr-4">{String(s.code)}</td>
                            <td className="py-2 pr-4 whitespace-nowrap">{String(s.name)}</td>
                            <td className="py-2 pr-4 text-gray-400">{String(s.sector)}</td>
                            <td className="py-2 pr-4">¥{Number(s.price).toLocaleString()}</td>
                            <td className={`py-2 pr-4 ${Number(s.day_change) >= 0 ? "text-green-400" : "text-red-400"}`}>
                              {Number(s.day_change) >= 0 ? "+" : ""}{Number(s.day_change).toFixed(1)}%
                            </td>
                            <td className="py-2 pr-4">{Number(s.avg_vol_k).toLocaleString()}</td>
                            <td className="py-2 pr-4">{Number(s.atr14_pct).toFixed(2)}%</td>
                            <td className={`py-2 pr-4 ${Number(s.ma25_diff) >= 0 ? "text-green-400" : "text-red-400"}`}>
                              {Number(s.ma25_diff) >= 0 ? "+" : ""}{Number(s.ma25_diff).toFixed(1)}%
                            </td>
                            <td className="py-2 pr-4">{Number(s.range_pos).toFixed(0)}%</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {/* 用語解説（折りたたみ） */}
                  <div className="mt-4">
                    <button
                      onClick={() => setShowGlossary(v => !v)}
                      className="text-xs text-indigo-400 hover:underline"
                    >
                      {showGlossary ? tg("hide_glossary") : tg("show_glossary")}
                    </button>
                    {showGlossary && (
                      <div className="mt-3 grid sm:grid-cols-2 gap-3">
                        {(["atr14","ma25","range","vol","day_change_g"] as const).map(k => (
                          <div key={k} className="bg-gray-800 rounded-lg p-3 border border-gray-700">
                            <p className="font-semibold text-xs text-gray-200 mb-1">{tg(`term_${k}_label`)}</p>
                            <p className="text-xs text-gray-400 leading-relaxed">{tg(`term_${k}_desc`)}</p>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )
          )}
        </section>

        {/* 計画生成フォーム */}
        <section className="bg-gray-900 rounded-xl border border-gray-800 p-5">
          <h2 className="font-semibold mb-1">{t("plan_form.title")}</h2>
          <p className="text-xs text-gray-500 mb-4">{tg("plan_desc")}</p>
          <div className="space-y-4">
            <label className="block">
              <span className="text-xs text-gray-400">{t("plan_form.review")}</span>
              <textarea rows={3} value={review} onChange={e => setReview(e.target.value)}
                placeholder={t("plan_form.review_placeholder")}
                className="mt-1 w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm resize-none" />
            </label>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <label className="block">
                <span className="text-xs text-gray-400">{t("plan_form.budget")}</span>
                <input type="number" value={budget} onChange={e => setBudget(+e.target.value)} step={10000}
                  className="mt-1 w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm" />
              </label>
              <label className="block">
                <span className="text-xs text-gray-400">{t("plan_form.period")}</span>
                <select value={holdingPeriod} onChange={e => setHoldingPeriod(e.target.value)}
                  className="mt-1 w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm">
                  {["period_week", "period_month", "period_day"].map(v => (
                    <option key={v} value={v}>{t(`plan_form.${v}`)}</option>
                  ))}
                </select>
              </label>
              <label className="block">
                <span className="text-xs text-gray-400">{t("plan_form.risk")}</span>
                <select value={risk} onChange={e => setRisk(e.target.value)}
                  className="mt-1 w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm">
                  {["risk_low", "risk_mid", "risk_high"].map(v => (
                    <option key={v} value={v}>{t(`plan_form.${v}`)}</option>
                  ))}
                </select>
              </label>
            </div>

            <button
              onClick={generate}
              disabled={generating || !stocks || stocks.length === 0}
              className="w-full bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 rounded-lg py-2.5 text-sm font-medium transition"
            >
              {generating ? t("plan_form.generating") : stocks === null ? t("screening.hint") : t("plan_form.submit")}
            </button>
          </div>
        </section>

        {/* 生成結果 */}
        {planText && (
          <section ref={planRef} className="bg-gray-900 rounded-xl border border-gray-800 p-5">
            <div className="flex items-center justify-between mb-3">
              <h2 className="font-semibold text-gray-100">{tg("plan_result_title")}</h2>
              <span className="text-xs text-gray-500">{tg("plan_result_note")}</span>
            </div>
            <div className="border-t border-gray-800 pt-4">
              <PlanOutput text={planText} />
            </div>
            {!generating && (
              <p className="mt-4 text-xs text-gray-600 border-t border-gray-800 pt-3">
                {tg("plan_disclaimer")}
              </p>
            )}
          </section>
        )}

      </main>
    </div>
  );
}

// ── ランディングページ（未ログイン時） ────────────────────────

function LandingPage({ locale, tl }: { locale: string; tl: ReturnType<typeof useTranslations> }) {
  const router = useRouter();

  return (
    <div className="flex flex-col min-h-screen">
      <Header />
      <main className="flex-1">
        {/* ヒーロー */}
        <section className="max-w-3xl mx-auto px-4 py-20 text-center">
          <h1 className="text-4xl sm:text-5xl font-bold leading-tight mb-5">
            {tl("headline")}
          </h1>
          <p className="text-lg text-gray-400 mb-8">{tl("subheadline")}</p>
          <button onClick={() => router.push(`/${locale}/auth`)}
            className="bg-indigo-600 hover:bg-indigo-500 text-white px-8 py-3.5 rounded-xl text-base font-semibold transition">
            {tl("cta")}
          </button>
        </section>

        {/* 特徴 */}
        <section className="max-w-4xl mx-auto px-4 pb-16 grid sm:grid-cols-3 gap-6">
          {(["screening", "safety", "plan"] as const).map(k => (
            <div key={k} className="bg-gray-900 border border-gray-800 rounded-xl p-5">
              <h3 className="font-semibold mb-2">{tl(`features.${k}.title`)}</h3>
              <p className="text-sm text-gray-400">{tl(`features.${k}.desc`)}</p>
            </div>
          ))}
        </section>

        {/* 料金 */}
        <section className="max-w-3xl mx-auto px-4 pb-20">
          <h2 className="text-2xl font-bold text-center mb-8">{tl("pricing.title")}</h2>
          <div className="grid sm:grid-cols-3 gap-5">
            {(["free", "credits", "monthly"] as const).map((k, i) => (
              <div key={k} className={`bg-gray-900 border rounded-xl p-6 text-center ${i === 2 ? "border-indigo-500" : "border-gray-800"}`}>
                <div className="text-sm text-gray-400 mb-1">{tl(`pricing.${k}.name`)}</div>
                <div className="text-3xl font-bold mb-2">{tl(`pricing.${k}.price`)}</div>
                <div className="text-xs text-gray-500 mb-5">{tl(`pricing.${k}.desc`)}</div>
                <button onClick={() => router.push(`/${locale}/auth`)}
                  className={`w-full py-2 rounded-lg text-sm font-medium transition ${i === 2 ? "bg-indigo-600 hover:bg-indigo-500" : "bg-gray-800 hover:bg-gray-700"}`}>
                  {tl("cta")}
                </button>
              </div>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}
