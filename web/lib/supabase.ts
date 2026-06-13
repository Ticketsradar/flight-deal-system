import { createClient } from "@supabase/supabase-js";

// 只用 publishable key(設計上公開、RLS 只開公開只讀)。
// 鐵律:sb_secret_ 死都唔可以入前端 / NEXT_PUBLIC_。
const url = process.env.NEXT_PUBLIC_SUPABASE_URL ?? "";
const publishableKey = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY ?? "";

export const supabase = createClient(url, publishableKey, {
  auth: { persistSession: false },
});

export const supabaseConfigured = Boolean(url && publishableKey);
