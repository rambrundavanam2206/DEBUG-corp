begin;
insert into auth.users(id) values ('a3cf9ef1-b6d1-4982-b7d1-7ef6fdac5001'),('a3cf9ef1-b6d1-4982-b7d1-7ef6fdac5002');
set local role authenticated;
select set_config('request.jwt.claims','{"sub":"a3cf9ef1-b6d1-4982-b7d1-7ef6fdac5001","role":"authenticated"}',true);
insert into public.projects(id,name,source_type) values ('a3cf9ef1-b6d1-4982-b7d1-7ef6fdac6001','analysis QA','zip');
insert into public.analyses(id,project_id,source_hash,problem_snapshot) values ('a3cf9ef1-b6d1-4982-b7d1-7ef6fdac7001','a3cf9ef1-b6d1-4982-b7d1-7ef6fdac6001',repeat('a',64),'{}');
do $$ begin
 begin
  insert into public.analyses(project_id,source_hash,problem_snapshot) values ('a3cf9ef1-b6d1-4982-b7d1-7ef6fdac6001',repeat('a',64),'{}');
  raise exception 'parallel running analysis allowed';
 exception when unique_violation then null; end;
 begin
  update public.analyses set source_hash=repeat('b',64);
  raise exception 'snapshot modification allowed';
 exception when insufficient_privilege then null; end;
end $$;
update public.analyses set status='completed',result='{"summary":"fixture"}' where id='a3cf9ef1-b6d1-4982-b7d1-7ef6fdac7001';
insert into public.analyses(project_id,source_hash,problem_snapshot,status) select 'a3cf9ef1-b6d1-4982-b7d1-7ef6fdac6001',repeat('a',64),'{}','failed' from generate_series(1,9);
do $$ begin
 begin
  insert into public.analyses(project_id,source_hash,problem_snapshot) values ('a3cf9ef1-b6d1-4982-b7d1-7ef6fdac6001',repeat('a',64),'{}');
  raise exception 'daily quota not enforced';
 exception when raise_exception then if SQLERRM<>'analysis_quota' then raise; end if; end;
end $$;
select set_config('request.jwt.claims','{"sub":"a3cf9ef1-b6d1-4982-b7d1-7ef6fdac5002","role":"authenticated"}',true);
do $$ declare n integer; begin
 if exists(select 1 from public.analyses) then raise exception 'cross user read allowed'; end if;
 update public.analyses set error='forged';get diagnostics n=row_count;
 if n<>0 then raise exception 'cross user update allowed'; end if;
 begin
  insert into public.analyses(project_id,source_hash,problem_snapshot) values ('a3cf9ef1-b6d1-4982-b7d1-7ef6fdac6001',repeat('a',64),'{}');
  raise exception 'cross project insert allowed';
 exception when insufficient_privilege then null; end;
end $$;
set local role anon;
do $$ begin
 begin perform * from public.analyses; raise exception 'anon read allowed';
 exception when insufficient_privilege then null; end;
end $$;
set local role authenticated;
select set_config('request.jwt.claims','{"sub":"a3cf9ef1-b6d1-4982-b7d1-7ef6fdac5001","role":"authenticated"}',true);
delete from public.projects where id='a3cf9ef1-b6d1-4982-b7d1-7ef6fdac6001';
do $$ begin if exists(select 1 from public.analyses) then raise exception 'analysis cascade failed'; end if; end $$;
reset role;
select 'PASS: analysis ownership, snapshot immutability, active-run exclusion, daily quota, cascade and anonymous denial' as result;
rollback;
