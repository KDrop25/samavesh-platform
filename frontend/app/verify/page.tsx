import Link from "next/link";
import { redirect } from "next/navigation";
import { resendCode, verifyEmail } from "@/app/actions";
import { Field, Form } from "@/components/Form";
import { getT, titled } from "@/lib/i18n";

export const generateMetadata = titled("verify.title");

export default async function VerifyPage({ searchParams }: PageProps<"/verify">) {
  const [t, params] = await Promise.all([getT(), searchParams]);
  const email = typeof params.email === "string" ? params.email : "";
  if (!email) redirect("/register");
  const formLabels = { pendingLabel: t("form.pending"), errorTitle: t("form.errorSummary") };

  return (
    <div className="max-w-md">
      <h1>{t("verify.title")}</h1>
      <p className="mb-6">{t("verify.intro", { email })}</p>
      <Form action={verifyEmail} submitLabel={t("verify.submit")} {...formLabels}>
        <input type="hidden" name="email" value={email} />
        <Field
          name="code"
          label={t("field.code")}
          hint={t("hint.code")}
          inputMode="numeric"
          autoComplete="one-time-code"
          maxLength={6}
        />
      </Form>

      <h2 className="mt-10">{t("verify.resendTitle")}</h2>
      <Form action={resendCode} submitLabel={t("verify.resend")} secondary {...formLabels}>
        <input type="hidden" name="email" value={email} />
      </Form>
      {process.env.NODE_ENV !== "production" && (
        <p className="mt-6">
          <Link href="/dev/outbox">{t("verify.outbox")}</Link>
        </p>
      )}
    </div>
  );
}
