import { useState } from "react";
import { PhotoAdjuster, DEFAULT_ADJ } from "@/components/PhotoAdjuster";
import { TEMPLATES } from "@/lib/api";

const BASE = process.env.REACT_APP_BACKEND_URL;

export const PhotoPositions = ({ form, setForm, sources }) => {
  const [k, setK] = useState(0);
  const tpl = TEMPLATES.find((t) => t.id === form.template) || TEMPLATES[0];
  const total = 1 + form.slides.length;
  const idx = Math.min(k, total - 1);
  const adjs = form.photo_adjust || [];
  const setAdj = (val) => {
    const next = Array.from({ length: total }, (_, j) => adjs[j] || DEFAULT_ADJ);
    next[idx] = val;
    setForm({ ...form, photo_adjust: next });
  };

  return (
    <div className="space-y-4" data-testid="photo-positions">
      <div className="flex flex-wrap gap-2">
        {Array.from({ length: total }, (_, j) => (
          <button type="button" key={j} data-testid={`photo-slide-tab-${j}`} onClick={() => setK(j)}
            className={`font-mono text-xs px-3 py-1.5 border-2 border-black transition-colors ${j === idx ? "bg-black text-white" : "hover:bg-black/5"}`}>
            {j === 0 ? "Cover" : `Slide ${String(j + 1).padStart(2, "0")}`}
          </button>
        ))}
      </div>
      <div className="max-w-md">
        <PhotoAdjuster key={`${form.template}-${idx}`} src={`${BASE}${sources[idx % sources.length]}`}
          aspect={idx === 0 ? tpl.cover : tpl.detail} value={adjs[idx]} onChange={setAdj} />
      </div>
    </div>
  );
};
