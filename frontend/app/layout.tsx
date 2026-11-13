import type { Metadata } from "next";
import { cookies } from "next/headers";
import Link from "next/link";
import "./globals.css";
import { logout, setLanguage } from "@/app/actions";
import { NavLink } from "@/components/NavLink";
import { SessionTimeout } from "@/components/SessionTimeout";
import { getLocale, getT } from "@/lib/i18n";
import { getUser, type Role } from "@/lib/session";

export const metadata: Metadata = {
  title: { default: "Samavesh", template: "%s – Samavesh" },
  description: "Accessible support, compliance and grievance platform for specially abled students.",
};

/** Sections each role can open. The API enforces the same rules; this only builds the menu. */
const NAV: { href: string; label: string; roles: Role[] }[] = [
  { href: "/admin/users", label: "nav.users", roles: ["administrator"] },
];

export default async function RootLayout({ children }: LayoutProps<"/">) {
  const [t, locale, user, store] = await Promise.all([getT(), getLocale(), getUser(), cookies()]);
  const theme = store.get("theme")?.value;
  const textSize = store.get("text_size")?.value;
  const other = locale === "hi" ? "en" : "hi";

  return (
    <html lang={locale} data-theme={theme} data-text-size={textSize} className="h-full">
      <body className="flex min-h-full flex-col font-sans">
        <a href="#main" className="skip-link">
          {t("nav.skip")}
        </a>
        <header className="border-b border-border">
          <div className="mx-auto flex max-w-5xl flex-wrap items-center gap-x-6 gap-y-1 px-4 py-2">
            <Link href="/" className="text-xl font-bold text-fg no-underline">
              {t("app.name")}
            </Link>
            <nav aria-label={t("nav.main")} className="flex-1">
              <ul className="flex flex-wrap gap-x-2">
                {user && (
                  <li>
                    <NavLink href="/dashboard">{t("nav.dashboard")}</NavLink>
                  </li>
                )}
                {NAV.filter((item) => user && item.roles.includes(user.role)).map((item) => (
                  <li key={item.href}>
                    <NavLink href={item.href}>{t(item.label)}</NavLink>
                  </li>
                ))}
                <li>
                  <NavLink href="/settings">{t("nav.settings")}</NavLink>
                </li>
                {!user && (
                  <>
                    <li>
                      <NavLink href="/login">{t("nav.signIn")}</NavLink>
                    </li>
                    <li>
                      <NavLink href="/register">{t("nav.register")}</NavLink>
                    </li>
                  </>
                )}
              </ul>
            </nav>
            <div className="flex flex-wrap items-center gap-3">
              <form action={setLanguage.bind(null, other)}>
                <button type="submit" lang={other} className="btn btn-secondary">
                  {other === "hi" ? "हिन्दी" : "English"}
                </button>
              </form>
              {user && (
                <form action={logout} className="flex items-center gap-3">
                  <span className="text-muted">{t("nav.signedInAs", { name: user.full_name })}</span>
                  <button type="submit" className="btn btn-secondary">
                    {t("nav.signOut")}
                  </button>
                </form>
              )}
            </div>
          </div>
        </header>
        <main id="main" tabIndex={-1} className="mx-auto w-full max-w-5xl flex-1 px-4 py-8">
          {children}
        </main>
        <footer className="border-t border-border">
          <p className="mx-auto max-w-5xl px-4 py-4 text-muted">{t("footer.text")}</p>
        </footer>
        {user && (
          <SessionTimeout
            labels={{
              title: t("timeout.title"),
              body: t("timeout.body"),
              stay: t("timeout.stay"),
              signOut: t("nav.signOut"),
            }}
          />
        )}
      </body>
    </html>
  );
}
