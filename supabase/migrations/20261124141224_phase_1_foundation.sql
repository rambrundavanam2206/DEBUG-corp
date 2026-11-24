-- Phase 1: user-scoped foundation. No privileged auth triggers or service keys.
create table public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  display_name text not null default '' check (char_length(display_name) <= 80),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create table public.projects (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id) on delete cascade default auth.uid(),
  name text not null check (char_length(trim(name)) between 1 and 120),
  source_type text not null check (source_type in ('zip', 'github')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index projects_owner_created_idx on public.projects(owner_id, created_at desc);

create function public.set_updated_at() returns trigger
language plpgsql security invoker set search_path = '' as $$
begin
  new.created_at := old.created_at;
  new.updated_at := now();
  return new;
end;
$$;
revoke all on function public.set_updated_at() from public, anon;
grant execute on function public.set_updated_at() to authenticated;
create trigger profiles_updated before update on public.profiles
for each row execute function public.set_updated_at();
create trigger projects_updated before update on public.projects
for each row execute function public.set_updated_at();

alter table public.profiles enable row level security;
alter table public.projects enable row level security;
revoke all on public.profiles, public.projects from anon, public;
grant select, insert, update, delete on public.profiles, public.projects to authenticated;

create policy profiles_select_own on public.profiles for select to authenticated
using ((select auth.uid()) = id);
create policy profiles_insert_own on public.profiles for insert to authenticated
with check ((select auth.uid()) = id);
create policy profiles_update_own on public.profiles for update to authenticated
using ((select auth.uid()) = id) with check ((select auth.uid()) = id);
create policy profiles_delete_own on public.profiles for delete to authenticated
using ((select auth.uid()) = id);

create policy projects_select_own on public.projects for select to authenticated
using ((select auth.uid()) = owner_id);
create policy projects_insert_own on public.projects for insert to authenticated
with check ((select auth.uid()) = owner_id);
create policy projects_update_own on public.projects for update to authenticated
using ((select auth.uid()) = owner_id) with check ((select auth.uid()) = owner_id);
create policy projects_delete_own on public.projects for delete to authenticated
using ((select auth.uid()) = owner_id);
