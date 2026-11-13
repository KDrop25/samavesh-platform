import { inviteUser, setUserActive } from "@/app/actions";
import { Field, Form } from "@/components/Form";
import { api } from "@/lib/api";
import { getT, titled } from "@/lib/i18n";
import { requireUser, type Role } from "@/lib/session";

export const generateMetadata = titled("users.title");

type AdminUser = {
  id: number;
  email: string;
  full_name: string;
  role: Role;
  is_active: boolean;
  email_verified_at: string | null;
};

const STAFF_ROLES: Role[] = ["support_staff", "nodal_officer", "grievance_officer", "administrator"];

export default async function UsersPage() {
  const [t, me] = await Promise.all([getT(), requireUser("administrator")]);
  const result = await api<AdminUser[]>("/admin/users");
  const users = result.ok ? result.data : [];
  const formLabels = { pendingLabel: t("form.pending"), errorTitle: t("form.errorSummary") };

  return (
    <>
      <h1>{t("users.title")}</h1>
      {!result.ok && (
        <p className="notice notice-error" role="alert">
          {t("error.api_unreachable")}
        </p>
      )}
      <div className="overflow-x-auto">
        <table className="table">
          <caption>{t("users.caption")}</caption>
          <thead>
            <tr>
              <th scope="col">{t("users.name")}</th>
              <th scope="col">{t("users.email")}</th>
              <th scope="col">{t("users.role")}</th>
              <th scope="col">{t("users.status")}</th>
              <th scope="col">{t("users.actions")}</th>
            </tr>
          </thead>
          <tbody>
            {users.map((user) => (
              <tr key={user.id}>
                <th scope="row">{user.full_name}</th>
                <td>{user.email}</td>
                <td>{t(`role.${user.role}`)}</td>
                <td>
                  {!user.is_active
                    ? t("users.inactive")
                    : user.email_verified_at
                      ? t("users.active")
                      : t("users.pending")}
                </td>
                <td>
                  {user.id === me.id ? (
                    t("users.you")
                  ) : (
                    <Form
                      action={setUserActive.bind(null, user.id, user.full_name, !user.is_active)}
                      submitLabel={t(user.is_active ? "users.deactivate" : "users.activate", {
                        name: user.full_name,
                      })}
                      secondary
                      {...formLabels}
                    />
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <section aria-labelledby="invite-title" className="mt-12 max-w-md">
        <h2 id="invite-title">{t("users.invite.title")}</h2>
        <p className="mb-4">{t("users.invite.intro")}</p>
        <Form action={inviteUser} submitLabel={t("users.invite.submit")} {...formLabels}>
          <Field name="full_name" label={t("field.full_name")} autoComplete="off" maxLength={120} />
          <Field name="email" label={t("field.email")} type="email" autoComplete="off" inputMode="email" />
          <Field
            name="role"
            label={t("users.invite.role")}
            options={STAFF_ROLES.map((role) => ({ value: role, label: t(`role.${role}`) }))}
          />
        </Form>
      </section>
    </>
  );
}
