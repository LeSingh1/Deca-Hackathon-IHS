export const money = (x: number, cents = false): string =>
  (x < 0 ? "-" : "") +
  "$" +
  Math.abs(x).toLocaleString("en-US", {
    minimumFractionDigits: cents ? 2 : 0,
    maximumFractionDigits: cents ? 2 : 0,
  });

export const pct = (x: number, dp = 2): string => `${(x * 100).toFixed(dp)}%`;

export const CATEGORY_LABEL: Record<string, string> = {
  interchange: "Interchange",
  assessment: "Network dues",
  processor_markup: "Processor markup",
  junk_fee: "Junk fee",
  equipment_lease: "Equipment lease",
};
