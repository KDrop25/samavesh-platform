import { Notice } from "@/components/Notice";
import { getT } from "@/lib/i18n";

/** notice code (from the URL) -> message key. Anything not listed here is ignored. */
const NOTICES: Record<string, string> = {
  guardian_removed: "guardians.removed",
  assignment_ended: "staff.ended",
  consent_saved: "consent.saved",
  plan_saved: "plans.saved",
  plan_submitted: "plans.submitted",
};

/**
 * Confirmation for actions whose own form disappears when they succeed (submitting a draft
 * removes the Submit button; removing a guardian removes their row). A message inside that
 * form would vanish with it, so the action redirects with ?notice=code&n=nonce instead and the
 * page shows it here. The nonce makes every notice a new element, so it is focused and
 * announced each time, even twice in a row.
 */
export async function PageNotice({ query }: { query: Record<string, string | string[] | undefined> }) {
  const key = typeof query.notice === "string" ? NOTICES[query.notice] : undefined;
  if (!key) return null;
  const t = await getT();
  return <Notice key={String(query.n)}>{t(key)}</Notice>;
}
