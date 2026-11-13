import Link from "next/link";
import { notFound } from "next/navigation";
import { endPlan, logProvision, revisePlan, submitPlan } from "@/app/actions";
import { Field, Form } from "@/components/Form";
import { PageNotice } from "@/components/PageNotice";
import { api } from "@/lib/api";
import { formatDate, formatDateTime, getLocale, getT, titled } from "@/lib/i18n";
import { requireUser } from "@/lib/session";

export const generateMetadata = titled("plans.title");

type Log = { provided_on: string; staff_name: string; notes: string | null };
type Item = {
  id: number;
  type: string;
  details: string | null;
  interval_days: number | null;
  last_provided_on: string | null;
  next_due_on: string | null;
  overdue: boolean;
  logs: Log[];
};
type Plan = {
  id: number;
  version: number;
  status: string;
  is_active: boolean;
  start_date: string;
  review_date: string;
  notes: string | null;
  drafted_by: string;
  items: Item[];
  decisions: { decision: string; approver: string; reason: string | null; decided_at: string }[];
};
type PlanList = { has_profile: boolean; can_draft: boolean; can_decide: boolean; plans: Plan[] };
type Term = { id: number; name: string; start_date: string; end_date: string };
type Summary = {
  term: Term;
  rows: { plan_id: number; type: string; planned: number | null; delivered: number; shortfall: number | null }[];
};

