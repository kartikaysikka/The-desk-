import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Check, RefreshCw, Save, Trash2, X, ExternalLink, Plus } from "lucide-react";
import { toast } from "sonner";
import { api, errMsg, STATUS_LABEL, TEMPLATES } from "@/lib/api";
import { SlidePreview } from "@/components/SlidePreview";

const Field = ({ label, children }) => (<div><label className="nd-label">{label}</label>{children}</div>);

export default function Review() {
  const { id } = useParams();
  const nav = useNavigate();
  const [post, setPost] = useState(null);
  const [form, setForm] = useState(null);
  const [settings, setSettings] = useState({});
  const [busy, setBusy] = useState("");

  const load = (p) => { setPost(p); setForm({ template: p.template || "bw_informative", kicker: p.kicker, headline: p.headline, slides: p.slides, caption: p.caption, hashtags: p.hashtags }); };

  useEffect(() => {
    api.get(`/posts/${id}`).then((r) => load(r.data)).catch(() => nav("/"));
    api.get("/settings").then((r) => setSettings(r.data));
  }, [id, nav]);

  const run = async (key, fn, ok) => {
    setBusy(key);
    try { const r = await fn(); if (r?.data?.id) load(r.data); if (ok) toast.success(ok); return true; }
    catch (e) { toast.error(errMsg(e)); api.get(`/posts/${id}`).then((r) => load(r.data)); return false; }
    finally { setBusy(""); }
  };

  if (!post || !form) return <p className="font-mono text-sm" data-testid="review-loading">Loading story…</p>;
  const locked = post.status === "published" || post.status === "publishing";
  const setSlide = (i, k, v) => setForm({ ...form, slides: form.slides.map((s, j) => (j === i ? { ...s, [k]: v } : s)) });
  const fullCaption = `${form.caption}\n\n${form.hashtags} ${settings.default_hashtags || ""}`;

  return (
    <div className="grid lg:grid-cols-[minmax(0,460px)_1fr] gap-12 items-start">
      <div className="lg:sticky lg:top-8 space-y-4 nd-rise">
        <SlidePreview key={post.rendered_urls.join()} urls={post.rendered_urls} handle={settings.brand_name} caption={fullCaption} />
        <div className="font-mono text-xs uppercase tracking-widest" data-testid="review-status">Status: <b>{STATUS_LABEL[post.status]}</b></div>
        {post.error && <p className="font-mono text-xs border-l-4 border-black pl-3" data-testid="publish-error">{post.error}</p>}
        {post.permalink && <a href={post.permalink} target="_blank" rel="noreferrer" className="nd-btn ghost" data-testid="view-on-instagram"><ExternalLink size={14} /> View on Instagram</a>}
      </div>

      <div className="space-y-8 nd-rise" style={{ animationDelay: "100ms" }}>
        <div className="flex flex-wrap gap-3 border-b-2 border-black pb-6">
          <button data-testid="approve-publish-btn" className="nd-btn" disabled={locked || !!busy}
            onClick={() => run("approve", () => api.post(`/posts/${id}/approve`), "Published to Instagram")}>
            <Check size={16} /> {busy === "approve" ? "Publishing…" : "Approve & publish"}
          </button>
          <button data-testid="save-rerender-btn" className="nd-btn ghost" disabled={locked || !!busy}
            onClick={() => run("save", () => api.put(`/posts/${id}`, form), "Design updated")}>
            <Save size={16} /> {busy === "save" ? "Rendering…" : "Save & re-render"}
          </button>
          <button data-testid="regenerate-btn" className="nd-btn ghost" disabled={locked || !!busy}
            onClick={() => run("regen", () => api.post(`/posts/${id}/regenerate`), "Rewritten by AI")}>
            <RefreshCw size={16} /> {busy === "regen" ? "Rewriting…" : "Rewrite with AI"}
          </button>
          <button data-testid="reject-btn" className="nd-btn ghost" disabled={locked || !!busy} onClick={() => run("reject", () => api.post(`/posts/${id}/reject`), "Rejected")}><X size={16} /> Reject</button>
          <button data-testid="delete-btn" className="nd-btn ghost ml-auto" disabled={!!busy}
            onClick={async () => { if (window.confirm("Delete this story?")) { await api.delete(`/posts/${id}`); nav("/"); } }}><Trash2 size={16} /></button>
        </div>

        <fieldset disabled={locked} className="space-y-8">
          <Field label="Template">
            <div className="flex flex-wrap gap-2 mt-2">
              {TEMPLATES.map((t) => (
                <button type="button" key={t.id} data-testid={`template-option-${t.id}`} onClick={() => setForm({ ...form, template: t.id })}
                  className={`font-mono text-xs uppercase tracking-widest px-3 py-2 border-2 border-black transition-colors ${form.template === t.id ? "bg-black text-white" : "hover:bg-black/5"}`}>{t.name}</button>
              ))}
            </div>
            {form.template !== (post.template || "bw_informative") && <p className="font-mono text-xs mt-2" data-testid="template-changed-hint">Click "Save &amp; re-render" to apply the new template.</p>}
          </Field>
          <div className="grid md:grid-cols-[180px_1fr] gap-6">
            <Field label="Label"><input data-testid="edit-kicker" className="nd-input font-mono uppercase" value={form.kicker} onChange={(e) => setForm({ ...form, kicker: e.target.value })} /></Field>
            <Field label="Cover headline"><input data-testid="edit-headline" className="nd-input font-display text-2xl" value={form.headline} onChange={(e) => setForm({ ...form, headline: e.target.value })} /></Field>
          </div>
          <div className="space-y-6">
            {form.slides.map((s, i) => (
              <div key={i} className="border-l-4 border-black pl-5 space-y-3" data-testid={`slide-editor-${i}`}>
                <div className="flex justify-between items-center">
                  <span className="nd-label">Slide {String(i + 2).padStart(2, "0")}</span>
                  <button type="button" data-testid={`remove-slide-${i}`} onClick={() => setForm({ ...form, slides: form.slides.filter((_, j) => j !== i) })} className="text-xs font-mono underline">remove</button>
                </div>
                <input data-testid={`edit-slide-title-${i}`} className="nd-input font-display text-xl" value={s.title} onChange={(e) => setSlide(i, "title", e.target.value)} />
                <textarea data-testid={`edit-slide-body-${i}`} className="nd-textarea" rows={3} value={s.body} onChange={(e) => setSlide(i, "body", e.target.value)} />
              </div>
            ))}
            {form.slides.length < 9 && (
              <button type="button" data-testid="add-slide-btn" className="font-mono text-xs uppercase tracking-widest flex items-center gap-1 hover:underline"
                onClick={() => setForm({ ...form, slides: [...form.slides, { title: "New slide", body: "" }] })}><Plus size={14} /> Add slide</button>
            )}
          </div>
          <Field label="Caption"><textarea data-testid="edit-caption" className="nd-textarea mt-2" rows={6} value={form.caption} onChange={(e) => setForm({ ...form, caption: e.target.value })} /></Field>
          <Field label="Hashtags"><input data-testid="edit-hashtags" className="nd-input font-mono text-sm" value={form.hashtags} onChange={(e) => setForm({ ...form, hashtags: e.target.value })} /></Field>
        </fieldset>

        <details className="border-t-2 border-black pt-4">
          <summary className="nd-label cursor-pointer">Original raw notes</summary>
          <p className="font-serif mt-3 whitespace-pre-line" data-testid="raw-notes">{post.raw_text}</p>
        </details>
      </div>
    </div>
  );
}
