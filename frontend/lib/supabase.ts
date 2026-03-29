import { createBrowserClient } from "@supabase/ssr";

const supabaseUrl  = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const supabaseAnon = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;

/** ブラウザ用 Supabase クライアント（シングルトン） */
export const supabase = createBrowserClient(supabaseUrl, supabaseAnon);

/** 現在のセッションから Bearer トークンを取得する */
export async function getAuthToken(): Promise<string | null> {
  const { data } = await supabase.auth.getSession();
  return data.session?.access_token ?? null;
}
