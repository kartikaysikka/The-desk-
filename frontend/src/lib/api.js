import axios from "axios";

export const api = axios.create({
  baseURL: `${process.env.REACT_APP_BACKEND_URL}/api`,
  withCredentials: true,
});

export function errMsg(e) {
  const d = e?.response?.data?.detail;
  if (!d) return e?.message || "Something went wrong";
  if (typeof d === "string") return d;
  if (Array.isArray(d)) return d.map((x) => x?.msg || JSON.stringify(x)).join(" ");
  return d.msg || String(d);
}

export const TEMPLATES = [
  { id: "bw_informative", name: "Black And White Informative", hint: "Full-bleed cover, fact slides with photo on top (4:5)" },
  { id: "standard", name: "Standard", hint: "Photo on top, dark headline panel with red accents (1:1)" },
];

export const STATUS_LABEL = {
  pending_review: "Awaiting approval",
  publishing: "Publishing",
  published: "Published",
  failed: "Failed",
  rejected: "Rejected",
};
