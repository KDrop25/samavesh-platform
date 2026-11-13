import Link from "next/link";
import { notFound } from "next/navigation";
import { deleteComplianceItem, deleteEvidence, saveComplianceItem } from "@/app/actions";
import { ComplianceFields, type ComplianceItem } from "@/app/compliance/fields";
import { Form } from "@/components/Form";
import { PageNotice, UploadNotice } from "@/components/PageNotice";
import { UploadForm } from "@/components/UploadForm";
import { api } from "@/lib/api";
import { getT, titled } from "@/lib/i18n";
import { requireUser } from "@/lib/session";

export const generateMetadata = titled("compliance.title");

/** Edit one checklist item and manage its evidence. Nodal officer only. */
export default async function ComplianceItemPage({ params, searchParams }: PageProps<"/compliance/[id]">) {
  const [t, { id }, query] = await Promise.all([getT(), params, searchParams]);
  await requireUser("nodal_officer");
  if (!/^\d+$/.test(id)) notFound();
  const [result, upload] = await Promise.all([
    api<ComplianceItem>(`/compliance/${id}`),
    api<{ token: string }>("/files/tokens/upload", {
      method: "POST",
      body: { purpose: "evidence", ref_id: Number(id), return_to: `/compliance/${id}` },
    }),
  ]);
  if (!result.ok) notFound();
  const item = result.data;
  const formLabels = { pendingLabel: t("form.pending"), errorTitle: t("form.errorSummary") };

  return (
    <div className="max-w-xl">
      <h1>{t("compliance.editTitle", { id: item.id })}</h1>
      <p className="mb-6">
        <Link href="/compliance">{t("compliance.back")}</Link>
      </p>
      <PageNotice query={query} />
      <UploadNotice query={query} success="evidence.uploaded" />

      <Form action={saveComplianceItem.bind(null, item.id)} submitLabel={t("compliance.save")} {...formLabels}>
        <ComplianceFields item={item} />
      </Form>

      <section aria-labelledby="evidence-title" className="mt-12">
        <h2 id="evidence-title">{t("evidence.title")}</h2>
        {item.evidence.length === 0 ? (
          <p>{t("evidence.none")}</p>
        ) : (
          <ul className="flex flex-col gap-3">
            {item.evidence.map((file) => (
              <li key={file.id} className="card flex flex-wrap items-center justify-between gap-3">
                <a href={`/files/${file.file_id}`}>{t("evidence.download", { name: file.filename })}</a>
                <Form
                  action={deleteEvidence.bind(null, item.id, file.id)}
                  submitLabel={t("evidence.remove", { name: file.filename })}
                  secondary
                  {...formLabels}
                />
              </li>
            ))}
          </ul>
        )}
        {upload.ok && (
          <UploadForm
            token={upload.data.token}
            label={t("evidence.upload.label")}
            hint={t("evidence.upload.hint")}
            submit={t("evidence.upload.submit")}
          />
        )}
      </section>

      <section aria-labelledby="delete-title" className="mt-12">
        <h2 id="delete-title">{t("compliance.delete.title")}</h2>
        <p className="mb-4">{t("compliance.delete.text")}</p>
        <Form
          action={deleteComplianceItem.bind(null, item.id)}
          submitLabel={t("compliance.delete", { id: item.id })}
          secondary
          {...formLabels}
        />
      </section>
    </div>
  );
}
