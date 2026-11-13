import { notFound } from "next/navigation";
import { api } from "@/lib/api";
import { getT, titled } from "@/lib/i18n";

export const generateMetadata = titled("outbox.title");

type DevEmail = { to: string; subject: string; body: string; at: string };

/** Dev only: the API does not mount /dev/emails in production, and neither does this page. */
export default async function OutboxPage() {
  if (process.env.NODE_ENV === "production") notFound();
  const t = await getT();
  const result = await api<DevEmail[]>("/dev/emails", { token: null });
  const emails = result.ok ? result.data : [];

  return (
    <>
      <h1>{t("outbox.title")}</h1>
      <p className="mb-6">{t("outbox.intro")}</p>
      {emails.length === 0 ? (
        <p>{t("outbox.empty")}</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="table">
            <caption>{t("outbox.caption")}</caption>
            <thead>
              <tr>
                <th scope="col">{t("outbox.to")}</th>
                <th scope="col">{t("outbox.subject")}</th>
                <th scope="col">{t("outbox.body")}</th>
              </tr>
            </thead>
            <tbody>
              {emails.map((email, index) => (
                <tr key={index}>
                  <td>{email.to}</td>
                  <td>{email.subject}</td>
                  <td>{email.body}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
