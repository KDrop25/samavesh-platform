import Link from "next/link";
import { decidePlan } from "@/app/actions";
import { Field, Form, RadioGroup } from "@/components/Form";
import { PageNotice } from "@/components/PageNotice";
import { api } from "@/lib/api";
import { formatDate, formatDateTime, getLocale, getT, titled } from "@/lib/i18n";
import { requireUser } from "@/lib/session";

export const generateMetadata = titled("approvals.title");

type Pending = {
  id: number;
  version: number;
  supersedes_plan_id: number | null;
  student_id: number;
  student_name: string;
  start_date: string;
  review_date: string;
  notes: string | null;
  drafted_by: string;
  submitted_at: string;
  items: { id: number; type: string; details: string | null; interval_days: number | null }[];
};

/** Plans waiting for a decision. A plan is inactive until a nodal officer approves it here. */
export default async function ApprovalsPage({ searchParams }: PageProps<"/approvals">) {
  const [t, locale, query] = await Promise.all([getT(), getLocale(), searchParams]);
  const user = await requireUser("nodal_officer", "administrator");
  const result = await api<Pending[]>("/approvals");
  const plans = result.ok ? result.data : [];
  const canDecide = user.role === "nodal_officer";

  return (
    <>
      <h1>{t("approvals.title")}</h1>
      <PageNotice query={query} />
      {!canDecide && <p className="mb-6">{t("approvals.readOnly")}</p>}
      {!result.ok && (
        <p className="notice notice-error" role="alert">
          {t("error.api_unreachable")}
        </p>
      )}
      {result.ok && plans.length === 0 && <p>{t("approvals.none")}</p>}

      {plans.map((plan) => (
        <section key={plan.id} aria-labelledby={`pending-${plan.id}`} className="card mb-8">
          <h2 id={`pending-${plan.id}`}>
            {t("approvals.heading", { id: plan.id, version: plan.version, name: plan.student_name })}
          </h2>
          {plan.supersedes_plan_id && <p className="mb-3">{t("approvals.replaces", { id: plan.supersedes_plan_id })}</p>}
          <dl className="mb-4 grid gap-x-6 gap-y-1 sm:grid-cols-[10rem_1fr]">
            <dt className="font-semibold">{t("plans.draftedBy")}</dt>
            <dd>{plan.drafted_by}</dd>
            <dt className="font-semibold">{t("approvals.submitted")}</dt>
            <dd>{formatDateTime(plan.submitted_at, locale)}</dd>
            <dt className="font-semibold">{t("plans.start")}</dt>
            <dd>{formatDate(plan.start_date, locale)}</dd>
            <dt className="font-semibold">{t("plans.review")}</dt>
            <dd>{formatDate(plan.review_date, locale)}</dd>
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
                </tr>
              </thead>
              <tbody>
                {plan.items.map((item) => (
                  <tr key={item.id}>
                    <th scope="row">{t(`type.${item.type}`)}</th>
                    <td className="whitespace-pre-wrap">{item.details ?? "–"}</td>
                    <td>{item.interval_days ? t("plans.every", { n: item.interval_days }) : t("plans.standing")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="my-4">
            <Link href={`/students/${plan.student_id}/plans`}>{t("approvals.view", { name: plan.student_name })}</Link>
          </p>
          {canDecide && (
            <div className="max-w-md">
              <Form
                action={decidePlan.bind(null, plan.id)}
                submitLabel={t("approvals.submit", { id: plan.id })}
                pendingLabel={t("form.pending")}
                errorTitle={t("form.errorSummary")}
              >
                <RadioGroup
                  name="decision"
                  legend={t("field.decision")}
                  defaultValue="approved"
                  options={[
                    { value: "approved", label: t("decision.approved") },
                    { value: "rejected", label: t("decision.rejected") },
                  ]}
                />
                <Field
                  name="reason"
                  label={t("field.reason")}
                  hint={t("hint.decisionReason")}
                  type="textarea"
                  optional={t("form.optional")}
                  maxLength={2000}
                />
              </Form>
            </div>
          )}
        </section>
      ))}
    </>
  );
}
