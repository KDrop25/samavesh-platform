import Link from "next/link";
import { notFound } from "next/navigation";
import { changeGrievanceStatus } from "@/app/actions";
import { Field, Form } from "@/components/Form";
import { api } from "@/lib/api";
import { formatDateTime, getLocale, getT, titled } from "@/lib/i18n";
import { requireUser } from "@/lib/session";

export const generateMetadata = titled("grievance.case.title");

type Case = {
  id: number; reference: string; category: string; subject: string; description: string; status: string;
  is_anonymous: boolean; complainant_name: string | null; contact_email: string | null; has_account: boolean;
  escalation_flagged: boolean; working_days_under_review: number | null; escalation_limit: number; next_statuses: string[];
  events: { status: string; at: string; public_note: string | null; internal_note: string | null; officer: string | null }[];
};

/** Grievance officer only: the one place the complainant's identity is shown. */
export default async function CasePage({ params }: PageProps<"/grievances/[id]">) {
  const [t, locale, { id }] = await Promise.all([getT(), getLocale(), params]);
  await requireUser("grievance_officer");
  if (!/^\d+$/.test(id)) notFound();
  const result = await api<Case>(`/grievances/${id}`);
  if (!result.ok) notFound();
  const c = result.data;
  return (
    <div className="max-w-3xl">
      <h1>{c.reference}</h1>
      <p className="mb-6"><Link href="/grievances">{t("grievance.back")}</Link></p>
      <dl className="mb-8 grid gap-x-6 gap-y-1 sm:grid-cols-[12rem_1fr]">
        <dt className="font-semibold">{t("track.status")}</dt><dd>{t(`gstatus.${c.status}`)}{c.escalation_flagged && <strong className="text-danger"> ({t("grievance.flagged")})</strong>}</dd>
        {c.working_days_under_review !== null && (<><dt className="font-semibold">{t("grievance.daysUnderReview")}</dt><dd>{t("grievance.daysOf", { n: c.working_days_under_review, limit: c.escalation_limit })}</dd></>)}
        <dt className="font-semibold">{t("field.category")}</dt><dd>{t(`category.${c.category}`)}</dd>
        <dt className="font-semibold">{t("field.subject")}</dt><dd>{c.subject}</dd>
        <dt className="font-semibold">{t("field.description_g")}</dt><dd className="whitespace-pre-wrap">{c.description}</dd>
        <dt className="font-semibold">{t("grievance.complainant")}</dt>
        <dd>{c.is_anonymous ? t("grievance.anonymousComplainant") : `${c.complainant_name}${c.has_account ? ` (${t("grievance.hasAccount")})` : ""}`}</dd>
        {c.contact_email && (<><dt className="font-semibold">{t("field.contact_email")}</dt><dd>{c.contact_email}</dd></>)}
      </dl>
      <h2>{t("grievance.timeline")}</h2>
      <ol className="mb-8 flex flex-col gap-3">
        {c.events.map((e, i) => (
          <li key={i} className="card">
            <strong>{t(`gstatus.${e.status}`)}</strong> – {formatDateTime(e.at, locale)}{e.officer && ` – ${e.officer}`}
            {e.public_note && <p>{t("grievance.publicNote")}: {e.public_note}</p>}
            {e.internal_note && <p>{t("grievance.internalNote")}: {e.internal_note}</p>}
          </li>))}
      </ol>
      {c.next_statuses.length > 0 && (
        <section aria-labelledby="update-title" className="max-w-md">
          <h2 id="update-title">{t("grievance.update")}</h2>
          <Form action={changeGrievanceStatus.bind(null, c.id)} submitLabel={t("grievance.update.submit")} pendingLabel={t("form.pending")} errorTitle={t("form.errorSummary")}>
            <Field name="status" label={t("field.status_g")} options={c.next_statuses.map((v) => ({ value: v, label: t(`gstatus.${v}`) }))} />
            <Field name="public_note" label={t("grievance.publicNote")} hint={t("hint.publicNote")} type="textarea" optional={t("form.optional")} maxLength={2000} />
            <Field name="internal_note" label={t("grievance.internalNote")} hint={t("hint.internalNote")} type="textarea" optional={t("form.optional")} maxLength={2000} />
          </Form>
        </section>
      )}
    </div>
  );
}
