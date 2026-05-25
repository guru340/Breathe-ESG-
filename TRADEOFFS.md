# Tradeoffs

## 1. No Authentication Or Roles

I did not build login, tenant membership, or analyst/admin roles. Multi-tenancy exists in the data model, but the prototype uses one demo tenant so the reviewer can exercise ingestion and approval quickly. In production, row access and lock permissions would be mandatory.

## 2. No Authoritative Emission Factor Library

I used a small factor table in code. A real deployment needs versioned factors by region, reporting framework, date range, source citation, and market/location-based Scope 2 methods. I kept factors simple so the review workflow and data lineage stay inspectable.

## 3. No Live External Integrations

I did not connect to SAP, utility APIs, or Concur directly. The prototype ingests realistic exported CSVs instead. Live integrations would require credentials, customer-specific configuration, retries, permissions, and secrets management. Those are important, but they are less useful than proving the normalized model and analyst review loop first.
