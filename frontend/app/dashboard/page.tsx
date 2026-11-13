import Link from "next/link";
import { getT, titled } from "@/lib/i18n";
import { sectionsFor } from "@/lib/nav";
import { requireUser } from "@/lib/session";

export const generateMetadata = titled("dashboard.title");

export default async function DashboardPage() {
  const [t, user] = await Promise.all([getT(), requireUser()]);
  const sections = sectionsFor(user);

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
                <Link href={section.href}>{t(section.label)}</Link>
              </h3>
              <p>{t(section.text)}</p>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
