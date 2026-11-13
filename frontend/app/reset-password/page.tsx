import Link from "next/link";
import { forgotPassword, resetPassword } from "@/app/actions";
import { Field, Form } from "@/components/Form";
import { getT, titled } from "@/lib/i18n";

export const generateMetadata = titled("reset.title");

export default async function ResetPasswordPage({ searchParams }: PageProps<"/reset-password">) {
  const [t, params] = await Promise.all([getT(), searchParams]);
  const email = typeof params.email === "string" ? params.email : "";
  const formLabels = { pendingLabel: t("form.pending"), errorTitle: t("form.errorSummary") };

  return (
    <div className="max-w-md">
      <h1>{t("reset.title")}</h1>
      {email ? (
        <>
          <p className="notice">{t("reset.sent", { email })}</p>
          <Form action={resetPassword} submitLabel={t("reset.submit")} {...formLabels}>
            <input type="hidden" name="email" value={email} />
            <Field
              name="code"
              label={t("field.code")}
              hint={t("hint.code")}
              inputMode="numeric"
              autoComplete="one-time-code"
              maxLength={6}
            />
            <Field
              name="new_password"
              label={t("field.new_password")}
              type="password"
              autoComplete="new-password"
              hint={t("hint.password")}
            />
          </Form>
          {process.env.NODE_ENV !== "production" && (
            <p className="mt-6">
              <Link href="/dev/outbox">{t("verify.outbox")}</Link>
            </p>
          )}
        </>
      ) : (
        <>
          <p className="mb-6">{t("reset.intro")}</p>
          <Form action={forgotPassword} submitLabel={t("reset.send")} {...formLabels}>
            <Field name="email" label={t("field.email")} type="email" autoComplete="email" inputMode="email" />
          </Form>
        </>
      )}
    </div>
  );
}
