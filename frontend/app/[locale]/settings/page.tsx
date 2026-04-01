"use client";
import { useEffect, useState } from "react";
import { useTranslations, useLocale } from "next-intl";
import { useRouter, useSearchParams } from "next/navigation";
import Header from "@/components/Header";
import { fetchUserSettings, saveUserSettings, createCheckout, fetchBillingPortal, fetchProfile } from "@/lib/api";

const CREDITS_PRICE_ID = process.env.NEXT_PUBLIC_STRIPE_CREDITS_PRICE_ID ?? "";
const MONTHLY_PRICE_ID = process.env.NEXT_PUBLIC_STRIPE_MONTHLY_PRICE_ID ?? "";

interface StockEntry { 証券コード: string; ticker: string; 銘柄名: string; セクター: string; }

export default function SettingsPage() {
  const t      = useTranslations("settings");
  const locale = useLocale();
  const router       = useRouter();
  const searchParams = useSearchParams();

  const [checkoutSuccess, setCheckoutSuccess] = useState(false);
  const [profile,    setProfile]    = useState<{ credits: number; plan: string } | null>(null);
  const [universe,   setUniverse]   = useState<StockEntry[]>([]);
  const [minVol,     setMinVol]     = useState(2000);
  const [maxAtr,     setMaxAtr]     = useState(4.0);
  const [trend,      setTrend]      = useState("any");
  const [budget,     setBudget]     = useState(100000);
  const [saved,      setSaved]      = useState(false);
  const [buying,     setBuying]     = useState(false);
  const [portaling,  setPortaling]  = useState(false);

  useEffect(() => {
    if (searchParams.get("checkout") === "success") {
      setCheckoutSuccess(true);
      // URLからクエリパラメータを消す
      router.replace(`/${locale}/settings`);
    }
    fetchProfile().then(setProfile).catch(() => {});
    fetchUserSettings().then((s: { stock_universe?: StockEntry[]; screening_defaults?: { min_volume_k: number; max_atr_pct: number; trend: string }; plan_defaults?: { budget: number } }) => {
      if (s.stock_universe)     setUniverse(s.stock_universe);
      if (s.screening_defaults) {
        setMinVol(s.screening_defaults.min_volume_k);
        setMaxAtr(s.screening_defaults.max_atr_pct);
        setTrend(s.screening_defaults.trend);
      }
      if (s.plan_defaults) setBudget(s.plan_defaults.budget);
    }).catch(() => {});
  }, []);

  const save = async () => {
    await saveUserSettings({
      stock_universe: universe.filter(s => s.ticker && s.銘柄名),
      screening_defaults: { min_volume_k: minVol, max_atr_pct: maxAtr, trend },
      plan_defaults: { budget },
    });
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const addRow = () => setUniverse(u => [...u, { 証券コード: "", ticker: "", 銘柄名: "", セクター: "" }]);
  const removeRow = (i: number) => setUniverse(u => u.filter((_, idx) => idx !== i));
  const updateRow = (i: number, field: keyof StockEntry, val: string) =>
    setUniverse(u => u.map((r, idx) => idx === i ? { ...r, [field]: val } : r));

  const checkout = async (priceId: string) => {
    setBuying(true);
    try {
      const { url } = await createCheckout(priceId);
      window.location.href = url;
    } catch (e: unknown) {
      alert("Checkout failed: " + (e instanceof Error ? e.message : String(e)));
    } finally {
      setBuying(false);
    }
  };

  const openPortal = async () => {
    setPortaling(true);
    try {
      const { url } = await fetchBillingPortal();
      window.location.href = url;
    } catch {
      alert("Could not open billing portal. Please try again.");
    } finally {
      setPortaling(false);
    }
  };

  return (
    <div className="flex flex-col min-h-screen">
      <Header />
      <main className="max-w-4xl mx-auto w-full px-4 py-6 space-y-8">
        <h1 className="text-xl font-bold">{t("title")}</h1>

        {checkoutSuccess && (
          <div className="bg-green-900 border border-green-700 text-green-200 rounded-lg px-4 py-3 text-sm">
            {locale === "ja" ? "決済が完了しました。ご購入ありがとうございます！" : "Payment successful! Thank you for your purchase."}
          </div>
        )}

        {/* 課金 */}
        {profile && (
          <section id="billing" className="bg-gray-900 border border-gray-800 rounded-xl p-5">
            <h2 className="font-semibold mb-3">Plan</h2>
            <p className="text-sm text-gray-400 mb-4">
              {profile.plan === "monthly"
                ? "Monthly plan — 3 runs/day"
                : `${profile.credits} credits remaining`}
            </p>
            <div className="flex gap-3 flex-wrap">
              {profile.plan === "monthly" ? (
                <button disabled={portaling} onClick={openPortal}
                  className="bg-gray-800 hover:bg-gray-700 disabled:opacity-50 rounded-lg px-4 py-2 text-sm transition">
                  {portaling ? "Redirecting..." : "Manage / Cancel subscription"}
                </button>
              ) : (
                <>
                  <button disabled={buying} onClick={() => checkout(CREDITS_PRICE_ID)}
                    className="bg-gray-800 hover:bg-gray-700 disabled:opacity-50 rounded-lg px-4 py-2 text-sm transition">
                    Buy Credits ($1 / 3 runs)
                  </button>
                  <button disabled={buying} onClick={() => checkout(MONTHLY_PRICE_ID)}
                    className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 rounded-lg px-4 py-2 text-sm transition">
                    Go Monthly ($6/mo)
                  </button>
                </>
              )}
            </div>
          </section>
        )}

        {/* 銘柄ユニバース */}
        <section className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h2 className="font-semibold mb-1">{t("universe.title")}</h2>
          <p className="text-xs text-gray-500 mb-4">{t("universe.desc")}</p>
          <div className="overflow-x-auto">
            <table className="w-full text-xs border-collapse">
              <thead>
                <tr className="text-gray-400 border-b border-gray-700">
                  <th className="text-left py-2 pr-3">{t("universe.code")}</th>
                  <th className="text-left py-2 pr-3">{t("universe.ticker")}</th>
                  <th className="text-left py-2 pr-3">{t("universe.name")}</th>
                  <th className="text-left py-2 pr-3">{t("universe.sector")}</th>
                  <th className="py-2" />
                </tr>
              </thead>
              <tbody>
                {universe.map((row, i) => (
                  <tr key={i} className="border-b border-gray-800">
                    {(["証券コード","ticker","銘柄名","セクター"] as const).map(f => (
                      <td key={f} className="py-1.5 pr-3">
                        <input value={row[f]} onChange={e => updateRow(i, f, e.target.value)}
                          className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1 focus:outline-none focus:border-indigo-500" />
                      </td>
                    ))}
                    <td className="py-1.5">
                      <button onClick={() => removeRow(i)} className="text-red-500 hover:text-red-400 px-2">✕</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <button onClick={addRow} className="mt-3 text-xs text-indigo-400 hover:underline">
            + {t("universe.add")}
          </button>
        </section>

        {/* スクリーニングデフォルト */}
        <section className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h2 className="font-semibold mb-4">{t("screening.title")}</h2>
          <div className="grid sm:grid-cols-3 gap-4">
            <label className="block">
              <span className="text-xs text-gray-400">Min volume (k)</span>
              <input type="number" value={minVol} onChange={e => setMinVol(+e.target.value)} step={500}
                className="mt-1 w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm" />
            </label>
            <label className="block">
              <span className="text-xs text-gray-400">Max ATR14 (%)</span>
              <input type="number" value={maxAtr} onChange={e => setMaxAtr(+e.target.value)} step={0.5} min={1} max={8}
                className="mt-1 w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm" />
            </label>
            <label className="block">
              <span className="text-xs text-gray-400">Trend</span>
              <select value={trend} onChange={e => setTrend(e.target.value)}
                className="mt-1 w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm">
                {["any","uptrend","downtrend"].map(v => <option key={v} value={v}>{v}</option>)}
              </select>
            </label>
          </div>
        </section>

        {/* 保存ボタン */}
        <button onClick={save}
          className="w-full bg-indigo-600 hover:bg-indigo-500 rounded-lg py-2.5 text-sm font-medium transition">
          {saved ? t("saved") : t("save")}
        </button>
      </main>
    </div>
  );
}
