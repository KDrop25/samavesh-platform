import Link from "next/link";
import { redirect } from "next/navigation";
import { login } from "@/app/actions";
import { Field, Form } from "@/components/Form";
import { getT, titled } from "@/lib/i18n";
import { getUser } from "@/lib/session";

export const generateMetadata = titled("login.title");

export default async function LoginPage({ searchParams }: PageProps<"/login">) {
  const [t, params, user] = await Promise.all([getT(), searchParams, getUser()]);
  if (user) redirect("/dashboard");

  return (
    <div className="max-w-md">
      <h1>{t("login.title")}</h1>
      {params.timeout && <p className="notice">{t("login.timeout")}</p>}
      {params.password && <p className="notice">{t("login.passwordSet")}</p>}
      <Form
        action={login}
        submitLabel={t("login.submit")}
        pendingLabel={t("form.pending")}
        errorTitle={t("form.errorSummary")}
      >
        <Field name="email" label={t("field.email")} type="email" autoComplete="email" inputMode="email" />
        <Field name="password" label={t("field.password")} type="password" autoComplete="current-password" />
      </Form>
      <ul className="mt-6 flex flex-col gap-2">
        <li>
          <Link href="/reset-password">{t("login.forgot")}</Link>
        </li>
        <li>
          <Link href="/register">{t("login.noAccount")}</Link>
        </li>
      </ul>
    </div>
  );
}
