import Link from "next/link";
import { saveComplianceItem } from "@/app/actions";
import { ComplianceFields, COMPLIANCE_STATUSES, type ComplianceItem } from "@/app/compliance/fields";
import { Form } from "@/components/Form";
import { PageNotice } from "@/components/PageNotice";
import { api } from "@/lib/api";
import { formatDate, getLocale, getT, titled } from "@/lib/i18n";
import { requireUser } from "@/lib/session";

export const generateMetadata = titled("compliance.title");

type Checklist = {
  can_edit: boolean;
  summary: Record<string, number | null>;
  items: ComplianceItem[];
};

export default async function CompliancePage({ searchParams }: PageProps<"/compliance">) {
  const [t, locale, query] = await Promise.all([getT(), getLocale(), searchParams]);
  await requireUser("support_staff", "nodal_officer", "administrator");
  const result = await api<Checklist>("/compliance");
  if (!result.ok) {
    return (
      <>
        <h1>{t("compliance.title")}</h1>
        <p className="notice notice-error" role="alert">
          {t("error.api_unreachable")}
        </p>
      </>
    );
  }
  const { can_edit, summary, items } = result.data;
  const rate = summary.percent_compliant;
  const figures: [string, string | number][] = [
    [t("compliance.total"), summary.total ?? 0],
    ...COMPLIANCE_STATUSES.map((status): [string, number] => [t(`compliance.status.${status}`), summary[status] ?? 0]),
    [t("compliance.overdue"), summary.overdue ?? 0],
    [t("compliance.dueSoon"), summary.due_soon ?? 0],
    [t("compliance.rate"), rate === null ? t("compliance.rateNone") : `${rate}%`],
  ];

  return (
    <>
      <h1>{t("compliance.title")}</h1>
      <PageNotice query={query} />
      <p className="mb-8 text-muted">{t("compliance.disclaimer")}</p>

      <section aria-labelledby="summary-title" className="mb-10">
        <h2 id="summary-title">{t("compliance.summary")}</h2>
        <dl className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {figures.map(([label, value]) => (
            <div key={label} className="card">
              <dt className="text-muted">{label}</dt>
              <dd className="text-2xl font-bold">{value}</dd>
            </div>
          ))}
        </dl>
      </section>

      {items.length === 0 ? (
        <p>{t("compliance.none")}</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="table">
            <caption>{t("compliance.caption")}</caption>
            <thead>
              <tr>
                <th scope="col">{t("compliance.item")}</th>
                <th scope="col">{t("compliance.source")}</th>
                <th scope="col">{t("compliance.due")}</th>
                <th scope="col">{t("compliance.statusCol")}</th>
                <th scope="col">{t("compliance.reason")}</th>
                <th scope="col">{t("compliance.evidence")}</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id}>
                  <th scope="row" className="font-normal">
                    {item.description}
                    {can_edit && (
                      <>
                        <br />
                        <Link href={`/compliance/${item.id}`}>{t("compliance.edit", { id: item.id })}</Link>
                      </>
                    )}
                  </th>
                  <td>{item.source_obligation}</td>
                  <td>
                    {formatDate(item.due_date, locale)}
                    {item.overdue && <strong className="text-danger"> ({t("compliance.flag.overdue")})</strong>}
                    {item.due_soon && <strong> ({t("compliance.flag.dueSoon")})</strong>}
                  </td>
                  <td>{t(`compliance.status.${item.status}`)}</td>
                  <td>{item.reason ?? "–"}</td>
                  <td>
                    {item.evidence.length === 0 ? (
                      t("compliance.noEvidence")
                    ) : (
                      <ul>
                        {item.evidence.map((file) => (
                          <li key={file.id}>
                            <a href={`/files/${file.file_id}`}>{t("evidence.download", { name: file.filename })}</a>
                          </li>
                        ))}
                      </ul>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {can_edit && (
        <section aria-labelledby="add-title" className="mt-12 max-w-xl">
          <h2 id="add-title">{t("compliance.add")}</h2>
          <Form
            action={saveComplianceItem.bind(null, null)}
            submitLabel={t("compliance.add.submit")}
            pendingLabel={t("form.pending")}
            errorTitle={t("form.errorSummary")}
          >
            <ComplianceFields />
          </Form>
        </section>
      )}
    </>
  );
}
