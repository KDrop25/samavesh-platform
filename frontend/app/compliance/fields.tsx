import { Field } from "@/components/Form";
import { getT } from "@/lib/i18n";

export const COMPLIANCE_STATUSES = ["compliant", "partially", "not_compliant", "not_applicable"];

export type ComplianceItem = {
  id: number;
  description: string;
  source_obligation: string;
  due_date: string;
  status: string;
  reason: string | null;
  overdue: boolean;
  due_soon: boolean;
  evidence: { id: number; file_id: number; filename: string }[];
};

/** Fields shared by the "add item" and "edit item" forms. */
export async function ComplianceFields({ item }: { item?: ComplianceItem }) {
  const t = await getT();
  return (
    <>
      <Field
        name="description"
        label={t("field.description")}
        hint={t("hint.description")}
        type="textarea"
        defaultValue={item?.description ?? ""}
        maxLength={2000}
      />
      <Field
        name="source_obligation"
        label={t("field.source_obligation")}
        hint={t("hint.source_obligation")}
        defaultValue={item?.source_obligation ?? ""}
        maxLength={300}
      />
      <Field name="due_date" label={t("field.due_date")} type="date" defaultValue={item?.due_date ?? ""} />
      <Field
        name="status"
        label={t("field.status")}
        defaultValue={item?.status ?? "not_compliant"}
        options={COMPLIANCE_STATUSES.map((value) => ({ value, label: t(`compliance.status.${value}`) }))}
      />
      <Field
        name="reason"
        label={t("field.reason")}
        hint={t("hint.reason")}
        type="textarea"
        optional={t("form.optional")}
        defaultValue={item?.reason ?? ""}
        maxLength={2000}
      />
    </>
  );
}
