import { addHoliday, removeHoliday, saveEscalationSettings } from "@/app/actions";
import { CheckboxGroup, Field, Form } from "@/components/Form";
import { PageNotice } from "@/components/PageNotice";
import { api } from "@/lib/api";
import { formatDate, getLocale, getT, titled } from "@/lib/i18n";
import { requireUser } from "@/lib/session";

export const generateMetadata = titled("escalation.title");
const DAYS = [0, 1, 2, 3, 4, 5, 6];
type S = { working_weekdays: number[]; escalation_working_days: number; holidays: { id: number; day: string; name: string }[] };

export default async function EscalationSettingsPage({ searchParams }: PageProps<"/escalation-settings">) {
  const [t, locale, query] = await Promise.all([getT(), getLocale(), searchParams]);
  await requireUser("administrator", "grievance_officer");
  const result = await api<S>("/settings");
  if (!result.ok) return <h1>{t("escalation.title")}</h1>;
  const s = result.data;
  const labels = { pendingLabel: t("form.pending"), errorTitle: t("form.errorSummary") };
  return (
    <div className="max-w-xl">
      <h1>{t("escalation.title")}</h1>
      <PageNotice query={query} />
      <p className="mb-6">{t("escalation.intro")}</p>
      <Form action={saveEscalationSettings} submitLabel={t("settings.save")} {...labels}>
        <Field name="escalation_working_days" label={t("escalation.days")} inputMode="numeric" defaultValue={String(s.escalation_working_days)} maxLength={3} />
        <CheckboxGroup name="working_weekdays" legend={t("escalation.weekdays")} options={DAYS.map((d) => ({ value: String(d), label: t(`weekday.${d}`) }))} defaultValues={s.working_weekdays.map(String)} />
      </Form>
      <section aria-labelledby="hol" className="mt-12">
        <h2 id="hol">{t("escalation.holidays")}</h2>
        {s.holidays.length === 0 ? <p>{t("escalation.noHolidays")}</p> : (
          <ul className="flex flex-col gap-3">{s.holidays.map((h) => (
            <li key={h.id} className="card flex flex-wrap items-center justify-between gap-3">
              <span>{formatDate(h.day, locale)} – {h.name}</span>
              <Form action={removeHoliday.bind(null, h.id)} submitLabel={t("escalation.removeHoliday", { name: h.name })} secondary {...labels} />
            </li>))}
          </ul>)}
        <div className="mt-6">
          <Form action={addHoliday} submitLabel={t("escalation.addHoliday")} {...labels}>
            <Field name="day" label={t("field.day")} type="date" />
            <Field name="name" label={t("field.holiday_name")} maxLength={120} />
          </Form>
        </div>
      </section>
    </div>
  );
}
