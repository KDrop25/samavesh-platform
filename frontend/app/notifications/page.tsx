import Link from "next/link";
import { markAllNotificationsRead, markNotificationRead } from "@/app/actions";
import { api } from "@/lib/api";
import { formatDateTime, getLocale, getT, titled, type T } from "@/lib/i18n";
import { requireUser } from "@/lib/session";

export const generateMetadata = titled("notifications.title");

type Notice = { id: number; kind: string; link: string; params: Record<string, string | number>; read: boolean; at: string };

/** Sentences are built here from codes and identifiers, so the stored notice holds no prose. */
function text(t: T, n: Notice): string {
  const p = n.params;
  switch (n.kind) {
    case "plan_approved": return t("notice.plan_approved");
    case "plan_rejected": return t("notice.plan_rejected");
    case "plan_review": return t("notice.plan_review");
    case "compliance_due": return t("notice.compliance_due", { days: p.days });
    case "grievance_status": return t("notice.grievance_status", { reference: p.reference, status: t(`gstatus.${p.status}`) });
    case "escalation": return t("notice.escalation", { reference: p.reference });
    default: return t("notice.generic");
  }
}

export default async function NotificationsPage() {
  const [t, locale] = await Promise.all([getT(), getLocale()]);
  await requireUser();
  const result = await api<{ unread: number; items: Notice[] }>("/notifications");
  const { unread = 0, items = [] } = result.ok ? result.data : {};

  return (
    <>
      <h1>{t("notifications.title")}</h1>
      {items.length === 0 ? (
        <p>{t("notifications.none")}</p>
      ) : (
        <>
          <p className="mb-4">{t("notifications.unread", { n: unread })}</p>
          {unread > 0 && (
            <form action={markAllNotificationsRead} className="mb-6">
              <button type="submit" className="btn btn-secondary">{t("notifications.markAll")}</button>
            </form>
          )}
          <ul className="flex flex-col gap-3">
            {items.map((n) => (
              <li key={n.id} className="card flex flex-wrap items-center justify-between gap-3">
                <div>
                  <Link href={n.link} className={n.read ? "" : "font-bold"}>{text(t, n)}</Link>
                  <p className="text-muted">{formatDateTime(n.at, locale)}</p>
                </div>
                {n.read ? (
                  <span className="text-muted">{t("notifications.read")}</span>
                ) : (
                  <form action={markNotificationRead.bind(null, n.id)}>
                    <button type="submit" className="btn btn-secondary">{t("notifications.markRead")}</button>
                  </form>
                )}
              </li>
            ))}
          </ul>
        </>
      )}
    </>
  );
}
