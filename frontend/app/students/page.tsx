import Link from "next/link";
import { redirect } from "next/navigation";
import { api } from "@/lib/api";
import { getT, titled } from "@/lib/i18n";
import { requireUser } from "@/lib/session";

export const generateMetadata = titled("students.title");

type StudentRow = { id: number; full_name: string; email: string; is_minor: boolean; has_profile: boolean };

export default async function StudentsPage() {
  const [t, user] = await Promise.all([
    getT(),
    requireUser("student", "guardian", "support_staff", "nodal_officer", "administrator"),
  ]);
  if (user.role === "student") redirect(`/students/${user.id}`);
  const result = await api<StudentRow[]>("/students");
  const students = result.ok ? result.data : [];

  return (
    <>
      <h1>{t("students.title")}</h1>
      {!result.ok && (
        <p className="notice notice-error" role="alert">
          {t("error.api_unreachable")}
        </p>
      )}
      {result.ok && students.length === 0 ? (
        <p>{t("students.empty")}</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="table">
            <caption>{t("students.caption")}</caption>
            <thead>
              <tr>
                <th scope="col">{t("students.name")}</th>
                <th scope="col">{t("students.email")}</th>
                <th scope="col">{t("students.age")}</th>
                <th scope="col">{t("students.profile")}</th>
              </tr>
            </thead>
            <tbody>
              {students.map((student) => (
                <tr key={student.id}>
                  <th scope="row">
                    <Link href={`/students/${student.id}`}>{student.full_name}</Link>
                  </th>
                  <td>{student.email}</td>
                  <td>{t(student.is_minor ? "students.under18" : "students.adult")}</td>
                  <td>{t(student.has_profile ? "students.hasProfile" : "students.noProfile")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
