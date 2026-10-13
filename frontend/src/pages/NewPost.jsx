import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ImagePlus, X, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { api, errMsg } from "@/lib/api";

export default function NewPost() {
  const nav = useNavigate();
  const [files, setFiles] = useState([]);
  const [raw, setRaw] = useState("");
  const [kicker, setKicker] = useState("");
  const [busy, setBusy] = useState(false);

  const addFiles = (list) => setFiles((f) => [...f, ...Array.from(list).filter((x) => x.type.startsWith("image/"))].slice(0, 10));

  const submit = async (e) => {
    e.preventDefault();
    if (!files.length) return toast.error("Add at least one photo");
    setBusy(true);
    const fd = new FormData();
    fd.append("raw_text", raw);
    fd.append("kicker", kicker);
    files.forEach((f) => fd.append("images", f));
    try {
      const { data } = await api.post("/posts", fd);
      toast.success("Draft ready for review");
      nav(`/posts/${data.id}`);
    } catch (err) { toast.error(errMsg(err)); setBusy(false); }
  };

  return (
    <form onSubmit={submit} className="grid lg:grid-cols-[1fr_1.2fr] gap-12 max-w-6xl" data-testid="new-post-form">
      <section className="nd-rise">
        <div className="nd-label">Step 01 — Photos (first = cover)</div>
        <label data-testid="image-dropzone" onDragOver={(e) => e.preventDefault()} onDrop={(e) => { e.preventDefault(); addFiles(e.dataTransfer.files); }}
          className="mt-3 border-2 border-dashed border-black aspect-[4/5] flex flex-col items-center justify-center cursor-pointer hover:bg-black/5 transition-colors relative overflow-hidden">
          {files[0] ? <img src={URL.createObjectURL(files[0])} alt="cover" className="absolute inset-0 w-full h-full object-cover" /> : (
            <><ImagePlus size={40} strokeWidth={1.4} /><span className="font-mono text-xs uppercase tracking-widest mt-3">Drop or click to add photos</span></>
          )}
          <input data-testid="image-input" type="file" accept="image/*" multiple className="hidden" onChange={(e) => addFiles(e.target.files)} />
        </label>
        {files.length > 0 && (
          <div className="flex gap-2 mt-3 flex-wrap" data-testid="image-thumbs">
            {files.map((f, i) => (
              <div key={i} className="relative w-16 h-20 border-2 border-black">
                <img src={URL.createObjectURL(f)} alt="" className="w-full h-full object-cover" />
                <button type="button" data-testid={`remove-image-${i}`} onClick={() => setFiles(files.filter((_, j) => j !== i))} className="absolute -top-2 -right-2 bg-black text-white rounded-full p-0.5"><X size={12} /></button>
              </div>
            ))}
          </div>
        )}
      </section>
      <section className="nd-rise space-y-8" style={{ animationDelay: "100ms" }}>
        <div>
          <div className="nd-label">Step 02 — Raw notes</div>
          <h2 className="font-display text-4xl mt-1">FILE THE STORY</h2>
          <p className="font-serif text-[#6b6b66] mt-2">Paste everything you know — who, what, where, quotes, numbers. Messy is fine.</p>
        </div>
        <textarea data-testid="raw-text-input" className="nd-textarea min-h-[300px]" required value={raw} onChange={(e) => setRaw(e.target.value)}
          placeholder="e.g. Fire at central market around 4pm today, 3 shops gutted, no casualties, fire brigade took 2 hrs, cause suspected short circuit…" />
        <div>
          <label className="nd-label">Label (optional)</label>
          <input data-testid="kicker-input" className="nd-input font-mono uppercase" value={kicker} onChange={(e) => setKicker(e.target.value)} placeholder="BREAKING / POLITICS / SPORTS" />
        </div>
        <button data-testid="generate-post-btn" className="nd-btn" disabled={busy}>
          <Sparkles size={16} /> {busy ? "Writing & designing…" : "Generate post"}
        </button>
        {busy && <p className="font-mono text-xs text-[#6b6b66]" data-testid="generating-hint">This usually takes 10–20 seconds.</p>}
      </section>
    </form>
  );
}
