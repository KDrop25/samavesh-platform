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
  if (["support_staff", "nodal_officer", "administrator"].includes(user.role)) {
    sections.push({ href: "/provisions/overdue", label: "nav.overdue", text: "dashboard.overdue" });
    sections.push({ href: "/compliance", label: "nav.compliance", text: "dashboard.compliance" });
  }
  if (["nodal_officer", "administrator"].includes(user.role)) {
    sections.push({ href: "/approvals", label: "nav.approvals", text: "dashboard.approvals" });
    sections.push({ href: "/audit", label: "nav.audit", text: "dashboard.audit" });
  }
  if (user.role === "nodal_officer") {
    sections.push({ href: "/terms", label: "nav.terms", text: "dashboard.terms" });
  }
  if (user.role === "grievance_officer") {
    sections.push({ href: "/grievances", label: "nav.grievances", text: "dashboard.grievances" });
  }
  if (["grievance_officer", "administrator"].includes(user.role)) {
    sections.push({ href: "/escalation-settings", label: "nav.escalation", text: "dashboard.escalation" });
  }
  if (user.role === "administrator") {
    sections.push({ href: "/grievances/escalated", label: "nav.escalated", text: "dashboard.escalated" });
    sections.push({ href: "/admin/users", label: "nav.users", text: "dashboard.users" });
  }
  return sections;
}
