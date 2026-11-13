# Data model

Core entities. Columns marked 🔒 are encrypted at rest (AES-256-GCM). Every table also has `id` and `created_at`. Tables marked ✍ are append-only: the database refuses UPDATE and DELETE.

```mermaid
erDiagram
    users ||--o{ guardian_links : "student / guardian"
    users ||--o{ staff_assignments : "student / staff"
    users ||--o| student_profiles : "student"
    consents ||--o| student_profiles : "consent for under-18"
    student_profiles ||--o{ accommodation_plans : "has"
    accommodation_plans ||--o{ plan_items : "contains"
    accommodation_plans ||--o{ plan_decisions : "decided by ✍"
    accommodation_plans o|--o{ accommodation_plans : "supersedes"
    plan_items ||--o{ provision_logs : "delivered"
    compliance_items ||--o{ compliance_evidence : "evidence"
    files ||--o| student_profiles : "certificate"
    files ||--o| compliance_evidence : "evidence"
    grievances ||--o{ grievance_events : "timeline"
    users ||--o{ notifications : "receives"
    users ||--o{ audit_log : "acted (✍)"
    terms ||--o{ provision_logs : "summarised by term"
    holidays }o--|| settings : "working-day rule"

    users {
        int id PK
        string email UK
        string role "student | guardian | support_staff | nodal_officer | grievance_officer | administrator"
        date date_of_birth
        bool is_active
        int token_version
    }
    student_profiles {
        int id PK
        int student_id FK
        int consent_id FK
        enc disability_categories "🔒 RPwD categories"
        enc udid_number "🔒"
        enc support_needs "🔒"
    }
    accommodation_plans {
        int id PK
        int profile_id FK
        int version
        int supersedes_plan_id FK
        string status "draft | submitted | approved | rejected | superseded | ended"
        date start_date
        date review_date
    }
    plan_items {
        int id PK
        int plan_id FK
        string type "scribe | extra_time | accessible_material | assistive_tech | physical_access | transport"
        int interval_days "null = standing arrangement"
    }
    provision_logs {
        int id PK
        int plan_item_id FK
        date provided_on
        int staff_id FK
    }
    compliance_items {
        int id PK
        string status "compliant | partially | not_compliant | not_applicable"
        date due_date
        enc reason "🔒 required unless compliant"
    }
    grievances {
        int id PK
        string reference UK "GRV-XXXX-XXXX-XXXX"
        bool is_anonymous
        string status "received | under_review | resolved | escalated"
        enc complainant_name "🔒 null when anonymous"
        enc complainant_user_id "🔒 null when anonymous"
        datetime escalation_flagged_at
    }
    grievance_events {
        int id PK
        int grievance_id FK
        string status
        enc public_note "🔒"
        enc internal_note "🔒 officer only"
        datetime created_at "timestamp of each status"
    }
    audit_log {
        int id PK
        int actor_user_id "null for system and complainant"
        string action "create | update | delete"
        string entity_type
        int entity_id
        json changed_fields "encrypted values recorded as [encrypted]"
    }
```

## Rules that the schema alone does not enforce

- A plan is **active** only when `status = approved` and `start_date` has arrived. Approval writes a `plan_decisions` row first.
- Changing an approved plan creates a new `draft` version; the old one is `superseded` only when the new one is approved.
- An under-18 student has no `student_profiles` row until a `consents` row exists (checked in the API, returns `consent_required`).
- Grievance status moves `received → under_review → resolved | escalated` (and `escalated → resolved`); each step adds a `grievance_events` row with its timestamp.
- Escalation is flagged after more than the configured number of working days under review, using Monday–Saturday by default and the holiday table.
