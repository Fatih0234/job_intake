create extension if not exists pgcrypto;

create or replace function set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = timezone('utc', now());
  return new;
end;
$$;

create table if not exists pipeline_runs (
  id uuid primary key default gen_random_uuid(),
  stage text not null,
  status text not null,
  started_at timestamptz not null default timezone('utc', now()),
  finished_at timestamptz,
  counters jsonb not null default '{}'::jsonb,
  summary jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists search_definitions (
  id uuid primary key default gen_random_uuid(),
  name text not null unique,
  platform text not null default 'linkedin',
  city text not null,
  role_family text not null,
  keywords jsonb not null default '[]'::jsonb,
  query_text text,
  is_enabled boolean not null default true,
  config_payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists jobs (
  id uuid primary key default gen_random_uuid(),
  canonical_job_key text not null unique,
  platform text not null default 'linkedin',
  external_job_id text,
  source_job_url text not null,
  normalized_job_url text not null,
  title text not null,
  company text not null,
  city text not null,
  country text not null default 'Germany',
  location_raw text,
  description_text text,
  employment_type text,
  seniority text,
  posted_text text,
  posted_at timestamptz,
  first_seen_at timestamptz not null default timezone('utc', now()),
  last_seen_at timestamptz not null default timezone('utc', now()),
  source_search_name text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists job_discoveries (
  id uuid primary key default gen_random_uuid(),
  search_definition_id uuid references search_definitions(id) on delete set null,
  pipeline_run_id uuid references pipeline_runs(id) on delete set null,
  job_id uuid references jobs(id) on delete set null,
  platform text not null default 'linkedin',
  external_job_id text,
  discovery_url text not null,
  rank_position integer,
  discovered_at timestamptz not null default timezone('utc', now()),
  raw_payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists job_classifications (
  id uuid primary key default gen_random_uuid(),
  job_id uuid not null unique references jobs(id) on delete cascade,
  student_fit text not null,
  role_family text not null,
  shortlist_decision boolean not null default false,
  shortlist_reason text,
  rule_version text not null default 'v1',
  signals jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists notion_sync_state (
  id uuid primary key default gen_random_uuid(),
  job_id uuid not null unique references jobs(id) on delete cascade,
  notion_page_id text,
  sync_status text not null default 'pending',
  last_attempted_at timestamptz,
  last_synced_at timestamptz,
  last_error text,
  payload_checksum text,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create index if not exists idx_search_definitions_enabled
  on search_definitions (is_enabled, city, role_family);

create index if not exists idx_jobs_external_job_id
  on jobs (external_job_id);

create index if not exists idx_jobs_last_seen_at
  on jobs (last_seen_at desc);

create index if not exists idx_jobs_city
  on jobs (city);

create index if not exists idx_job_discoveries_search_definition
  on job_discoveries (search_definition_id, discovered_at desc);

create index if not exists idx_job_discoveries_external_job_id
  on job_discoveries (external_job_id);

create index if not exists idx_job_classifications_shortlist
  on job_classifications (shortlist_decision, student_fit, role_family);

create index if not exists idx_notion_sync_state_status
  on notion_sync_state (sync_status, last_synced_at);

create index if not exists idx_pipeline_runs_stage_status
  on pipeline_runs (stage, status, started_at desc);

create trigger pipeline_runs_set_updated_at
before update on pipeline_runs
for each row execute function set_updated_at();

create trigger search_definitions_set_updated_at
before update on search_definitions
for each row execute function set_updated_at();

create trigger jobs_set_updated_at
before update on jobs
for each row execute function set_updated_at();

create trigger job_discoveries_set_updated_at
before update on job_discoveries
for each row execute function set_updated_at();

create trigger job_classifications_set_updated_at
before update on job_classifications
for each row execute function set_updated_at();

create trigger notion_sync_state_set_updated_at
before update on notion_sync_state
for each row execute function set_updated_at();

