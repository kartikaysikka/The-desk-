import { useEffect, useState } from "react";
import { toast } from "sonner";
import { api, errMsg, TEMPLATES } from "@/lib/api";

export default function Settings() {
  const [s, setS] = useState(null);
  const [token, setToken] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => { api.get("/settings").then((r) => setS(r.data)); }, []);

  const save = async (e) => {
    e.preventDefault(); setBusy(true);
    try {
      const { data } = await api.put("/settings", { ...s, ig_access_token: token || null });
      setS(data); setToken(""); toast.success("Settings saved");
    } catch (err) { toast.error(errMsg(err)); }
    finally { setBusy(false); }
  };

  if (!s) return <p className="font-mono text-sm">Loading…</p>;
  const set = (k) => (e) => setS({ ...s, [k]: e.target.value });

  return (
    <form onSubmit={save} className="max-w-3xl space-y-12 nd-rise" data-testid="settings-form">
      <section className="space-y-6">
        <h2 className="font-display text-4xl">MASTHEAD</h2>
        <p className="font-serif text-[#6b6b66] -mt-4">Shown on every slide.</p>
        <div><label className="nd-label">Channel name</label><input data-testid="brand-name-input" className="nd-input" value={s.brand_name} onChange={set("brand_name")} required /></div>
        <div><label className="nd-label">Default photo credit</label><input data-testid="default-photo-credit-input" className="nd-input font-mono uppercase" value={s.default_photo_credit} onChange={set("default_photo_credit")} /></div>
        <div>
          <label className="nd-label">Preferred template</label>
          <div className="flex flex-wrap gap-2 mt-2">
            {TEMPLATES.map((t) => (
              <button type="button" key={t.id} data-testid={`default-template-${t.id}`} onClick={() => setS({ ...s, default_template: t.id })}
                className={`font-mono text-xs uppercase tracking-widest px-3 py-2 border-2 border-black transition-colors ${s.default_template === t.id ? "bg-black text-white" : "hover:bg-black/5"}`}>{t.name}</button>
            ))}
          </div>
        </div>
        <div><label className="nd-label">Always-add hashtags</label><input data-testid="default-hashtags-input" className="nd-input font-mono text-sm" value={s.default_hashtags} onChange={set("default_hashtags")} /></div>
      </section>

      <section className="space-y-6 border-t-2 border-black pt-10">
        <div className="flex items-center justify-between">
          <h2 className="font-display text-4xl">INSTAGRAM</h2>
          <span data-testid="ig-connection-status" className={`font-mono text-xs uppercase px-2 py-1 border-2 border-black ${s.ig_token_set && s.ig_user_id ? "bg-black text-white" : ""}`}>
            {s.ig_token_set && s.ig_user_id ? "Connected" : "Not connected"}
          </span>
        </div>
        <div><label className="nd-label">IG User ID (instagram_business_account.id)</label><input data-testid="ig-user-id-input" className="nd-input font-mono" value={s.ig_user_id} onChange={set("ig_user_id")} /></div>
        <div>
          <label className="nd-label">Long-lived access token {s.ig_token_set && `(saved: ${s.ig_token_preview})`}</label>
          <input data-testid="ig-token-input" className="nd-input font-mono" type="password" value={token} onChange={(e) => setToken(e.target.value)} placeholder={s.ig_token_set ? "Leave blank to keep current token" : "Paste token"} />
        </div>
        <ol className="font-serif text-sm text-[#6b6b66] list-decimal pl-5 space-y-1">
          <li>Convert your Instagram to a Business/Creator account and link it to a Facebook Page.</li>
          <li>Create an app at developers.facebook.com with permissions instagram_basic, instagram_content_publish, pages_show_list.</li>
          <li>Generate a token in Graph API Explorer, exchange it for a long-lived token (~60 days).</li>
          <li>Call <code>/me/accounts?fields=instagram_business_account</code> to get your IG User ID.</li>
        </ol>
      </section>
      <button data-testid="save-settings-btn" className="nd-btn" disabled={busy}>{busy ? "Saving…" : "Save settings"}</button>
    </form>
  );
}
