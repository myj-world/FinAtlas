-- Phase 4: persist rule and sanctions-hit details for dashboard drill-downs.

alter table screenings
  add column if not exists sanctions_hits jsonb default '[]'::jsonb,
  add column if not exists rules jsonb default '[]'::jsonb;
