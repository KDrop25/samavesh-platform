import { cookies } from "next/headers";
import { savePreferences } from "@/app/actions";
import { Form, RadioGroup } from "@/components/Form";
import { getLocale, getT, titled } from "@/lib/i18n";

export const generateMetadata = titled("settings.title");

export default async function SettingsPage() {
  const [t, locale, store] = await Promise.all([getT(), getLocale(), cookies()]);

  return (
    <div className="max-w-md">
      <h1>{t("settings.title")}</h1>
      <p className="mb-6">{t("settings.intro")}</p>
      <Form
        action={savePreferences}
        submitLabel={t("settings.save")}
        pendingLabel={t("form.pending")}
        errorTitle={t("form.errorSummary")}
      >
        <RadioGroup
          name="theme"
          legend={t("settings.theme")}
          defaultValue={store.get("theme")?.value ?? "auto"}
          options={["auto", "light", "dark", "contrast"].map((value) => ({ value, label: t(`theme.${value}`) }))}
        />
        <RadioGroup
          name="text_size"
          legend={t("settings.textSize")}
          defaultValue={store.get("text_size")?.value ?? "normal"}
          options={["normal", "large", "larger"].map((value) => ({ value, label: t(`size.${value}`) }))}
        />
        <RadioGroup
          name="locale"
          legend={t("settings.language")}
          defaultValue={locale}
          options={[
            { value: "en", label: "English", lang: "en" },
            { value: "hi", label: "हिन्दी", lang: "hi" },
          ]}
        />
      </Form>
    </div>
  );
}
