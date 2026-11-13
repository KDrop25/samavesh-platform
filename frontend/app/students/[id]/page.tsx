import Link from "next/link";
import { notFound } from "next/navigation";
import {
  assignStaff,
  endAssignment,
  inviteGuardian,
  recordConsent,
  removeGuardian,
  saveProfile,
} from "@/app/actions";
import { CheckboxGroup, Field, Form } from "@/components/Form";
import { PageNotice, UploadNotice } from "@/components/PageNotice";
import { UploadForm } from "@/components/UploadForm";
import { api } from "@/lib/api";
import { formatDate, getLocale, getT, titled } from "@/lib/i18n";
import { requireUser } from "@/lib/session";

export const generateMetadata = titled("profile.title");

const RPWD_CATEGORIES = [
  "blindness",
  "low_vision",
  "leprosy_cured",
  "hearing_impairment",
  "locomotor_disability",
  "dwarfism",
  "intellectual_disability",
  "mental_illness",
  "autism_spectrum_disorder",
  "cerebral_palsy",
  "muscular_dystrophy",
  "chronic_neurological_conditions",
  "specific_learning_disabilities",
  "multiple_sclerosis",
  "speech_and_language_disability",
  "thalassemia",
  "hemophilia",
  "sickle_cell_disease",
  "multiple_disabilities",
  "acid_attack_victim",
  "parkinsons_disease",
];

type Profile = {
  enrollment_no: string | null;
  programme: string | null;
  department: string | null;
  year_of_study: number | null;
  disability_categories: string[];
  udid_number: string | null;
  benchmark_percentage: number | null;
  support_needs: string | null;
  communication_preference: string | null;
  certificate: { id: number; filename: string } | null;
};

type Detail = {
  student: { id: number; full_name: string; email: string; date_of_birth: string | null; is_minor: boolean };
  guardians: { id: number; guardian_email: string; relationship: string; status: "invited" | "active" }[];
  consent: { consenting_person_name: string; relationship: string; consent_date: string; method: string } | null;
  staff: { assignment_id: number; staff_id: number; full_name: string }[];
  profile: Profile | null;
  can: {
    edit_profile: boolean;
    manage_guardians: boolean;
    assign_staff: boolean;
    give_consent: boolean;
    record_consent: boolean;
  };
};

