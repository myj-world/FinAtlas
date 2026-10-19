-- Phase 1: RLS-ready tables for AML screening results and investigation cases.

create table if not exists screenings (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users default auth.uid(),
  transaction_id text,
  transaction_data jsonb not null default '{}'::jsonb,
  deterministic_score numeric(4,3) not null default 0,
  gemini_result jsonb,
  final_score numeric(4,3) not null default 0,
  classification text not null default 'No Match / Low Risk',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists cases (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users default auth.uid(),
  screening_id uuid references screenings(id) on delete cascade,
  status text not null default 'open',
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Row Level Security
alter table screenings enable row level security;
alter table cases enable row level security;

-- Policies for screenings
drop policy if exists "Users can select own screenings" on screenings;
create policy "Users can select own screenings"
  on screenings for select using (auth.uid() = user_id);

drop policy if exists "Users can insert own screenings" on screenings;
create policy "Users can insert own screenings"
  on screenings for insert with check (auth.uid() = user_id);

drop policy if exists "Users can update own screenings" on screenings;
create policy "Users can update own screenings"
  on screenings for update using (auth.uid() = user_id);

drop policy if exists "Users can delete own screenings" on screenings;
create policy "Users can delete own screenings"
  on screenings for delete using (auth.uid() = user_id);

-- Policies for cases
drop policy if exists "Users can select own cases" on cases;
create policy "Users can select own cases"
  on cases for select using (auth.uid() = user_id);

drop policy if exists "Users can insert own cases" on cases;
create policy "Users can insert own cases"
  on cases for insert with check (auth.uid() = user_id);

drop policy if exists "Users can update own cases" on cases;
create policy "Users can update own cases"
  on cases for update using (auth.uid() = user_id);

drop policy if exists "Users can delete own cases" on cases;
create policy "Users can delete own cases"
  on cases for delete using (auth.uid() = user_id);
