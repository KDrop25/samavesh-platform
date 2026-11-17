import type { Metadata } from "next";
import { cookies } from "next/headers";
import Link from "next/link";
import "./globals.css";
import { logout, setLanguage } from "@/app/actions";
import { NavLink } from "@/components/NavLink";
import { SessionTimeout } from "@/components/SessionTimeout";
import { getLocale, getT } from "@/lib/i18n";
import { api } from "@/lib/api";
import { sectionsFor } from "@/lib/nav";
import { getUser } from "@/lib/session";

export const metadata: Metadata = {
  title: { default: "Samavesh", template: "%s – Samavesh" },
  description: "Accessible support, compliance and grievance platform for specially abled students.",
};

function Brand({ name }: { name: string }) {
  return (
    <Link href="/" className="brand">
      <span className="brand-mark" aria-hidden="true">
        स
      </span>
      {name}
    </Link>
  );
}

function NavList({ items, row }: { items: { href: string; label: string }[]; row?: boolean }) {
  return (
    <ul className={row ? "flex flex-wrap gap-1" : "nav-list"}>
      {items.map((i) => (
        <li key={i.href}>
          <NavLink href={i.href}>{i.label}</NavLink>
        </li>
      ))}
    </ul>
  );
}

export default async function RootLayout({ children }: LayoutProps<"/">) {
  const [t, locale, user, store] = await Promise.all([getT(), getLocale(), getUser(), cookies()]);
  const theme = store.get("theme")?.value;
  const textSize = store.get("text_size")?.value;
  const other = locale === "hi" ? "en" : "hi";
  const inbox = user ? await api<{ unread: number }>("/notifications") : null;
  const unread = inbox?.ok ? inbox.data.unread : 0;

  const items: { href: string; label: string }[] = [
    ...(user ? [{ href: "/dashboard", label: t("nav.dashboard") }] : []),
    ...(user ? sectionsFor(user) : []).map((i) => ({ href: i.href, label: t(i.label) })),
    { href: "/grievances/new", label: t("nav.raise") },
    { href: "/track", label: t("nav.track") },
    ...(user ? [{ href: "/notifications", label: `${t("nav.notifications")} (${unread})` }] : []),
    { href: "/settings", label: t("nav.settings") },
    ...(user ? [] : [{ href: "/login", label: t("nav.signIn") }, { href: "/register", label: t("nav.register") }]),
  ];

  return (
    <html lang={locale} data-theme={theme} data-text-size={textSize} className="h-full">
      <body className="min-h-full font-sans">
        <a href="#main" className="skip-link">
          {t("nav.skip")}
        </a>
        <div className={user ? "shell shell-side" : "shell"}>
          {user ? (
            <aside className="side">
              <Brand name={t("app.name")} />
              <nav aria-label={t("nav.main")}>
                <NavList items={items} />
              </nav>
              <div className="side-foot">
                <div className="flex items-center gap-3 px-1">
                  <span className="avatar" aria-hidden="true">
                    {user.full_name.charAt(0).toUpperCase()}
                  </span>
                  <span className="text-sm leading-snug text-muted">{t("nav.signedInAs", { name: user.full_name })}</span>
                </div>
                <div className="flex gap-2">
                  <form action={setLanguage.bind(null, other)}>
                    <button type="submit" lang={other} className="btn btn-secondary">
                      {other === "hi" ? "हिन्दी" : "English"}
                    </button>
                  </form>
                  <form action={logout}>
                    <button type="submit" className="btn btn-secondary">
                      {t("nav.signOut")}
                    </button>
                  </form>
                </div>
              </div>
            </aside>
          ) : (
            <header className="topbar">
              <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-6 gap-y-1 px-4 py-2">
                <Brand name={t("app.name")} />
                <nav aria-label={t("nav.main")} className="flex-1">
                  <NavList items={items} row />
                </nav>
                <form action={setLanguage.bind(null, other)}>
                  <button type="submit" lang={other} className="btn btn-secondary">
                    {other === "hi" ? "हिन्दी" : "English"}
                  </button>
                </form>
              </div>
            </header>
          )}
          <div className="flex min-w-0 flex-col">
            <main id="main" tabIndex={-1} className={`mx-auto w-full flex-1 px-4 py-8 lg:px-10 ${user ? "max-w-5xl" : "max-w-6xl"}`}>
              {children}
            </main>
            <footer className="border-t border-line">
              <p className="mx-auto max-w-6xl px-4 py-4 text-sm text-muted lg:px-10">{t("footer.text")}</p>
            </footer>
          </div>
        </div>
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
