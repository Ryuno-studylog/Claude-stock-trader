"use client";
import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import Header from "@/components/Header";
import { fetchHistory } from "@/lib/api";

interface HistoryEntry {
  id: string;
  created_at: string;
  vix: number | null;
  vix_level: string;
  budget: number;
  holding_period: string;
  screened_stocks: string[];
  review_note: string;
  plan_text: string;
}

export default function HistoryPage() {
  const t = useTranslations("history");
  const [entries, setEntries] = useState<HistoryEntry[]>([]);

  useEffect(() => {
    fetchHistory().then(setEntries).catch(() => {});
  }, []);

  return (
    <div className="flex flex-col min-h-screen">
      <Header />
      <main className="max-w-4xl mx-auto w-full px-4 py-6">
        <h1 className="text-xl font-bold mb-6">{t("title")}</h1>

        {entries.length === 0 ? (
          <p className="text-gray-500">{t("empty")}</p>
        ) : (
          <div className="space-y-4">
            {entries.map(e => (
              <details key={e.id} className="bg-gray-900 border border-gray-800 rounded-xl">
                <summary className="cursor-pointer px-5 py-4 list-none flex flex-wrap items-center gap-3 text-sm">
                  <span className="font-medium">{e.created_at.slice(0, 16).replace("T", " ")}</span>
                  {e.vix && <span className="text-gray-400">{t("vix")} {e.vix}</span>}
                  <span className="text-gray-400">{t("budget")} ¥{e.budget.toLocaleString()}</span>
                  {e.screened_stocks?.length > 0 && (
                    <span className="text-gray-500 text-xs">{t("stocks")}: {e.screened_stocks.join(", ")}</span>
                  )}
                </summary>
                <div className="px-5 pb-5 border-t border-gray-800 mt-2 pt-4">
                  {e.review_note && (
                    <p className="text-sm text-gray-400 mb-3 italic">{e.review_note}</p>
                  )}
                  <div className="whitespace-pre-wrap text-sm text-gray-200 leading-relaxed">
                    {e.plan_text}
                  </div>
                </div>
              </details>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
