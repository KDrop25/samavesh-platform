import { cookies } from "next/headers";
import en from "@/messages/en.json";
import hi from "@/messages/hi.json";

export type Locale = "en" | "hi";
export type T = (key: string, vars?: Record<string, string | number>) => string;

const dictionaries: Record<Locale, Record<string, string>> = { en, hi };

export async function getLocale(): Promise<Locale> {
  return (await cookies()).get("locale")?.value === "hi" ? "hi" : "en";
}

/** `export const generateMetadata = titled("login.title")` gives each page a unique, translated title. */
export const titled = (key: string) => async () => ({ title: (await getT())(key) });

/** Translator for the current request. Falls back to English, then to the key itself. */
export async function getT(): Promise<T> {
  const dict = dictionaries[await getLocale()];
  return (key, vars) => {
    const text = dict[key] ?? dictionaries.en[key] ?? key;
    return vars ? text.replace(/\{(\w+)\}/g, (_, name) => String(vars[name] ?? "")) : text;
  };
}
