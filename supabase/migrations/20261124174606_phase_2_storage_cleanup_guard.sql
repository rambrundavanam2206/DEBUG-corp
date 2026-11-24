create or replace function public.limit_projects() returns trigger
language plpgsql security invoker set search_path='' as $$
begin
 if new.owner_id is distinct from auth.uid() then raise insufficient_privilege using message='owner mismatch'; end if;
 perform pg_advisory_xact_lock(hashtextextended(new.owner_id::text,0));
 if (select count(*) from public.projects where owner_id=new.owner_id)>=3 then raise exception 'project_limit'; end if;
 return new;
end;
$$;
create function public.guard_project_storage() returns trigger
language plpgsql security invoker set search_path='' as $$
begin
 if TG_OP='UPDATE' then
   if new.id<>old.id or new.owner_id<>old.owner_id then raise insufficient_privilege using message='Project identity cannot change'; end if;
   return new;
 end if;
 if exists(select 1 from storage.objects where bucket_id='project-sources' and name=old.owner_id::text || '/' || old.id::text || '/source.json') then
   raise exception 'Delete source files before deleting project';
 end if;
 return old;
end;
$$;
revoke all on function public.guard_project_storage() from public,anon;
grant execute on function public.guard_project_storage() to authenticated;
create trigger project_storage_guard before update or delete on public.projects
for each row execute function public.guard_project_storage();
