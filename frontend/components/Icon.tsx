// Decorative line icons (24px grid). Always paired with visible text, so they are hidden from assistive tech.
const paths: Record<string, string> = {
  home: "M3 11l9-8 9 8M5 10v10h14V10",
  user: "M12 12a4 4 0 100-8 4 4 0 000 8zM4 21a8 8 0 0116 0",
  users: "M9 11a4 4 0 100-8 4 4 0 000 8zM2 21a7 7 0 0114 0M17 3.5a4 4 0 010 7.5M22 21a7 7 0 00-4-6.3",
  clock: "M12 21a9 9 0 100-18 9 9 0 000 18zM12 7v5l3 2",
  shield: "M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6l8-3zM9 12l2 2 4-4",
  check: "M12 21a9 9 0 100-18 9 9 0 000 18zM8 12l3 3 5-6",
  list: "M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01",
  note: "M5 3h14v18H5zM9 8h6M9 12h6M9 16h3",
  chat: "M4 5h16v11H9l-5 4V5z",
  alert: "M12 3l10 18H2L12 3zM12 10v5M12 18h.01",
  search: "M11 19a8 8 0 100-16 8 8 0 000 16zM21 21l-4.3-4.3",
  bell: "M6 16V11a6 6 0 1112 0v5l2 2H4l2-2zM10 21h4",
  gear: "M12 15a3 3 0 100-6 3 3 0 000 6zM19 12a7 7 0 00-.1-1l2-1.6-2-3.4-2.4 1a7 7 0 00-1.7-1L14.5 3h-4l-.4 2.9a7 7 0 00-1.7 1l-2.4-1-2 3.4 2 1.6a7 7 0 000 2l-2 1.6 2 3.4 2.4-1a7 7 0 001.7 1l.4 2.9h4l.4-2.9a7 7 0 001.7-1l2.4 1 2-3.4-2-1.6c.1-.3.1-.7.1-1z",
  login: "M10 17l5-5-5-5M15 12H3M14 4h6v16h-6",
  plus: "M12 5v14M5 12h14",
  sliders: "M4 6h10M18 6h2M4 12h4M12 12h8M4 18h12M20 18h0M14 4v4M8 10v4M16 16v4",
};

const byHref: [RegExp, string][] = [
  [/^\/dashboard/, "home"],
  [/^\/students\/\d/, "user"],
  [/^\/students/, "users"],
  [/^\/provisions/, "clock"],
  [/^\/compliance/, "shield"],
  [/^\/approvals/, "check"],
  [/^\/audit/, "list"],
  [/^\/terms/, "note"],
  [/^\/grievances\/new/, "plus"],
  [/^\/grievances\/escalated/, "alert"],
  [/^\/grievances/, "chat"],
  [/^\/escalation/, "sliders"],
  [/^\/admin/, "users"],
  [/^\/track/, "search"],
  [/^\/notifications/, "bell"],
  [/^\/settings/, "gear"],
  [/^\/login/, "login"],
  [/^\/register/, "plus"],
];

export const iconFor = (href: string) => byHref.find(([re]) => re.test(href))?.[1] ?? "note";

export function Icon({ name }: { name: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d={paths[name] ?? paths.note} />
    </svg>
  );
}
