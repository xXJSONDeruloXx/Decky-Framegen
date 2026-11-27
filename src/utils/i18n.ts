type SteamWindow = Window & {
  LocalizationManager?: {
    m_rgLocalesToUse?: string[];
  };
};

export const isTraditionalChinese = (): boolean => {
  const rawLocale =
    (typeof window !== "undefined"
      ? (window as SteamWindow).LocalizationManager?.m_rgLocalesToUse?.[0]
      : undefined) ||
    (typeof navigator !== "undefined" ? navigator.language : "") ||
    "";
  const locale = rawLocale.trim().toLowerCase().replace(/_/g, "-");
  return (
    locale === "tchinese" ||
    locale === "zh-tw" ||
    locale === "zh-hant" ||
    locale.startsWith("zh-hant-")
  );
};

export const L = (en: string, zhTW: string): string =>
  isTraditionalChinese() ? zhTW : en;
