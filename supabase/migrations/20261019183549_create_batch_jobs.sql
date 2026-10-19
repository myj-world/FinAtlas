-- Phase 4: batch job tracking for async screening.

create table if not exists batches (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users default auth.uid(),
  status text not null default 'pending',
  total integer not null default 0,
  processed integer not null default 0,
  succeeded integer not null default 0,
  failed integer not null default 0,
  results jsonb default '[]'::jsonb,
  error_message text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint valid_batch_status check (status in ('pending', 'running', 'completed', 'failed'))
);

-- Row Level Security
alter table batches enable row level security;

drop policy if exists "Users can select own batches" on batches;
create policy "Users can select own batches"
  on batches for select using (auth.uid() = user_id);

drop policy if exists "Users can insert own batches" on batches;
create policy "Users can insert own batches"
  on batches for insert with check (auth.uid() = user_id);

drop policy if exists "Users can update own batches" on batches;
create policy "Users can update own batches"
  on batches for update using (auth.uid() = user_id);

drop policy if exists "Users can delete own batches" on batches;
create policy "Users can delete own batches"
  on batches for delete using (auth.uid() = user_id);

-- Indexes for common dashboard filters.
create index if not exists idx_screenings_user_created on screenings (user_id, created_at desc);
create index if not exists idx_cases_user_created on cases (user_id, created_at desc);
create index if not exists idx_batches_user_created on batches (user_id, created_at desc);
