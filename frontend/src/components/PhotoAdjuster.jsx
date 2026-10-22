import { useEffect, useRef, useState } from "react";
import { Move, RotateCcw } from "lucide-react";
import { Slider } from "@/components/ui/slider";

export const DEFAULT_ADJ = { x: 0.5, y: 0.4, zoom: 1 };
const clamp = (v) => Math.min(1, Math.max(0, v));

export const PhotoAdjuster = ({ src, aspect, value, onChange }) => {
  const box = useRef(null);
  const drag = useRef(null);
  const [cw, setCw] = useState(0);
  const [nat, setNat] = useState(null);
  const v = value || DEFAULT_ADJ;

  useEffect(() => {
    const ro = new ResizeObserver(([e]) => setCw(e.contentRect.width));
    if (box.current) ro.observe(box.current);
    return () => ro.disconnect();
  }, []);

  const ch = cw / aspect;
  const s = nat ? Math.max(cw / nat.w, ch / nat.h) * v.zoom : 1;
  const w = nat ? nat.w * s : cw, h = nat ? nat.h * s : ch;
  const ox = w - cw, oy = h - ch;

  const onDown = (e) => { e.currentTarget.setPointerCapture(e.pointerId); drag.current = { sx: e.clientX, sy: e.clientY, x: v.x, y: v.y }; };
  const onMove = (e) => {
    const d = drag.current;
    if (!d) return;
    onChange({ ...v, x: ox > 0 ? clamp(d.x - (e.clientX - d.sx) / ox) : 0.5, y: oy > 0 ? clamp(d.y - (e.clientY - d.sy) / oy) : 0.5 });
  };

  return (
    <div className="space-y-3" data-testid="photo-adjuster">
      <div ref={box} className="relative w-full overflow-hidden bg-black border-2 border-black cursor-grab active:cursor-grabbing touch-none select-none"
        style={{ height: ch || undefined, aspectRatio: ch ? undefined : aspect }} data-testid="photo-adjuster-frame"
        onPointerDown={onDown} onPointerMove={onMove} onPointerUp={() => (drag.current = null)}>
        <img src={src} alt="" draggable={false} onLoad={(e) => setNat({ w: e.target.naturalWidth, h: e.target.naturalHeight })}
          className="absolute max-w-none pointer-events-none" style={{ width: w, height: h, left: -ox * v.x, top: -oy * v.y }} />
        <span className="absolute bottom-2 left-2 bg-black/70 text-white font-mono text-[10px] px-2 py-1 flex items-center gap-1"><Move size={12} /> Drag to position</span>
      </div>
      <div className="flex items-center gap-4">
        <span className="nd-label w-12">Zoom</span>
        <Slider data-testid="photo-zoom-slider" min={1} max={3} step={0.05} value={[v.zoom]} onValueChange={([z]) => onChange({ ...v, zoom: z })} className="flex-1" />
        <span className="font-mono text-xs w-12" data-testid="photo-zoom-value">{v.zoom.toFixed(2)}x</span>
        <button type="button" data-testid="photo-adjust-reset" onClick={() => onChange(DEFAULT_ADJ)} className="p-1 hover:bg-black hover:text-white transition-colors" title="Reset"><RotateCcw size={14} /></button>
      </div>
    </div>
  );
};
