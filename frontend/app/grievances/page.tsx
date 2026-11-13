import Link from "next/link";
import { api } from "@/lib/api";
import { formatDateTime, getLocale, getT, titled } from "@/lib/i18n";
import { requireUser } from "@/lib/session";

export const generateMetadata = titled("grievance.inbox.title");

type Row = { id: number; reference: string; category: string; subject: string; status: string; received_at: string; is_anonymous: boolean; escalation_flagged: boolean; working_days_under_review: number | null };

export default async function InboxPage() {
  const [t, locale] = await Promise.all([getT(), getLocale()]);
  await requireUser("grievance_officer");
  const result = await api<Row[]>("/grievances");
  const rows = result.ok ? result.data : [];
  return (
    <>
      <h1>{t("grievance.inbox.title")}</h1>
      {rows.length === 0 ? <p>{t("grievance.inbox.none")}</p> : (
        <div className="overflow-x-auto">
          <table className="table">
            <caption>{t("grievance.inbox.caption")}</caption>
            <thead><tr>
              <th scope="col">{t("grievance.reference")}</th><th scope="col">{t("field.subject")}</th>
              <th scope="col">{t("field.category")}</th><th scope="col">{t("track.status")}</th><th scope="col">{t("audit.when")}</th>
            </tr></thead>
            <tbody>{rows.map((r) => (
              <tr key={r.id}>
                <th scope="row"><Link href={`/grievances/${r.id}`}>{r.reference}</Link></th>
                <td>{r.subject}</td><td>{t(`category.${r.category}`)}</td>
                <td>{t(`gstatus.${r.status}`)}{r.escalation_flagged && <strong className="text-danger"> ({t("grievance.flagged")})</strong>}</td>
                <td>{formatDateTime(r.received_at, locale)}</td>
              </tr>))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
