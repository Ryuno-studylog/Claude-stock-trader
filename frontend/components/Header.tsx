"use client";
import { useTranslations, useLocale } from "next-intl";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { supabase } from "@/lib/supabase";
import { useEffect, useState } from "react";

export default function Header() {
  const t       = useTranslations("nav");
  const locale  = useLocale();
  const router  = useRouter();
  const path    = usePathname();
  const [user,  setUser]    = useState<{ email?: string } | null>(null);
  const [credits, setCredits] = useState<number | null>(null);

  useEffect(() => {
    supabase.auth.getUser().then(({ data }) => setUser(data.user));
  }, []);

  const logout = async () => {
    await supabase.auth.signOut();
    router.push(`/${locale}/auth`);
  };

  const switchLocale = (next: string) => {
    // パスの言語プレフィックスを置き換える
    const segments = path.split("/");
    segments[1] = next;
    router.push(segments.join("/"));
  };

  return (
    <header className="border-b border-gray-800 px-6 py-3 flex items-center justify-between">
      <Link href={`/${locale}`} className="text-lg font-bold text-indigo-400">
        Nightly Edge
      </Link>

      <nav className="flex items-center gap-5 text-sm text-gray-300">
        {user ? (
          <>
            <Link href={`/${locale}`}         className="hover:text-white">{t("dashboard")}</Link>
            <Link href={`/${locale}/history`} className="hover:text-white">{t("history")}</Link>
            <Link href={`/${locale}/settings`}className="hover:text-white">{t("settings")}</Link>
            <button onClick={logout} className="hover:text-white">{t("logout")}</button>
          </>
        ) : (
          <Link href={`/${locale}/auth`} className="hover:text-white">{t("login")}</Link>
        )}
        <a href="mailto:ryunosukeiwakawa@playrie.com" className="hover:text-white text-gray-500">
          {t("contact")}
        </a>

        {/* 言語切替 */}
        <div className="flex gap-1 border border-gray-700 rounded px-2 py-0.5">
          {["ja", "en"].map((l) => (
            <button
              key={l}
              onClick={() => switchLocale(l)}
              className={`text-xs px-1 rounded ${locale === l ? "text-white font-bold" : "text-gray-500 hover:text-gray-300"}`}
            >
              {l.toUpperCase()}
            </button>
          ))}
        </div>
      </nav>
    </header>
  );
}
