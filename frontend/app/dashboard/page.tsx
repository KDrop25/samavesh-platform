import Link from "next/link";
import { getT, titled } from "@/lib/i18n";
import { requireUser, type Role } from "@/lib/session";

export const generateMetadata = titled("dashboard.title");

/** One card per section the role can use. Grows as modules are added. */
const SECTIONS: { href: string; title: string; text: string; roles: Role[] }[] = [
  { href: "/admin/users", title: "nav.users", text: "dashboard.users", roles: ["administrator"] },
];

export default async function DashboardPage() {
  const [t, user] = await Promise.all([getT(), requireUser()]);
  const sections = SECTIONS.filter((section) => section.roles.includes(user.role));

  return (
    <>
      <h1>{t("dashboard.welcome", { name: user.full_name })}</h1>
      <p className="mb-8">{t("dashboard.role", { role: t(`role.${user.role}`) })}</p>
      <h2>{t("dashboard.sections")}</h2>
      {sections.length === 0 ? (
        <p>{t("dashboard.empty")}</p>
      ) : (
        <ul className="grid gap-4 sm:grid-cols-2">
          {sections.map((section) => (
            <li key={section.href} className="card">
              <h3>
                <Link href={section.href}>{t(section.title)}</Link>
              </h3>
              <p>{t(section.text)}</p>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