export default async function PlansPage({ params, searchParams }: PageProps<"/students/[id]/plans">) {
  const [t, locale, { id }, query] = await Promise.all([getT(), getLocale(), params, searchParams]);
  await requireUser("student", "guardian", "support_staff", "nodal_officer", "administrator");
  const [student, list, terms] = await Promise.all([
    api<{ student: { id: number; full_name: string } }>(`/students/${id}`),
    api<PlanList>(`/students/${id}/plans`),
    api<Term[]>("/terms"),
  ]);
  if (!student.ok || !list.ok) notFound();
  const { full_name: name } = student.data.student;
  const { has_profile, can_draft, can_decide, plans } = list.data;

  const termList = terms.ok ? terms.data : [];
  const termId = typeof query.term === "string" && /^\d+$/.test(query.term) ? query.term : termList[0]?.id;
  const summary = termId ? await api<Summary>(`/students/${id}/provision-summary?term_id=${termId}`) : null;

  const date = (iso: string) => formatDate(iso, locale);
  const formLabels = { pendingLabel: t("form.pending"), errorTitle: t("form.errorSummary") };
  const today = new Date().toLocaleDateString("en-CA", { timeZone: "Asia/Kolkata" }); // YYYY-MM-DD

  return (
    <>
      <h1>{t("plans.for", { name })}</h1>
      <p className="mb-6">
        <Link href={`/students/${id}`}>{t("plans.back", { name })}</Link>
      </p>
      <PageNotice query={query} />
      <p className="mb-6">{t("plans.activeNote")}</p>

      {!has_profile && <p className="notice notice-error">{t("plans.noProfile")}</p>}
      {can_draft && (
        <p className="mb-8">
          <Link href={`/students/${id}/plans/edit`} className="btn">
            {t("plans.new")}
          </Link>
        </p>
      )}
      {has_profile && plans.length === 0 && <p className="mb-8">{t("plans.none")}</p>}

      {plans.map((plan) => (
        <section key={plan.id} aria-labelledby={`plan-${plan.id}`} className="card mb-8">
          <h2 id={`plan-${plan.id}`}>{t("plans.heading", { id: plan.id, version: plan.version })}</h2>
          <dl className="mb-4 grid gap-x-6 gap-y-1 sm:grid-cols-[10rem_1fr]">
            <dt className="font-semibold">{t("plans.statusLabel")}</dt>
            <dd>
              {t(`plans.status.${plan.status}`)} – {t(plan.is_active ? "plans.active" : "plans.inactive")}
            </dd>
            <dt className="font-semibold">{t("plans.start")}</dt>
            <dd>{date(plan.start_date)}</dd>
            <dt className="font-semibold">{t("plans.review")}</dt>
            <dd>{date(plan.review_date)}</dd>
            <dt className="font-semibold">{t("plans.draftedBy")}</dt>
            <dd>{plan.drafted_by}</dd>
            {plan.notes && (
              <>
                <dt className="font-semibold">{t("plans.notes")}</dt>
                <dd className="whitespace-pre-wrap">{plan.notes}</dd>
              </>
            )}
          </dl>

          <div className="overflow-x-auto">
            <table className="table">
              <caption>{t("plans.items.caption", { id: plan.id })}</caption>
              <thead>
                <tr>
                  <th scope="col">{t("plans.items.type")}</th>
                  <th scope="col">{t("plans.items.details")}</th>
                  <th scope="col">{t("plans.items.interval")}</th>
                  <th scope="col">{t("plans.items.last")}</th>
                  <th scope="col">{t("plans.items.next")}</th>
                </tr>
              </thead>
              <tbody>
                {plan.items.map((item) => (
                  <tr key={item.id}>
                    <th scope="row">{t(`type.${item.type}`)}</th>
                    <td className="whitespace-pre-wrap">{item.details ?? "–"}</td>
                    <td>{item.interval_days ? t("plans.every", { n: item.interval_days }) : t("plans.standing")}</td>
                    <td>{item.last_provided_on ? date(item.last_provided_on) : t("plans.never")}</td>
                    <td>
                      {item.next_due_on ? date(item.next_due_on) : "–"}
                      {item.overdue && <strong className="text-danger"> ({t("plans.overdue")})</strong>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {plan.items.map((item) => {
            const type = t(`type.${item.type}`);
            return (
              <div key={item.id} className="mt-3 flex flex-col gap-3">
                {item.logs.length > 0 && (
                  <details>
                    <summary className="min-h-11 cursor-pointer font-semibold">
                      {t("provision.history", { type, n: item.logs.length })}
                    </summary>
                    <table className="table">
                      <caption className="sr-only">{t("provision.caption", { type })}</caption>
                      <thead>
                        <tr>
                          <th scope="col">{t("provision.date")}</th>
                          <th scope="col">{t("provision.staff")}</th>
                          <th scope="col">{t("provision.notes")}</th>
                        </tr>
                      </thead>
                      <tbody>
                        {item.logs.map((log, index) => (
                          <tr key={index}>
                            <td>{date(log.provided_on)}</td>
                            <td>{log.staff_name}</td>
                            <td>{log.notes ?? "–"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </details>
                )}
                {can_draft && plan.is_active && (
                  <details>
                    <summary className="min-h-11 cursor-pointer font-semibold">{t("provision.log.title", { type })}</summary>
                    <div className="max-w-md pt-2">
                      <Form
                        action={logProvision.bind(null, Number(id), item.id)}
                        submitLabel={t("provision.log.submit")}
                        {...formLabels}
                      >
                        <Field name="provided_on" label={t("field.provided_on")} type="date" defaultValue={today} />
                        <Field name="notes" label={t("field.notes")} type="textarea" optional={t("form.optional")} maxLength={2000} />
                      </Form>
                    </div>
                  </details>
                )}
              </div>
            );
          })}

          {plan.decisions.length > 0 && (
            <div className="mt-4">
              <h3 className="mb-1">{t("decisions.title", { id: plan.id })}</h3>
              <ul className="list-disc ps-5">
                {plan.decisions.map((decision, index) => (
                  <li key={index}>
                    {t("decisions.entry", {
                      decision: t(`decision.label.${decision.decision}`),
                      approver: decision.approver,
                      date: formatDateTime(decision.decided_at, locale),
                    })}
                    {decision.reason && <> – {t("decisions.reason", { reason: decision.reason })}</>}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {plan.status === "approved" && (can_draft || can_decide) && (
            <div className="mt-5 flex flex-wrap items-start gap-3">
              {can_draft && (
                <Form
                  action={revisePlan.bind(null, Number(id), plan.id)}
                  submitLabel={t("plans.revise", { id: plan.id })}
                  secondary
                  {...formLabels}
                />
              )}
              {can_decide && (
                <Form
                  action={endPlan.bind(null, Number(id), plan.id)}
                  submitLabel={t("plans.end", { id: plan.id })}
                  secondary
                  {...formLabels}
                />
              )}
            </div>
          )}

          {can_draft && (plan.status === "draft" || plan.status === "rejected") && (
            <div className="mt-5 flex flex-wrap items-start gap-3">
              <Link href={`/students/${id}/plans/edit?plan=${plan.id}`} className="btn btn-secondary">
                {t("plans.edit", { id: plan.id })}
              </Link>
              {plan.status === "draft" && (
                <Form
                  action={submitPlan.bind(null, Number(id), plan.id)}
                  submitLabel={t("plans.submit", { id: plan.id })}
                  {...formLabels}
                />
              )}
            </div>
          )}
        </section>
      ))}

      <section aria-labelledby="summary-title">
        <h2 id="summary-title">{t("summary.title")}</h2>
        {termList.length === 0 ? (
          <p>{t("summary.noTerms")}</p>
        ) : (
          <>
            <form method="get" className="mb-5 flex flex-wrap items-end gap-3">
              <div>
                <label htmlFor="term" className="mb-1 block font-semibold">
                  {t("summary.term")}
                </label>
                <select id="term" name="term" defaultValue={String(termId)} className="input">
                  {termList.map((term) => (
                    <option key={term.id} value={term.id}>
                      {term.name}
                    </option>
                  ))}
                </select>
              </div>
              <button type="submit" className="btn btn-secondary">
                {t("summary.show")}
              </button>
            </form>
            {summary?.ok && summary.data.rows.length === 0 && <p>{t("summary.empty")}</p>}
            {summary?.ok && summary.data.rows.length > 0 && (
              <div className="overflow-x-auto">
                <table className="table">
                  <caption>
                    {t("summary.caption", {
                      term: summary.data.term.name,
                      start: date(summary.data.term.start_date),
                      end: date(summary.data.term.end_date),
                    })}
                  </caption>
                  <thead>
                    <tr>
                      <th scope="col">{t("plans.items.type")}</th>
                      <th scope="col">{t("summary.planned")}</th>
                      <th scope="col">{t("summary.delivered")}</th>
                      <th scope="col">{t("summary.shortfall")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {summary.data.rows.map((row, index) => (
                      <tr key={index}>
                        <th scope="row">{t(`type.${row.type}`)}</th>
                        <td>{row.planned ?? t("summary.na")}</td>
                        <td>{row.delivered}</td>
                        <td>{row.shortfall ?? t("summary.na")}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </section>
    </>
  );
}
