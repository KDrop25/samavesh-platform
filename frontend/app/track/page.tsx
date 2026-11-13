import { api } from "@/lib/api";
import { formatDateTime, getLocale, getT, titled } from "@/lib/i18n";

export const generateMetadata = titled("track.title");

type Tracked = { reference: string; category: string; status: string; events: { status: string; at: string; public_note: string | null }[] };

/** Public status check: reference only, no sign-in. A plain GET form, so it works without JavaScript. */
export default async function TrackPage({ searchParams }: PageProps<"/track">) {
  const [t, locale, query] = await Promise.all([getT(), getLocale(), searchParams]);
  const reference = typeof query.reference === "string" ? query.reference.trim().slice(0, 30) : "";
  const result = reference ? await api<Tracked>(`/grievances/track/${encodeURIComponent(reference)}`, { token: null }) : null;

  return (
    <div className="max-w-xl">
      <h1>{t("track.title")}</h1>
      <p className="mb-6">{t("track.intro")}</p>
      <form method="get" className="mb-8 flex flex-col gap-4">
        <div>
          <label htmlFor="reference" className="mb-1 block font-semibold">{t("grievance.reference")}</label>
          <p id="reference-hint" className="mb-1 text-muted">{t("track.hint")}</p>
          <input id="reference" name="reference" defaultValue={reference} className="input" required autoComplete="off" aria-describedby="reference-hint" />
        </div>
        <div><button type="submit" className="btn">{t("track.submit")}</button></div>
      </form>
      {result && !result.ok && (
        <p role="alert" className="notice notice-error">{t(result.code === "reference_not_found" ? "error.reference_not_found" : "error.too_many_requests")}</p>
      )}
      {result?.ok && (
        <section aria-labelledby="result-title" aria-live="polite">
          <h2 id="result-title">{result.data.reference}</h2>
          <p className="mb-4"><strong>{t("track.status")}:</strong> {t(`gstatus.${result.data.status}`)}</p>
          <ol className="flex flex-col gap-3">
            {result.data.events.map((e, i) => (
              <li key={i} className="card">
                <strong>{t(`gstatus.${e.status}`)}</strong> – {formatDateTime(e.at, locale)}
                {e.public_note && <p className="mt-1">{e.public_note}</p>}
              </li>
            ))}
          </ol>
        </section>
      )}
    </div>
  );
}
