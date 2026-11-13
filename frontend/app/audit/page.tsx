import Link from "next/link";
import { api } from "@/lib/api";
import { formatDateTime, getLocale, getT, titled, type T } from "@/lib/i18n";
import { requireUser } from "@/lib/session";

export const generateMetadata = titled("audit.title");

type Entry = {
  id: number;
  at: string;
  actor: string | null;
  actor_role: string;
  action: string;
  entity_type: string;
  entity_id: number;
  changed_fields: Record<string, string | [unknown, unknown]> | null;
};
type AuditPage = { entity_types: string[]; next_before: number | null; entries: Entry[] };

/** Translated name where we have one; otherwise the raw identifier (new tables still show up). */
const named = (t: T, key: string, fallback: string) => (t(key) === key ? fallback : t(key));

function changes(t: T, entry: Entry): string[] {
  const shown = (value: unknown) => (value === null || value === "" ? t("audit.empty") : String(value));
  return Object.entries(entry.changed_fields ?? {}).map(([field, change]) =>
    Array.isArray(change)
      ? `${field}: ${t("audit.fromTo", { from: shown(change[0]), to: shown(change[1]) })}`
      : `${field}: ${t("audit.encrypted")}`,
  );
}

/** Read-only by design: there is no control on this page, or endpoint behind it, that changes the log. */
export default async function AuditPage({ searchParams }: PageProps<"/audit">) {
  const [t, locale, query] = await Promise.all([getT(), getLocale(), searchParams]);
  await requireUser("nodal_officer", "administrator");
  const type = typeof query.type === "string" && /^\w+$/.test(query.type) ? query.type : "";
  const before = typeof query.before === "string" && /^\d+$/.test(query.before) ? query.before : "";
  const params = new URLSearchParams();
  if (type) params.set("entity_type", type);
  if (before) params.set("before", before);
  const result = await api<AuditPage>(`/audit?${params}`);
  const { entity_types, next_before, entries } = result.ok
    ? result.data
    : { entity_types: [], next_before: null, entries: [] };

  return (
    <>
      <h1>{t("audit.title")}</h1>
      <p className="mb-6 max-w-3xl">{t("audit.intro")}</p>
      {!result.ok && (
        <p className="notice notice-error" role="alert">
          {t("error.api_unreachable")}
        </p>
      )}

      <form method="get" className="mb-6 flex flex-wrap items-end gap-3">
        <div>
          <label htmlFor="type" className="mb-1 block font-semibold">
            {t("audit.filter")}
          </label>
          <select id="type" name="type" defaultValue={type} className="input">
            <option value="">{t("audit.all")}</option>
            {entity_types.map((value) => (
              <option key={value} value={value}>
                {named(t, `entity.${value}`, value)}
              </option>
            ))}
          </select>
        </div>
        <button type="submit" className="btn btn-secondary">
          {t("audit.show")}
        </button>
      </form>

      {result.ok && entries.length === 0 ? (
        <p>{t("audit.none")}</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="table">
            <caption>{t("audit.caption")}</caption>
            <thead>
              <tr>
                <th scope="col">{t("audit.when")}</th>
                <th scope="col">{t("audit.who")}</th>
                <th scope="col">{t("audit.action")}</th>
                <th scope="col">{t("audit.record")}</th>
                <th scope="col">{t("audit.changes")}</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((entry) => (
                <tr key={entry.id}>
                  <td>{formatDateTime(entry.at, locale)}</td>
                  <td>
                    {entry.actor ? `${entry.actor} (${named(t, `role.${entry.actor_role}`, entry.actor_role)})` : named(t, `role.${entry.actor_role}`, entry.actor_role)}
                  </td>
                  <td>{named(t, `audit.action.${entry.action}`, entry.action)}</td>
                  <td>
                    {named(t, `entity.${entry.entity_type}`, entry.entity_type)} #{entry.entity_id}
                  </td>
                  <td>
                    {changes(t, entry).length === 0 ? (
                      "–"
                    ) : (
                      <ul>
                        {changes(t, entry).map((line) => (
                          <li key={line}>{line}</li>
                        ))}
                      </ul>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {next_before && (
        <p className="mt-6">
          <Link href={`/audit?${new URLSearchParams({ ...(type && { type }), before: String(next_before) })}`}>
            {t("audit.older")}
          </Link>
        </p>
      )}
    </>
  );
}
