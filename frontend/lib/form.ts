import type { ApiFailure } from "@/lib/api";
import type { T } from "@/lib/i18n";

export type FormState = {
  ok?: boolean;
  message?: string;
  /** field name -> message; rendered next to the field and linked from the error summary */
  errors?: Record<string, string>;
  /** submitted values echoed back so a failed form is not wiped (never passwords) */
  values?: Record<string, string>;
};

/** Read named fields from a form; empty strings become undefined so the API reports "missing". */
export function pick(form: FormData, names: string[]): Record<string, string | undefined> {
  return Object.fromEntries(
    names.map((name) => {
      const value = form.get(name);
      return [name, typeof value === "string" && value.trim() !== "" ? value.trim() : undefined];
    }),
  );
}

function issueMessage(t: T, field: string, type: string, ctx?: Record<string, unknown>): string {
  if (type === "missing") return t("error.required");
  if (type === "string_too_short") return t("error.min_length", { n: Number(ctx?.min_length) });
  if (type === "string_too_long") return t("error.max_length", { n: Number(ctx?.max_length) });
  if (type.startsWith("date")) return t("error.date");
  if (type.startsWith("int")) return t("error.number");
  if (type.endsWith("than_equal")) return t("error.range");
  if (field === "email") return t("error.email");
  if (field === "code") return t("error.code");
  return t("error.invalid");
}

/** Submitted values to echo back into a failed form. Never passwords, never React's own fields. */
export function formValues(form: FormData): Record<string, string> {
  return Object.fromEntries(
    [...form.entries()].filter(
      (entry): entry is [string, string] =>
        typeof entry[1] === "string" && !entry[0].startsWith("$") && !entry[0].includes("password"),
    ),
  );
}

/** Turn an API failure into translated, field-level messages that say what is wrong and how to fix it. */
export function failure(t: T, result: ApiFailure, form?: FormData): FormState {
  const values = form ? formValues(form) : undefined;

  const errors: Record<string, string> = {};
  for (const issue of result.detail ?? []) {
    // A model-level rule (e.g. students must give a date of birth) reports loc ["body"].
    const modelRule = /Value error, (\w+)_required/.exec(issue.msg)?.[1];
    const field = modelRule ?? String(issue.loc.at(-1));
    const ruleMessage = t(`error.rule.${modelRule}`); // specific wording where one exists
    const message = modelRule
      ? ruleMessage === `error.rule.${modelRule}`
        ? t("error.required")
        : ruleMessage
      : issueMessage(t, field, issue.type, issue.ctx);
    errors[field] = `${t(`field.${field}`)}: ${message}`;
  }
  if (Object.keys(errors).length) return { errors, values };

  const key = `error.${result.code}`;
  const message = t(key);
  return { message: message === key ? t("error.unexpected") : message, values };
}