export default async function StudentPage({ params, searchParams }: PageProps<"/students/[id]">) {
  const [t, locale, { id }, query] = await Promise.all([getT(), getLocale(), params, searchParams]);
  await requireUser("student", "guardian", "support_staff", "nodal_officer", "administrator");
  const result = await api<Detail>(`/students/${id}`);
  if (!result.ok) notFound(); // also covers "exists but is not yours": the API answers 404 for both
  const { student, guardians, consent, staff, profile, can } = result.data;

  const blocked = student.is_minor && !consent && !profile;
  const [staffList, upload] = await Promise.all([
    can.assign_staff ? api<{ id: number; full_name: string }[]>("/staff") : null,
    can.edit_profile && profile
      ? api<{ token: string }>("/files/tokens/upload", {
          method: "POST",
          body: { purpose: "certificate", ref_id: student.id, return_to: `/students/${student.id}` },
        })
      : null,
  ]);
  const assignable = (staffList?.ok ? staffList.data : []).filter(
    (member) => !staff.some((assigned) => assigned.staff_id === member.id),
  );
  const formLabels = { pendingLabel: t("form.pending"), errorTitle: t("form.errorSummary") };
  const optional = t("form.optional");
  const shown = (value: string | number | null) => (value === null || value === "" ? t("profile.notProvided") : value);

  return (
    <>
      <h1>{student.full_name}</h1>
      <p className="mb-6">
        <Link href={`/students/${student.id}/plans`}>{t("plans.link")}</Link>
      </p>
      <PageNotice query={query} />
      <UploadNotice query={query} success="certificate.uploaded" />

      <section aria-labelledby="details-title" className="mb-10">
        <h2 id="details-title">{t("student.details")}</h2>
        <dl className="grid gap-x-6 gap-y-1 sm:grid-cols-[14rem_1fr]">
          <dt className="font-semibold">{t("field.email")}</dt>
          <dd>{student.email}</dd>
          <dt className="font-semibold">{t("student.dob")}</dt>
          <dd>{student.date_of_birth ? formatDate(student.date_of_birth, locale) : t("profile.notProvided")}</dd>
          <dt className="font-semibold">{t("students.age")}</dt>
          <dd>{t(student.is_minor ? "students.under18" : "students.adult")}</dd>
        </dl>
      </section>

      <section aria-labelledby="guardians-title" className="mb-10">
        <h2 id="guardians-title">{t("guardians.title")}</h2>
        {guardians.length === 0 ? (
          <p>{t("guardians.none")}</p>
        ) : (
          <ul className="flex flex-col gap-3">
            {guardians.map((guardian) => (
              <li key={guardian.id} className="card flex flex-wrap items-center justify-between gap-3">
                <span>
                  {guardian.guardian_email} ({guardian.relationship}) – {t(`guardians.status.${guardian.status}`)}
                </span>
                {can.manage_guardians && (
                  <Form
                    action={removeGuardian.bind(null, student.id, guardian.id)}
                    submitLabel={t("guardians.remove", { email: guardian.guardian_email })}
                    secondary
                    {...formLabels}
                  />
                )}
              </li>
            ))}
          </ul>
        )}
        {can.manage_guardians && (
          <div className="mt-6 max-w-md">
            <h3 className="mb-1">{t("guardians.invite.title")}</h3>
            <p className="mb-4">{t("guardians.invite.intro")}</p>
            <Form
              action={inviteGuardian.bind(null, student.id)}
              submitLabel={t("guardians.invite.submit")}
              {...formLabels}
            >
              <Field name="guardian_email" label={t("field.guardian_email")} type="email" inputMode="email" autoComplete="off" />
              <Field name="relationship" label={t("field.relationship")} hint={t("hint.relationship")} maxLength={60} />
            </Form>
          </div>
        )}
      </section>

      {student.is_minor && (
        <section aria-labelledby="consent-title" className="mb-10">
          <h2 id="consent-title">{t("consent.title")}</h2>
          {consent ? (
            <p>
              {t("consent.given", {
                name: consent.consenting_person_name,
                relationship: consent.relationship,
                date: formatDate(consent.consent_date, locale),
              })}{" "}
              {t(`consent.method.${consent.method}`)}
            </p>
          ) : (
            <p>{t("consent.needed")}</p>
          )}
          {can.give_consent && (
            <div className="mt-4 max-w-xl">
              <p className="mb-4">{t("consent.give.text")}</p>
              <Form action={recordConsent.bind(null, student.id)} submitLabel={t("consent.give.submit")} {...formLabels} />
            </div>
          )}
          {can.record_consent && (
            <div className="mt-6 max-w-md">
              <h3 className="mb-3">{t("consent.record.title")}</h3>
              <Form
                action={recordConsent.bind(null, student.id)}
                submitLabel={t("consent.record.submit")}
                {...formLabels}
              >
                <Field name="consenting_person_name" label={t("field.consenting_person_name")} maxLength={120} autoComplete="off" />
                <Field name="relationship" label={t("field.relationship")} hint={t("hint.relationship")} maxLength={60} />
                <Field name="consent_date" label={t("field.consent_date")} type="date" />
              </Form>
            </div>
          )}
        </section>
      )}

      <section aria-labelledby="staff-title" className="mb-10">
        <h2 id="staff-title">{t("staff.title")}</h2>
        {staff.length === 0 ? (
          <p>{t("staff.none")}</p>
        ) : (
          <ul className="flex flex-col gap-3">
            {staff.map((member) => (
              <li key={member.assignment_id} className="card flex flex-wrap items-center justify-between gap-3">
                <span>{member.full_name}</span>
                {can.assign_staff && (
                  <Form
                    action={endAssignment.bind(null, student.id, member.assignment_id)}
                    submitLabel={t("staff.end", { name: member.full_name })}
                    secondary
                    {...formLabels}
                  />
                )}
              </li>
            ))}
          </ul>
        )}
        {can.assign_staff && assignable.length > 0 && (
          <div className="mt-6 max-w-md">
            <h3 className="mb-3">{t("staff.assign.title")}</h3>
            <Form action={assignStaff.bind(null, student.id)} submitLabel={t("staff.assign.submit")} {...formLabels}>
              <Field
                name="staff_id"
                label={t("field.staff_id")}
                options={assignable.map((member) => ({ value: String(member.id), label: member.full_name }))}
              />
            </Form>
          </div>
        )}
      </section>

      <section aria-labelledby="profile-title" className="mb-10">
        <h2 id="profile-title">{t("profile.title")}</h2>
        {blocked ? (
          <p className="notice notice-error">{t("profile.blocked")}</p>
        ) : can.edit_profile ? (
          <div className="max-w-2xl">
            <p className="mb-5">{t("profile.intro")}</p>
            <Form action={saveProfile.bind(null, student.id)} submitLabel={t("profile.save")} {...formLabels}>
              <Field name="enrollment_no" label={t("field.enrollment_no")} optional={optional} defaultValue={profile?.enrollment_no ?? ""} maxLength={40} />
              <Field name="programme" label={t("field.programme")} optional={optional} defaultValue={profile?.programme ?? ""} maxLength={120} />
              <Field name="department" label={t("field.department")} optional={optional} defaultValue={profile?.department ?? ""} maxLength={120} />
              <Field name="year_of_study" label={t("field.year_of_study")} optional={optional} inputMode="numeric" defaultValue={String(profile?.year_of_study ?? "")} maxLength={1} />
              <CheckboxGroup
                name="disability_categories"
                legend={`${t("field.disability_categories")} ${optional}`}
                hint={t("hint.disability_categories")}
                options={RPWD_CATEGORIES.map((value) => ({ value, label: t(`rpwd.${value}`) }))}
                defaultValues={profile?.disability_categories ?? []}
              />
              <Field name="udid_number" label={t("field.udid_number")} optional={optional} defaultValue={profile?.udid_number ?? ""} maxLength={40} autoComplete="off" />
              <Field name="benchmark_percentage" label={t("field.benchmark_percentage")} optional={optional} inputMode="numeric" defaultValue={String(profile?.benchmark_percentage ?? "")} maxLength={3} />
              <Field name="support_needs" label={t("field.support_needs")} type="textarea" optional={optional} hint={t("hint.support_needs")} defaultValue={profile?.support_needs ?? ""} maxLength={4000} />
              <Field name="communication_preference" label={t("field.communication_preference")} optional={optional} defaultValue={profile?.communication_preference ?? ""} maxLength={500} />
            </Form>
          </div>
        ) : profile ? (
          <dl className="grid gap-x-6 gap-y-1 sm:grid-cols-[14rem_1fr]">
            <dt className="font-semibold">{t("field.enrollment_no")}</dt>
            <dd>{shown(profile.enrollment_no)}</dd>
            <dt className="font-semibold">{t("field.programme")}</dt>
            <dd>{shown(profile.programme)}</dd>
            <dt className="font-semibold">{t("field.department")}</dt>
            <dd>{shown(profile.department)}</dd>
            <dt className="font-semibold">{t("field.year_of_study")}</dt>
            <dd>{shown(profile.year_of_study)}</dd>
            <dt className="font-semibold">{t("field.disability_categories")}</dt>
            <dd>{shown(profile.disability_categories.map((value) => t(`rpwd.${value}`)).join(", "))}</dd>
            <dt className="font-semibold">{t("field.udid_number")}</dt>
            <dd>{shown(profile.udid_number)}</dd>
            <dt className="font-semibold">{t("field.benchmark_percentage")}</dt>
            <dd>{shown(profile.benchmark_percentage)}</dd>
            <dt className="font-semibold">{t("field.support_needs")}</dt>
            <dd className="whitespace-pre-wrap">{shown(profile.support_needs)}</dd>
            <dt className="font-semibold">{t("field.communication_preference")}</dt>
            <dd>{shown(profile.communication_preference)}</dd>
          </dl>
        ) : (
          <p>{t("profile.none")}</p>
        )}
      </section>

      {profile && (
        <section aria-labelledby="certificate-title">
          <h2 id="certificate-title">{t("certificate.title")}</h2>
          {profile.certificate ? (
            <p>
              <a href={`/files/${profile.certificate.id}`}>
                {t("certificate.download", { name: profile.certificate.filename })}
              </a>
            </p>
          ) : (
            <p>{t("certificate.none")}</p>
          )}
          {upload?.ok && (
            <UploadForm
              token={upload.data.token}
              label={t("certificate.upload.label")}
              hint={t("certificate.upload.hint")}
              submit={t("certificate.upload.submit")}
            />
          )}
        </section>
      )}
    </>
  );
}
