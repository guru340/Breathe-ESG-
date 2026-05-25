# Decisions

## Source Mechanisms

SAP is handled as an uploaded CSV flat file shaped like an IDoc/export projection, not as live OData or BAPI. For a four-day prototype this gives realistic SAP messiness: German headers can be mapped, dates vary, units are inconsistent, plant codes require lookup, and material descriptions drive classification.

Utility data is handled as a portal CSV bill export. Many facilities teams can get monthly CSVs even when interval APIs are unavailable or require authorization from the utility account holder. The model accounts for meter number, tariff, demand, and billing periods that do not match calendar months.

Travel data is handled as a Concur-like expense export, not a live API integration. This captures the useful emissions shape: expense type, employee, vendor, dates, origin/destination, distance, nights, and cost center. Live Concur auth/scopes are integration work, not the core modeling risk for this assignment.

## Normalization Choices

I used a small in-code factor table instead of a factor database. The assignment is about ingestion and review judgment, so the prototype makes factor application visible without pretending to solve authoritative factor governance.

Every source row creates exactly one normalized activity row. That keeps audit traceability direct. A production system would split some rows, such as hotel folios or mixed procurement invoices, into multiple activity lines.

Unknown facilities and unknown units do not block ingestion. They create flagged rows. Analysts should see bad data in the queue instead of having it disappear into an import error log.

## PM Questions

- Which client ERP version and export channel should be prioritized: ECC IDoc flat files, S/4HANA OData, or BW extracts?
- Should analysts be allowed to edit emission factors directly, or only choose from approved factor libraries?
- What is the audit package boundary: calendar month, fiscal period, or reporting campaign?
- Should rejected rows be excluded from dashboards or included as failed evidence?
- Do we need a maker-checker approval workflow before locking?

## Ignored Subsets

SAP handling ignores nested IDoc segment parsing and live plant/material master sync.

Utility handling ignores PDF bill extraction, interval data granularity, renewable energy certificates, and market-based Scope 2.

Travel handling ignores airport-code distance lookup, fare class radiative forcing, rail, meals, and complex hotel itemization.
