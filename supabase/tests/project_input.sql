begin;
insert into auth.users(id) values ('a3cf9ef1-b6d1-4982-b7d1-7ef6fdac3001'),('a3cf9ef1-b6d1-4982-b7d1-7ef6fdac3002');
set local role authenticated;
select set_config('request.jwt.claims','{"sub":"a3cf9ef1-b6d1-4982-b7d1-7ef6fdac3001","role":"authenticated"}',true);
insert into public.projects(id,name,source_type) values ('a3cf9ef1-b6d1-4982-b7d1-7ef6fdac4001','storage check','zip');
insert into storage.objects(bucket_id,name) values ('project-sources','a3cf9ef1-b6d1-4982-b7d1-7ef6fdac3001/a3cf9ef1-b6d1-4982-b7d1-7ef6fdac4001/source.json');
insert into public.projects(name,source_type) values ('second','zip'),('third','zip');
do $$ begin
 begin
   insert into public.projects(name,source_type) values ('fourth','zip');
   raise exception 'quota not enforced';
 exception when raise_exception then
   if SQLERRM <> 'project_limit' then raise; end if;
 end;
 begin
   delete from public.projects where id='a3cf9ef1-b6d1-4982-b7d1-7ef6fdac4001';
   raise exception 'orphan allowed';
 exception when raise_exception then
   if SQLERRM <> 'Delete source files before deleting project' then raise; end if;
 end;
 begin
   update public.projects set id=gen_random_uuid() where id='a3cf9ef1-b6d1-4982-b7d1-7ef6fdac4001';
   raise exception 'identity change allowed';
 exception when insufficient_privilege then null;
 end;
end $$;
select set_config('request.jwt.claims','{"sub":"a3cf9ef1-b6d1-4982-b7d1-7ef6fdac3002","role":"authenticated"}',true);
do $$ declare n integer; begin
 if exists(select 1 from storage.objects where bucket_id='project-sources') then raise exception 'cross-user storage read'; end if;
 update storage.objects set name='stolen' where bucket_id='project-sources';
 get diagnostics n = row_count;
 if n<>0 then raise exception 'cross-user update'; end if;
 begin
 insert into storage.objects(bucket_id,name) values('project-sources','a3cf9ef1-b6d1-4982-b7d1-7ef6fdac3001/a3cf9ef1-b6d1-4982-b7d1-7ef6fdac4001/source.json');
 raise exception 'cross-user write';
 exception when insufficient_privilege then null; end;
end $$;
select set_config('request.jwt.claims','{"sub":"a3cf9ef1-b6d1-4982-b7d1-7ef6fdac3001","role":"authenticated"}',true);
-- Storage deletion is verified through the live Storage API, never direct SQL.
reset role;
select 'PASS: private storage isolation, project quota, identity and orphan protection' as result;
rollback;
