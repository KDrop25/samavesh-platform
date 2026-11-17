import Link from "next/link";
import { Icon } from "@/components/Icon";
import { getT } from "@/lib/i18n";
import { getUser } from "@/lib/session";

export default async function HomePage() {
  const [t, user] = await Promise.all([getT(), getUser()]);
  const features = [
    { icon: "note", key: "home.f1" },
    { icon: "shield", key: "home.f2" },
    { icon: "chat", key: "home.f3" },
  ];
  return (
    <>
      <section className="grid items-center gap-12 py-6 lg:grid-cols-[1.15fr_0.85fr] lg:py-14">
        <div>
          <p className="glass mb-6 inline-flex items-center gap-2 px-4 py-1.5 text-sm font-semibold !rounded-full">
            <span className="pulse-dot" aria-hidden="true" />
            {t("home.badge")}
          </p>
          <h1 className="hero-title">
            <span className="gradient-text">{t("app.tagline")}</span>
          </h1>
          <p className="mb-8 max-w-xl text-lg text-muted">{t("home.intro")}</p>
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
            <Link href="/track" className="btn btn-secondary">
              {t("home.track")}
            </Link>
          </div>
        </div>
        {/* Decorative illustration of the product; the real information is in the text beside and below it. */}
        <div className="relative hidden min-h-80 lg:block" aria-hidden="true">
          <div className="glass float absolute start-0 top-2 flex w-[19rem] items-center gap-3 p-4">
            <span className="chip-icon !mb-0">
              <Icon name="check" />
            </span>
            <span className="font-semibold">{t("home.v1")}</span>
          </div>
          <div className="glass float-slow absolute end-0 top-[8.5rem] flex w-[19rem] items-center gap-3 p-4">
            <span className="chip-icon !mb-0">
              <Icon name="clock" />
            </span>
            <span className="font-semibold">{t("home.v2")}</span>
          </div>
          <div className="glass float absolute start-8 top-[16rem] flex w-[19rem] items-center gap-3 p-4">
            <span className="chip-icon !mb-0">
              <Icon name="chat" />
            </span>
            <span className="font-semibold">{t("home.v3")}</span>
          </div>
        </div>
      </section>
      <ul className="grid gap-4 md:grid-cols-3">
        {features.map((f) => (
          <li key={f.key} className="card">
            <span className="chip-icon">
              <Icon name={f.icon} />
            </span>
            <h2 className="!mb-1 !text-lg">{t(`${f.key}.title`)}</h2>
            <p className="text-muted">{t(`${f.key}.text`)}</p>
          </li>
        ))}
      </ul>
    </>
  );
}
