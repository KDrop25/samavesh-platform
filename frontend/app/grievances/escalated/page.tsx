import { api } from "@/lib/api";
import { formatDateTime, getLocale, getT, titled } from "@/lib/i18n";
import { requireUser } from "@/lib/session";

export const generateMetadata = titled("grievance.escalated.title");

type Case = { id: number; reference: string; category: string; subject: string; description: string; status: string; escalation_flagged: boolean; events: { status: string; at: string; public_note: string | null }[] };

/** Administrator view: content and timeline only. The API never sends identity here. */
export default async function EscalatedPage() {
  const [t, locale] = await Promise.all([getT(), getLocale()]);
  await requireUser("administrator");
  const result = await api<Case[]>("/grievances/escalated");
  const cases = result.ok ? result.data : [];
  return (
    <>
      <h1>{t("grievance.escalated.title")}</h1>
      <p className="mb-6">{t("grievance.escalated.intro")}</p>
      {cases.length === 0 && <p>{t("grievance.escalated.none")}</p>}
      {cases.map((c) => (
        <section key={c.id} aria-labelledby={`c-${c.id}`} className="card mb-6">
          <h2 id={`c-${c.id}`}>{c.reference}: {c.subject}</h2>
          <p className="mb-2"><strong>{t(`gstatus.${c.status}`)}</strong>{c.escalation_flagged && ` (${t("grievance.flagged")})`} – {t(`category.${c.category}`)}</p>
          <p className="mb-3 whitespace-pre-wrap">{c.description}</p>
          <ul className="list-disc ps-5">{c.events.map((e, i) => (<li key={i}>{t(`gstatus.${e.status}`)} – {formatDateTime(e.at, locale)}{e.public_note && `: ${e.public_note}`}</li>))}</ul>
        </section>))}
    </>
  );
}
