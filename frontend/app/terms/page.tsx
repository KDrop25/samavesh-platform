import { addTerm } from "@/app/actions";
import { Field, Form } from "@/components/Form";
import { api } from "@/lib/api";
import { formatDate, getLocale, getT, titled } from "@/lib/i18n";
import { requireUser } from "@/lib/session";

export const generateMetadata = titled("terms.title");

type Term = { id: number; name: string; start_date: string; end_date: string };

export default async function TermsPage() {
  const [t, locale] = await Promise.all([getT(), getLocale()]);
  await requireUser("nodal_officer");
  const result = await api<Term[]>("/terms");
  const terms = result.ok ? result.data : [];

  return (
    <>
      <h1>{t("terms.title")}</h1>
      {terms.length === 0 ? (
        <p>{t("terms.none")}</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="table">
            <caption>{t("terms.caption")}</caption>
            <thead>
              <tr>
                <th scope="col">{t("field.name")}</th>
                <th scope="col">{t("field.start_date")}</th>
                <th scope="col">{t("field.end_date")}</th>
              </tr>
            </thead>
            <tbody>
              {terms.map((term) => (
                <tr key={term.id}>
                  <th scope="row">{term.name}</th>
                  <td>{formatDate(term.start_date, locale)}</td>
                  <td>{formatDate(term.end_date, locale)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <section aria-labelledby="add-term" className="mt-12 max-w-md">
        <h2 id="add-term">{t("terms.add")}</h2>
        <Form
          action={addTerm}
          submitLabel={t("terms.submit")}
          pendingLabel={t("form.pending")}
          errorTitle={t("form.errorSummary")}
        >
          <Field name="name" label={t("field.name")} hint={t("hint.name")} maxLength={80} />
          <Field name="start_date" label={t("field.start_date")} type="date" />
          <Field name="end_date" label={t("field.end_date")} type="date" />
        </Form>
      </section>
    </>
  );
}
