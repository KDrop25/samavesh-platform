import Link from "next/link";
import { notFound } from "next/navigation";
import { savePlan } from "@/app/actions";
import { Checkbox, Field, Form } from "@/components/Form";
import { api } from "@/lib/api";
import { ACCOMMODATION_TYPES } from "@/lib/constants";
import { getT, titled } from "@/lib/i18n";
import { requireUser } from "@/lib/session";

export const generateMetadata = titled("plans.form.newTitle");

type Plan = {
  id: number;
  status: string;
  student_id: number;
  start_date: string;
  review_date: string;
  notes: string | null;
  items: { type: string; details: string | null; interval_days: number | null }[];
};

/** New plan, or (with ?plan=ID) edit a draft or rejected plan. Drafted by assigned support staff. */
export default async function PlanEditPage({ params, searchParams }: PageProps<"/students/[id]/plans/edit">) {
  const [t, { id }, query] = await Promise.all([getT(), params, searchParams]);
  await requireUser("support_staff");
  const student = await api<{ student: { id: number; full_name: string } }>(`/students/${id}`);
  if (!student.ok) notFound();

  const planId = typeof query.plan === "string" && /^\d+$/.test(query.plan) ? Number(query.plan) : null;
  const existing = planId ? await api<Plan>(`/plans/${planId}`) : null;
  if (existing && (!existing.ok || existing.data.student_id !== Number(id))) notFound();
  const plan = existing?.ok ? existing.data : null;
  const optional = t("form.optional");

  return (
    <div className="max-w-2xl">
      <h1>{plan ? t("plans.form.editTitle", { id: plan.id }) : t("plans.form.newTitle")}</h1>
      <p className="mb-6">
        <Link href={`/students/${id}/plans`}>{t("plans.back", { name: student.data.student.full_name })}</Link>
      </p>
      <Form
        action={savePlan.bind(null, Number(id), planId)}
        submitLabel={t("plans.form.save")}
        pendingLabel={t("form.pending")}
        errorTitle={t("form.errorSummary")}
      >
        <Field name="start_date" label={t("field.start_date")} type="date" defaultValue={plan?.start_date ?? ""} />
        <Field name="review_date" label={t("field.review_date")} type="date" defaultValue={plan?.review_date ?? ""} />
        <Field name="notes" label={t("field.notes")} type="textarea" optional={optional} defaultValue={plan?.notes ?? ""} maxLength={4000} />

        <h2 className="mb-0 mt-4">{t("plans.form.items")}</h2>
        <p>{t("plans.form.itemsHint")}</p>
        {ACCOMMODATION_TYPES.map((type) => {
          const item = plan?.items.find((entry) => entry.type === type);
          const name = t(`type.${type}`);
          return (
            <fieldset key={type} className="card flex flex-col gap-3">
              <legend className="px-1 font-bold">{name}</legend>
              <Checkbox name={`include_${type}`} label={t("plans.form.include")} defaultChecked={Boolean(item)} />
              <Field
                name={`details_${type}`}
                label={`${name}: ${t("field.details")}`}
                type="textarea"
                optional={optional}
                defaultValue={item?.details ?? ""}
                maxLength={2000}
              />
              <Field
                name={`interval_${type}`}
                label={`${name}: ${t("field.interval_days")}`}
                optional={optional}
                inputMode="numeric"
                defaultValue={String(item?.interval_days ?? "")}
                maxLength={3}
              />
            </fieldset>
          );
        })}
      </Form>
    </div>
  );
}
