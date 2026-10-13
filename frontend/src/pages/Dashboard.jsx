import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Plus } from "lucide-react";
import { api, STATUS_LABEL } from "@/lib/api";

const FILTERS = [["", "All"], ["pending_review", "Awaiting"], ["published", "Published"], ["failed", "Failed"], ["rejected", "Rejected"]];

const PostCard = ({ p, i }) => (
  <Link to={`/posts/${p.id}`} data-testid={`post-card-${p.id}`} className="nd-card nd-rise block border-2 border-black bg-white" style={{ animationDelay: `${i * 50}ms` }}>
    <div className="aspect-[4/5] bg-black overflow-hidden">
      <img src={`${process.env.REACT_APP_BACKEND_URL}${p.rendered_urls[0]}`} alt={p.headline} className="w-full h-full object-contain" loading="lazy" />
    </div>
    <div className="p-4 border-t-2 border-black">
      <div className="flex justify-between font-mono text-[11px] uppercase tracking-wider">
        <span data-testid={`post-status-${p.id}`} className={p.status === "pending_review" ? "bg-black text-white px-1.5" : ""}>{STATUS_LABEL[p.status]}</span>
        <span className="text-[#6b6b66]">{p.template === "standard" ? "Standard" : "B&W"} · {p.rendered_urls.length} slides</span>
      </div>
      <h3 className="font-serif font-semibold text-lg leading-snug mt-2 line-clamp-2">{p.headline}</h3>
    </div>
  </Link>
);

export default function Dashboard() {
  const [posts, setPosts] = useState(null);
  const [filter, setFilter] = useState("");

  useEffect(() => {
    setPosts(null);
    api.get("/posts", { params: filter ? { status: filter } : {} }).then((r) => setPosts(r.data));
  }, [filter]);

  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-6 mb-10">
        <div>
          <div className="nd-label">Today's queue</div>
          <h2 className="font-display text-4xl md:text-5xl mt-1">THE DESK</h2>
        </div>
        <Link to="/new" className="nd-btn" data-testid="new-story-btn"><Plus size={16} /> New story</Link>
      </div>
      <div className="flex flex-wrap gap-2 mb-8 border-b-2 border-black pb-4">
        {FILTERS.map(([v, l]) => (
          <button key={v} data-testid={`filter-${v || "all"}`} onClick={() => setFilter(v)}
            className={`font-mono text-xs uppercase tracking-widest px-3 py-1.5 border-2 border-black transition-colors ${filter === v ? "bg-black text-white" : "hover:bg-black/5"}`}>{l}</button>
        ))}
      </div>
      {posts === null && <p className="font-mono text-sm" data-testid="posts-loading">Loading wire…</p>}
      {posts?.length === 0 && (
        <div className="border-2 border-dashed border-black p-16 text-center" data-testid="empty-state">
          <p className="font-display text-3xl">NO STORIES ON THE WIRE</p>
          <p className="font-serif text-lg mt-2 text-[#6b6b66]">File your first story and the desk will design it.</p>
        </div>
      )}
      <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {posts?.map((p, i) => <PostCard key={p.id} p={p} i={i} />)}
      </div>
    </div>
  );
}
