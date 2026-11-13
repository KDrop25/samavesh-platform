import { submitGrievance } from "@/app/actions";
import { Field, Form, RadioGroup } from "@/components/Form";
import { GRIEVANCE_CATEGORIES as CATEGORIES } from "@/lib/constants";
import { getT, titled } from "@/lib/i18n";
import { getUser } from "@/lib/session";

export const generateMetadata = titled("grievance.new.title");

/** Open to everyone, signed in or not. */
export default async function NewGrievancePage() {
  const [t, user] = await Promise.all([getT(), getUser()]);
  return (
    <div className="max-w-xl">
      <h1>{t("grievance.new.title")}</h1>
      <p className="mb-6">{t("grievance.new.intro")}</p>
      <Form action={submitGrievance} submitLabel={t("grievance.new.submit")} pendingLabel={t("form.pending")} errorTitle={t("form.errorSummary")}>
        <Field name="category" label={t("field.category")} options={CATEGORIES.map((v) => ({ value: v, label: t(`category.${v}`) }))} />
        <Field name="subject" label={t("field.subject")} maxLength={200} />
        <Field name="description" label={t("field.description_g")} type="textarea" maxLength={5000} />
        <RadioGroup
          name="anonymous"
          legend={t("grievance.new.identity")}
          defaultValue="no"
          options={[
            { value: "no", label: t("grievance.new.named") },
            { value: "yes", label: t("grievance.new.anonymous") },
          ]}
        />
        <p className="text-muted">{t("grievance.new.identityHint")}</p>
        <Field name="complainant_name" label={t("field.complainant_name")} optional={user ? t("form.optional") : undefined} defaultValue={user?.full_name ?? ""} autoComplete="name" maxLength={120} />
        <Field name="contact_email" label={t("field.contact_email")} hint={t("hint.contact_email")} type="email" optional={t("form.optional")} defaultValue={user?.email ?? ""} />
      </Form>
    </div>
  );
}
