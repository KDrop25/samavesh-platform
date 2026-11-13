/** Mirrors GRIEVANCE_CATEGORIES in backend/app/models/grievance.py. */
export const GRIEVANCE_CATEGORIES = [
  "accommodation_not_provided",
  "physical_accessibility",
  "accessible_material",
  "examination",
  "discrimination_or_conduct",
  "other",
];

/** Mirrors ACCOMMODATION_TYPES in backend/app/models/plan.py. A plan has at most one item per type. */
export const ACCOMMODATION_TYPES = [
  "scribe",
  "extra_time",
  "accessible_material",
  "assistive_tech",
  "physical_access",
  "transport",
] as const;
