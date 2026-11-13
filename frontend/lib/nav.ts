import type { User } from "@/lib/session";

export type Section = { href: string; label: string; text: string };

/**
 * Sections a user can open - used for the main menu and the dashboard cards.
 * This only decides what to show; the API enforces access on every request.
 */
export function sectionsFor(user: User): Section[] {
  const sections: Section[] = [];
  if (user.role === "student") {
    sections.push({ href: `/students/${user.id}`, label: "nav.myProfile", text: "dashboard.myProfile" });
  }
  if (["guardian", "support_staff", "nodal_officer", "administrator"].includes(user.role)) {
    sections.push({ href: "/students", label: "nav.students", text: "dashboard.students" });
  }
  if (user.role === "administrator") {
    sections.push({ href: "/admin/users", label: "nav.users", text: "dashboard.users" });
  }
  return sections;
}
