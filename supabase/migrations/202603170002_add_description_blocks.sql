alter table jobs
add column if not exists description_blocks jsonb not null default '[]'::jsonb;
