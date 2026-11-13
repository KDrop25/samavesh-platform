/** Mirrors ACCOMMODATION_TYPES in backend/app/models/plan.py. A plan has at most one item per type. */
export const ACCOMMODATION_TYPES = [
  "scribe",
  "extra_time",
  "accessible_material",
  "assistive_tech",
  "physical_access",
  "transport",
] as const;
