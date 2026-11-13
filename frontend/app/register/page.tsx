import Link from "next/link";
import { redirect } from "next/navigation";
import { register } from "@/app/actions";
import { Field, Form, RadioGroup } from "@/components/Form";
import { getT, titled } from "@/lib/i18n";
import { getUser } from "@/lib/session";

export const generateMetadata = titled("register.title");

export default async function RegisterPage() {
  const [t, user] = await Promise.all([getT(), getUser()]);
  if (user) redirect("/dashboard");

  return (
    <div className="max-w-md">
      <h1>{t("register.title")}</h1>
      <p className="mb-6">{t("register.intro")}</p>
      <Form
        action={register}
        submitLabel={t("register.submit")}
        pendingLabel={t("form.pending")}
        errorTitle={t("form.errorSummary")}
      >
        <Field name="full_name" label={t("field.full_name")} autoComplete="name" maxLength={120} />
        <Field name="email" label={t("field.email")} type="email" autoComplete="email" inputMode="email" />
        <Field
          name="password"
          label={t("field.password")}
          type="password"
          autoComplete="new-password"
          hint={t("hint.password")}
        />
        <RadioGroup
          name="role"
          legend={t("field.role")}
          defaultValue="student"
          options={[
            { value: "student", label: t("role.student") },
            { value: "guardian", label: t("role.guardian") },
          ]}
        />
        <Field
          name="date_of_birth"
          label={t("field.date_of_birth")}
          type="date"
          autoComplete="bday"
          optional={t("form.optional")}
          hint={t("hint.date_of_birth")}
        />
      </Form>
      <p className="mt-6">
        <Link href="/login">{t("register.haveAccount")}</Link>
      </p>
    </div>
  );
}
