# Data Model

The model separates raw source truth from normalized analyst-review rows.

## Core Tables

`Tenant` is the customer boundary. Every facility, source, ingestion batch, and emissions row belongs to one tenant. This keeps the prototype multi-tenant without adding authentication complexity.

`Facility` maps client-specific site codes such as `DE01` or `US01` to a real site name and country. SAP plant codes and utility site codes are treated as source identifiers that must resolve through this lookup before the row can be trusted.

`SourceSystem` records the configured upstream system for a tenant: SAP, utility CSV, or travel export. It is deliberately separate from a batch because the same source will produce many files over time.

`IngestionBatch` records each upload: source, filename, received time, processed time, row count, failed count, and status. This is the operational handle analysts can refer to when a file import is questioned.

`RawRecord` stores the original parsed CSV row as JSON, row number, row hash, and any parse error. This is the source-of-truth layer. It is not overwritten when an analyst edits a normalized row.

`EmissionActivity` is the normalized review row. It stores scope, category, date or period, original quantity/unit, normalized quantity/unit, emission factor, calculated kgCO2e, flags, status, source reference, and analyst notes. It has a one-to-one link to `RawRecord` so auditors can move from reported emissions back to the exact source payload.

`AuditEvent` records every analyst edit and status transition with before/after snapshots. Approved rows can be locked; locked rows cannot be edited through the API.

## Scope Categorization

SAP diesel, gasoline, and natural gas procurement is Scope 1 because it represents fuel combusted by company-controlled operations. SAP steel and paper purchases are Scope 3 purchased goods.

Utility electricity is Scope 2 purchased electricity.

Travel rows are Scope 3 business travel. Flights use distance, hotels use nights, and ground transport uses distance.

## Unit Normalization

The ingestors keep both original and normalized quantities. Examples:

- `GAL` converts to litres.
- `MWh` converts to kWh.
- `TON` converts to kg.
- `MI` converts to km.

Rows with unknown units are still stored, but they receive `unknown_unit` and usually `missing_factor` flags so an analyst can resolve them without losing source traceability.

## Review Statuses

- `needs_review`: created by ingestion.
- `approved`: analyst accepts row for reporting.
- `rejected`: analyst excludes row but preserves evidence.
- `locked`: approved row frozen for audit package.

This is intentionally simple. A real system would add role-based approvals, versioned factor sets, and report-period close controls.
