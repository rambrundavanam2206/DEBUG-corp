create table public.analyses (
 id uuid primary key default gen_random_uuid(),
 project_id uuid not null references public.projects(id) on delete cascade,
 owner_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
 source_hash text not null check (source_hash ~ '^[a-f0-9]{64}$'),
 commit_sha text not null default '',
 problem_snapshot jsonb not null check (octet_length(problem_snapshot::text)<=180000),
 status text not null default 'running' check (status in ('running','completed','needs_context','failed')),
 provider text not null default '' check(length(provider)<=30),
 model text not null default '' check(length(model)<=200),
 result jsonb check (octet_length(result::text)<=120000),
 error text not null default '' check(length(error)<=2000),
 error_code text not null default '' check(length(error_code)<=80),
 usage jsonb not null default '{}' check(octet_length(usage::text)<=5000),
 created_at timestamptz not null default now(),
 updated_at timestamptz not null default now()
);
create index analyses_project_created_idx on public.analyses(project_id,created_at desc);
create index analyses_owner_created_idx on public.analyses(owner_id,created_at desc);
create unique index analyses_one_running_per_owner on public.analyses(owner_id) where status='running';
alter table public.analyses enable row level security;
revoke all on public.analyses from public,anon;
grant select,insert,update on public.analyses to authenticated;
create policy analyses_read on public.analyses for select to authenticated
using(owner_id=(select auth.uid()) and exists(select 1 from public.projects p where p.id=analyses.project_id and p.owner_id=(select auth.uid())));
create policy analyses_insert on public.analyses for insert to authenticated
with check(owner_id=(select auth.uid()) and exists(select 1 from public.projects p where p.id=analyses.project_id and p.owner_id=(select auth.uid())));
create policy analyses_update on public.analyses for update to authenticated
using(owner_id=(select auth.uid()) and exists(select 1 from public.projects p where p.id=analyses.project_id and p.owner_id=(select auth.uid())))
with check(owner_id=(select auth.uid()) and exists(select 1 from public.projects p where p.id=analyses.project_id and p.owner_id=(select auth.uid())));

create function public.guard_analysis() returns trigger
language plpgsql security invoker set search_path='' as $$
begin
 if TG_OP='INSERT' then
  if new.owner_id is distinct from auth.uid() then raise insufficient_privilege; end if;
  perform pg_advisory_xact_lock(hashtextextended(new.owner_id::text,1));
  if (select count(*) from public.analyses where owner_id=new.owner_id and created_at>now()-interval '24 hours')>=10
    or (select count(*) from public.analyses where project_id=new.project_id)>=30 then
     raise exception 'analysis_quota';
  end if;
  new.created_at:=now();
 else
  if new.id<>old.id or new.owner_id<>old.owner_id or new.project_id<>old.project_id
     or new.source_hash<>old.source_hash or new.commit_sha<>old.commit_sha
     or new.problem_snapshot<>old.problem_snapshot then raise insufficient_privilege using message='Analysis snapshot cannot change'; end if;
  new.created_at:=old.created_at;
 end if;
 new.updated_at:=now();
 return new;
end;
$$;
revoke all on function public.guard_analysis() from public,anon;
grant execute on function public.guard_analysis() to authenticated;
create trigger analyses_guard before insert or update on public.analyses for each row execute function public.guard_analysis();
