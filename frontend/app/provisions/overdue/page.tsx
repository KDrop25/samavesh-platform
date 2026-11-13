import Link from "next/link";
import { api } from "@/lib/api";
import { formatDate, getLocale, getT, titled } from "@/lib/i18n";
import { requireUser } from "@/lib/session";

export const generateMetadata = titled("overdue.title");

type Row = {
  student_id: number;
  student_name: string;
  plan_id: number;
  type: string;
  interval_days: number;
  last_provided_on: string | null;
  due_on: string;
  days_overdue: number;
};

export default async function OverduePage() {
  const [t, locale] = await Promise.all([getT(), getLocale()]);
  await requireUser("support_staff", "nodal_officer", "administrator");
  const result = await api<Row[]>("/provisions/overdue");
  const rows = result.ok ? result.data : [];

  return (
    <>
      <h1>{t("overdue.title")}</h1>
      {!result.ok && (
        <p className="notice notice-error" role="alert">
          {t("error.api_unreachable")}
        </p>
      )}
      {result.ok && rows.length === 0 ? (
        <p>{t("overdue.none")}</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="table">
            <caption>{t("overdue.caption")}</caption>
            <thead>
              <tr>
                <th scope="col">{t("overdue.student")}</th>
                <th scope="col">{t("plans.items.type")}</th>
                <th scope="col">{t("plans.items.interval")}</th>
                <th scope="col">{t("plans.items.last")}</th>
                <th scope="col">{t("overdue.due")}</th>
                <th scope="col">{t("overdue.days")}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, index) => (
                <tr key={index}>
                  <th scope="row">
                    <Link href={`/students/${row.student_id}/plans`}>{row.student_name}</Link>
                  </th>
                  <td>{t(`type.${row.type}`)}</td>
                  <td>{t("plans.every", { n: row.interval_days })}</td>
                  <td>{row.last_provided_on ? formatDate(row.last_provided_on, locale) : t("plans.never")}</td>
                  <td>{formatDate(row.due_on, locale)}</td>
                  <td>{row.days_overdue}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
