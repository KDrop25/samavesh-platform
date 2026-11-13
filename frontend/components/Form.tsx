"use client";

import { createContext, useActionState, useContext, useEffect, useRef, type ReactNode } from "react";
import type { FormState } from "@/lib/form";

const FormContext = createContext<FormState>({});

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
                  <a href={`#${name}`}>{message}</a>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
      <FormContext.Provider value={state}>{children}</FormContext.Provider>
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
  const state = useContext(FormContext);
  const error = state.errors?.[name];
  const describedBy = [hint && `${name}-hint`, error && `${name}-error`].filter(Boolean).join(" ") || undefined;
  const shared = {
    id: name,
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
      <label htmlFor={name} className="mb-1 block font-semibold">
        {label} {optional && <span className="font-normal text-muted">{optional}</span>}
      </label>
      {hint && (
        <p id={`${name}-hint`} className="mb-1 text-muted">
          {hint}
        </p>
      )}
      {error && (
        <p id={`${name}-error`} className="mb-1 font-semibold text-danger">
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
  const state = useContext(FormContext);
  const selected = state.values?.[name] ?? defaultValue;
  return (
    <fieldset key={selected}>
      <legend className="mb-1 font-semibold">{legend}</legend>
      {options.map((option) => (
        <div key={option.value} className="flex min-h-11 items-center gap-2">
          <input
            type="radio"
            id={`${name}-${option.value}`}
            name={name}
            value={option.value}
            defaultChecked={option.value === selected}
            className="size-5"
          />
          <label htmlFor={`${name}-${option.value}`} lang={option.lang}>
            {option.label}
          </label>
        </div>
      ))}
    </fieldset>
  );
}
