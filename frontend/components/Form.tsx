"use client";

import { createContext, useActionState, useContext, useEffect, useId, useRef, type ReactNode } from "react";
import type { FormState } from "@/lib/form";

/**
 * `id` is unique per form and prefixes every control id inside it. A page can hold several
 * forms with a field of the same name (two "relationship" fields, say); without the prefix
 * their ids would collide and a label would point at the wrong input.
 */
const FormContext = createContext<{ state: FormState; id: string }>({ state: {}, id: "" });

type Action = (state: FormState, form: FormData) => Promise<FormState>;

/**
 * Accessible form wrapper around a Server Action.
 * - Result is shown in a summary that receives focus: role="alert" for errors, role="status" for success.
 * - The summary links to each invalid field; each field repeats its own message.
 * - Validation is done on the server (noValidate) so every browser and screen reader gets the same messages.
 */
export function Form({
  action,
  submitLabel,
  pendingLabel,
  errorTitle,
  secondary = false,
  children,
}: {
  action: Action;
  submitLabel: string;
  pendingLabel: string;
  errorTitle: string;
  secondary?: boolean;
  children?: ReactNode;
}) {
  const [state, formAction, pending] = useActionState(action, {});
  const id = useId();
  const summary = useRef<HTMLDivElement>(null);
  const errors = Object.entries(state.errors ?? {});
  const hasResult = Boolean(state.message) || errors.length > 0;

  useEffect(() => {
    if (hasResult) summary.current?.focus();
  }, [state, hasResult]);

  return (
    <form
      action={formAction}
      noValidate
      onSubmit={(event) => {
        if (pending) event.preventDefault(); // no double submits, without disabling (and unfocusing) the button
      }}
      className="flex flex-col gap-5"
    >
      {hasResult && (
        <div
          ref={summary}
          tabIndex={-1}
          role={state.ok ? "status" : "alert"}
          className={state.ok ? "notice mb-0" : "notice notice-error mb-0"}
        >
          {errors.length > 0 && <p className="font-bold">{errorTitle}</p>}
          {state.message && <p>{state.message}</p>}
          {errors.length > 0 && (
            <ul className="list-disc ps-5">
              {errors.map(([name, message]) => (
                <li key={name}>
                  <a href={`#${id}${name}`}>{message}</a>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
      <FormContext.Provider value={{ state, id }}>{children}</FormContext.Provider>
      <div>
        <button type="submit" className={secondary ? "btn btn-secondary" : "btn"} aria-disabled={pending}>
          {pending ? pendingLabel : submitLabel}
        </button>
      </div>
    </form>
  );
}

type FieldProps = {
  name: string;
  label: string;
  type?: string;
  hint?: string;
  /** Translated "(optional)" suffix. Fields without it are required. */
  optional?: string;
  autoComplete?: string;
  inputMode?: "numeric" | "email" | "text";
  defaultValue?: string;
  maxLength?: number;
  options?: { value: string; label: string }[];
};

/** Labelled control with hint and error wired up through aria-describedby. */
export function Field({ name, label, type = "text", hint, optional, options, defaultValue, ...rest }: FieldProps) {
  const { state, id: formId } = useContext(FormContext);
  const id = `${formId}${name}`;
  const error = state.errors?.[name];
  const describedBy = [hint && `${id}-hint`, error && `${id}-error`].filter(Boolean).join(" ") || undefined;
  const shared = {
    id,
    name,
    className: "input",
    required: !optional,
    "aria-invalid": error ? true : undefined,
    "aria-describedby": describedBy,
    defaultValue: state.values?.[name] ?? defaultValue,
  };
  // Re-mount after each submit so the echoed value is applied (React resets uncontrolled fields).
  const key = `${name}:${state.values?.[name] ?? ""}`;

  return (
    <div>
      <label htmlFor={id} className="mb-1 block font-semibold">
        {label} {optional && <span className="font-normal text-muted">{optional}</span>}
      </label>
      {hint && (
        <p id={`${id}-hint`} className="mb-1 text-muted">
          {hint}
        </p>
      )}
      {error && (
        <p id={`${id}-error`} className="mb-1 font-semibold text-danger">
          {error}
        </p>
      )}
      {options ? (
        <select key={key} {...shared}>
          {options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      ) : type === "textarea" ? (
        <textarea key={key} {...shared} rows={5} maxLength={rest.maxLength} />
      ) : (
        <input key={key} {...shared} type={type} {...rest} />
      )}
    </div>
  );
}

/** Radio group with a real fieldset/legend, for choices where seeing every option matters. */
export function RadioGroup({
  name,
  legend,
  options,
  defaultValue,
}: {
  name: string;
  legend: string;
  options: { value: string; label: string; lang?: string }[];
  defaultValue: string;
}) {
  const { state, id: formId } = useContext(FormContext);
  const selected = state.values?.[name] ?? defaultValue;
  return (
    <fieldset key={selected}>
      <legend className="mb-1 font-semibold">{legend}</legend>
      {options.map((option) => (
        <div key={option.value} className="flex min-h-11 items-center gap-2">
          <input
            type="radio"
            id={`${formId}${name}-${option.value}`}
            name={name}
            value={option.value}
            defaultChecked={option.value === selected}
            className="size-5"
          />
          <label htmlFor={`${formId}${name}-${option.value}`} lang={option.lang}>
            {option.label}
          </label>
        </div>
      ))}
    </fieldset>
  );
}

/** Multi-select as a group of checkboxes in a fieldset: every option is visible and keyboard-reachable. */
export function CheckboxGroup({
  name,
  legend,
  hint,
  options,
  defaultValues,
}: {
  name: string;
  legend: string;
  hint?: string;
  options: { value: string; label: string }[];
  defaultValues: string[];
}) {
  const id = `${useContext(FormContext).id}${name}`;
  return (
    <fieldset aria-describedby={hint ? `${id}-hint` : undefined}>
      <legend className="mb-1 font-semibold">{legend}</legend>
      {hint && (
        <p id={`${id}-hint`} className="mb-1 text-muted">
          {hint}
        </p>
      )}
      <div className="grid gap-x-6 sm:grid-cols-2">
        {options.map((option) => (
          <div key={option.value} className="flex min-h-11 items-center gap-2">
            <input
              type="checkbox"
              id={`${id}-${option.value}`}
              name={name}
              value={option.value}
              defaultChecked={defaultValues.includes(option.value)}
              className="size-5 shrink-0"
            />
            <label htmlFor={`${id}-${option.value}`}>{option.label}</label>
          </div>
        ))}
      </div>
    </fieldset>
  );
}

/** A single labelled checkbox. Keeps its state when a failed form is shown again. */
export function Checkbox({ name, label, defaultChecked }: { name: string; label: string; defaultChecked: boolean }) {
  const { state, id: formId } = useContext(FormContext);
  const id = `${formId}${name}`;
  const checked = state.values ? name in state.values : defaultChecked;
  return (
    <div className="flex min-h-11 items-center gap-2">
      <input key={String(checked)} type="checkbox" id={id} name={name} defaultChecked={checked} className="size-5 shrink-0" />
      <label htmlFor={id}>{label}</label>
    </div>
  );
}
