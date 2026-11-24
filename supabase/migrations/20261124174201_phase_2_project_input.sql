alter table public.projects
 add column status text not null default 'pending' check (status in ('pending','importing','ready','failed','deleting')),
 add column repo_url text not null default '' check (length(repo_url)<=300),
 add column branch text not null default '' check (length(branch)<=200),
 add column commit_sha text not null default '' check (commit_sha='' or commit_sha ~ '^[a-f0-9]{40}$'),
 add column problem text not null default '' check (length(problem)<=30000),
 add column command text not null default '' check (length(command)<=1000),
 add column expected text not null default '' check (length(expected)<=5000),
 add column reproduction text not null default '' check (length(reproduction)<=5000),
 add column import_error text not null default '' check (length(import_error)<=2000),
 add column operation_started timestamptz,
 add column manifest jsonb not null default '[]' check (jsonb_typeof(manifest)='array' and jsonb_array_length(manifest)<=500 and octet_length(manifest::text)<=500000),
 add column skipped jsonb not null default '[]' check (jsonb_typeof(skipped)='array' and jsonb_array_length(skipped)<=3000 and octet_length(skipped::text)<=2000000);

create function public.limit_projects() returns trigger
language plpgsql security invoker set search_path='' as $$
begin
 if new.owner_id is distinct from auth.uid() then raise exception 'owner mismatch'; end if;
 perform pg_advisory_xact_lock(hashtextextended(new.owner_id::text,0));
 if (select count(*) from public.projects where owner_id=new.owner_id)>=3 then
  raise exception 'project_limit';
 end if;
 return new;
end;
$$;
revoke all on function public.limit_projects() from public,anon;
grant execute on function public.limit_projects() to authenticated;
create trigger project_quota before insert on public.projects
for each row execute function public.limit_projects();

insert into storage.buckets(id,name,public,file_size_limit,allowed_mime_types)
values ('project-sources','project-sources',false,47185920,array['application/json']);

create policy sources_select on storage.objects for select to authenticated
using (bucket_id='project-sources' and (storage.foldername(name))[1]=(select auth.uid())::text
and exists(select 1 from public.projects p where p.id::text=(storage.foldername(name))[2] and p.owner_id=(select auth.uid()))
and name=(select auth.uid())::text || '/' || (storage.foldername(name))[2] || '/source.json');
create policy sources_insert on storage.objects for insert to authenticated
with check (bucket_id='project-sources' and (storage.foldername(name))[1]=(select auth.uid())::text
and exists(select 1 from public.projects p where p.id::text=(storage.foldername(name))[2] and p.owner_id=(select auth.uid()))
and name=(select auth.uid())::text || '/' || (storage.foldername(name))[2] || '/source.json');
create policy sources_update on storage.objects for update to authenticated
using (bucket_id='project-sources' and (storage.foldername(name))[1]=(select auth.uid())::text
and exists(select 1 from public.projects p where p.id::text=(storage.foldername(name))[2] and p.owner_id=(select auth.uid())))
with check (bucket_id='project-sources' and (storage.foldername(name))[1]=(select auth.uid())::text
and exists(select 1 from public.projects p where p.id::text=(storage.foldername(name))[2] and p.owner_id=(select auth.uid()))
and name=(select auth.uid())::text || '/' || (storage.foldername(name))[2] || '/source.json');
create policy sources_delete on storage.objects for delete to authenticated
using (bucket_id='project-sources' and (storage.foldername(name))[1]=(select auth.uid())::text);
