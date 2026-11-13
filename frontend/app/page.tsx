import Link from "next/link";
import { getT } from "@/lib/i18n";
import { getUser } from "@/lib/session";

export default async function HomePage() {
  const [t, user] = await Promise.all([getT(), getUser()]);
  return (
    <div className="max-w-2xl">
      <p className="mb-2 font-semibold text-muted">{t("app.tagline")}</p>
      <h1>{t("home.title")}</h1>
      <p className="mb-6">{t("home.intro")}</p>
      <div className="flex flex-wrap gap-3">
        {user ? (
          <Link href="/dashboard" className="btn">
            {t("nav.dashboard")}
          </Link>
        ) : (
          <>
            <Link href="/register" className="btn">
              {t("home.start")}
            </Link>
            <Link href="/login" className="btn btn-secondary">
              {t("nav.signIn")}
            </Link>
          </>
        )}
      </div>
    </div>
  );
}
