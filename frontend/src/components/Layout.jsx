import { NavLink, useNavigate } from "react-router-dom";
import { LogOut, Plus } from "lucide-react";
import { useAuth } from "@/context/AuthContext";

const links = [
  { to: "/", label: "Desk", id: "nav-desk" },
  { to: "/new", label: "New Story", id: "nav-new" },
  { to: "/settings", label: "Settings", id: "nav-settings" },
];

export default function Layout({ children }) {
  const { logout } = useAuth();
  const nav = useNavigate();
  const today = new Date().toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "long", year: "numeric" });

  return (
    <div className="nd-grain min-h-screen">
      <div className="bg-black text-[#f3f1ec] font-mono text-xs py-2 nd-ticker">
        <span>LIVE DESK — UPLOAD RAW PHOTOS + NOTES — AI DRAFTS THE CAROUSEL — YOU APPROVE — IT GOES LIVE ON INSTAGRAM — {today.toUpperCase()}</span>
      </div>
      <header className="border-b-2 border-black px-6 md:px-12 py-5 flex items-end justify-between gap-6">
        <div>
          <div className="nd-label">{today}</div>
          <h1 className="font-display text-4xl sm:text-5xl lg:text-6xl leading-none mt-1" data-testid="app-title">THE NEWSDESK</h1>
        </div>
        <nav className="flex items-center gap-1 md:gap-6 font-mono text-xs uppercase tracking-widest">
          {links.map((l) => (
            <NavLink key={l.to} to={l.to} end data-testid={l.id}
              className={({ isActive }) => `px-2 py-1 border-b-2 ${isActive ? "border-black" : "border-transparent hover:border-black/40"} transition-colors`}>
              {l.label}
            </NavLink>
          ))}
          <button data-testid="logout-btn" onClick={async () => { await logout(); nav("/login"); }} className="p-2 hover:bg-black hover:text-white transition-colors" title="Log out">
            <LogOut size={16} />
          </button>
        </nav>
      </header>
      <main className="px-6 md:px-12 py-10">{children}</main>
      <button data-testid="fab-new-story" onClick={() => nav("/new")} className="md:hidden fixed bottom-6 right-6 bg-black text-white p-4 rounded-full shadow-lg"><Plus /></button>
    </div>
  );
}
