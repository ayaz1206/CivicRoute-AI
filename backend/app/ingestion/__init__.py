"""Boston 311 data ingestion (M2).

Pulls recent Boston 311 service requests from the CKAN Open Data API and stores
them in the dedicated ``historical_311_requests`` table. Ingestion is:

- validated: raw records are parsed/normalized with lenient field handling;
  records missing the natural key are skipped and counted.
- idempotent: records are upserted on ``case_enquiry_id`` so re-running does not
  create duplicates.

This module performs no LLM/agent work.
"""
