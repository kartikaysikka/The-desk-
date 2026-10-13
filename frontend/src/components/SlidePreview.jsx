import { useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";

export const SlidePreview = ({ urls, handle, caption }) => {
  const [i, setI] = useState(0);
  const go = (d) => setI((x) => Math.min(urls.length - 1, Math.max(0, x + d)));
  return (
    <div className="border-2 border-black bg-white max-w-[460px] w-full" data-testid="slide-preview">
      <div className="flex items-center gap-2 px-3 py-2 border-b border-black/20">
        <div className="w-7 h-7 rounded-full bg-black" />
        <span className="font-semibold text-sm">{handle?.replace("@", "")}</span>
      </div>
      <div className="relative aspect-[4/5] bg-black overflow-hidden">
        <img src={urls[i]} alt={`slide ${i + 1}`} className="w-full h-full object-cover" data-testid="preview-image" />
        {i > 0 && <button data-testid="preview-prev" onClick={() => go(-1)} className="absolute left-2 top-1/2 -translate-y-1/2 bg-white/90 rounded-full p-1"><ChevronLeft size={18} /></button>}
        {i < urls.length - 1 && <button data-testid="preview-next" onClick={() => go(1)} className="absolute right-2 top-1/2 -translate-y-1/2 bg-white/90 rounded-full p-1"><ChevronRight size={18} /></button>}
        <span className="absolute top-3 right-3 bg-black/70 text-white text-xs px-2 py-0.5 rounded-full font-mono" data-testid="preview-counter">{i + 1}/{urls.length}</span>
      </div>
      <div className="flex justify-center gap-1 py-2">
        {urls.map((_, j) => <span key={j} className={`w-1.5 h-1.5 rounded-full ${j === i ? "bg-black" : "bg-black/25"}`} />)}
      </div>
      <p className="px-3 pb-3 text-sm whitespace-pre-line line-clamp-6" data-testid="preview-caption"><b>{handle?.replace("@", "")}</b> {caption}</p>
    </div>
  );
};
