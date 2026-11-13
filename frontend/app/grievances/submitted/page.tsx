import Link from "next/link";
import { redirect } from "next/navigation";
import { getT, titled } from "@/lib/i18n";

export const generateMetadata = titled("grievance.submitted.title");

export default async function SubmittedPage({ searchParams }: PageProps<"/grievances/submitted">) {
  const [t, query] = await Promise.all([getT(), searchParams]);
  const ref = typeof query.ref === "string" && /^GRV-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}$/.test(query.ref) ? query.ref : null;
  if (!ref) redirect("/grievances/new");
  return (
    <div className="max-w-xl">
      <h1>{t("grievance.submitted.title")}</h1>
      <p>{t("grievance.submitted.text")}</p>
      <p className="card my-6">
        <span className="block text-muted">{t("grievance.reference")}</span>
        <strong className="text-2xl tracking-wide">{ref}</strong>
      </p>
      <p className="mb-6">{t("grievance.submitted.keep")}</p>
      <Link href={`/track?reference=${ref}`} className="btn">{t("track.title")}</Link>
    </div>
  );
}
