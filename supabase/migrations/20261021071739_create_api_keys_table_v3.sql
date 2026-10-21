-- Create api_keys table for per-user plaintext API keys
create table if not exists api_keys (
  id uuid primary key default gen_random_uuid(),
  user_id uuid default auth.uid() references auth.users (id),
  key_text text not null,
  revoked boolean not null default false,
  created_at timestamptz not null default now(),
  revoked_at timestamptz
);

alter table api_keys enable row level security;

-- Policies
drop policy if exists "Users can insert own api keys" on api_keys;
create policy "Users can insert own api keys" on api_keys
  for insert with check (auth.uid() = user_id);

drop policy if exists "Users can select own api keys" on api_keys;
create policy "Users can select own api keys" on api_keys
  for select using (auth.uid() = user_id);

drop policy if exists "Users can update own api keys" on api_keys;
create policy "Users can update own api keys" on api_keys
  for update using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists "Users can delete own api keys" on api_keys;
create policy "Users can delete own api keys" on api_keys
  for delete using (auth.uid() = user_id);

create index if not exists idx_api_keys_user_revoked on api_keys (user_id, revoked);
