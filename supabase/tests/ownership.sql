-- Run with an administrative SQL connection. All fixtures are rolled back.
begin;
insert into auth.users(id) values
('a3cf9ef1-b6d1-4982-b7d1-7ef6fdac1001'),
('a3cf9ef1-b6d1-4982-b7d1-7ef6fdac1002');
select set_config('request.jwt.claims', '{"sub":"a3cf9ef1-b6d1-4982-b7d1-7ef6fdac1001","role":"authenticated"}', true);
insert into public.projects(id,owner_id,name,source_type) values
('a3cf9ef1-b6d1-4982-b7d1-7ef6fdac2001','a3cf9ef1-b6d1-4982-b7d1-7ef6fdac1001','A project','zip');
select set_config('request.jwt.claims', '{"sub":"a3cf9ef1-b6d1-4982-b7d1-7ef6fdac1002","role":"authenticated"}', true);
insert into public.projects(id,owner_id,name,source_type) values
('a3cf9ef1-b6d1-4982-b7d1-7ef6fdac2002','a3cf9ef1-b6d1-4982-b7d1-7ef6fdac1002','B project','github');
insert into public.profiles(id, display_name) values
('a3cf9ef1-b6d1-4982-b7d1-7ef6fdac1001', 'A'),
('a3cf9ef1-b6d1-4982-b7d1-7ef6fdac1002', 'B');
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"a3cf9ef1-b6d1-4982-b7d1-7ef6fdac1001","role":"authenticated"}', true);
do $$
declare n integer;
begin
  if (select count(*) from public.projects) <> 1 then raise exception 'A project isolation failed'; end if;
  if (select count(*) from public.profiles) <> 1 then raise exception 'A profile isolation failed'; end if;
  update public.projects set name = 'not allowed' where owner_id = 'a3cf9ef1-b6d1-4982-b7d1-7ef6fdac1002';
  get diagnostics n = row_count;
  if n <> 0 then raise exception 'Cross-user project update allowed'; end if;
  delete from public.projects where owner_id = 'a3cf9ef1-b6d1-4982-b7d1-7ef6fdac1002';
  get diagnostics n = row_count;
  if n <> 0 then raise exception 'Cross-user project delete allowed'; end if;
  update public.profiles set display_name = 'not allowed' where id = 'a3cf9ef1-b6d1-4982-b7d1-7ef6fdac1002';
  get diagnostics n = row_count;
  if n <> 0 then raise exception 'Cross-user profile update allowed'; end if;
  delete from public.profiles where id = 'a3cf9ef1-b6d1-4982-b7d1-7ef6fdac1002';
  get diagnostics n = row_count;
  if n <> 0 then raise exception 'Cross-user profile delete allowed'; end if;
  begin
    insert into public.projects(owner_id,name,source_type) values ('a3cf9ef1-b6d1-4982-b7d1-7ef6fdac1002','forged','zip');
    raise exception 'Cross-user insert allowed';
  exception when insufficient_privilege then null; end;
  begin
    update public.projects set owner_id='a3cf9ef1-b6d1-4982-b7d1-7ef6fdac1002';
    raise exception 'Ownership transfer allowed';
  exception when insufficient_privilege then null; end;
  begin
    update public.profiles set id='a3cf9ef1-b6d1-4982-b7d1-7ef6fdac1002';
    raise exception 'Profile ownership transfer allowed';
  exception when insufficient_privilege then null; end;
  update public.projects set name='A updated' where owner_id='a3cf9ef1-b6d1-4982-b7d1-7ef6fdac1001';
  get diagnostics n = row_count;
  if n <> 1 then raise exception 'Own update blocked'; end if;
  insert into public.projects(name,source_type) values ('own new project','zip');
  if (select count(*) from public.projects) <> 2 then raise exception 'Own insert blocked'; end if;
  delete from public.projects where name='own new project';
  get diagnostics n = row_count;
  if n <> 1 then raise exception 'Own delete blocked'; end if;
  update public.profiles set display_name='A updated' where id='a3cf9ef1-b6d1-4982-b7d1-7ef6fdac1001';
  get diagnostics n = row_count;
  if n <> 1 then raise exception 'Own profile update blocked'; end if;
end $$;
select set_config('request.jwt.claims', '{"sub":"a3cf9ef1-b6d1-4982-b7d1-7ef6fdac1002","role":"authenticated"}', true);
do $$ begin
  if (select count(*) from public.projects) <> 1 or (select name from public.projects) <> 'B project' then raise exception 'B project isolation failed'; end if;
  if (select count(*) from public.profiles) <> 1 or (select display_name from public.profiles) <> 'B' then raise exception 'B profile isolation failed'; end if;
end $$;
set local role anon;
select set_config('request.jwt.claims', '{"role":"anon"}', true);
do $$ begin
  begin perform * from public.projects; raise exception 'Anonymous projects access allowed';
  exception when insufficient_privilege then null; end;
  begin perform * from public.profiles; raise exception 'Anonymous profiles access allowed';
  exception when insufficient_privilege then null; end;
end $$;
reset role;
select 'PASS: ownership, CRUD, ownership transfer, profile and anonymous isolation checks' as result;
rollback;
