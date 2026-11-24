alter policy sources_select on storage.objects using (bucket_id='project-sources' and (storage.foldername(storage.objects.name))[1]=(select auth.uid())::text
and exists(select 1 from public.projects p where p.id::text=(storage.foldername(storage.objects.name))[2] and p.owner_id=(select auth.uid()))
and storage.objects.name=(select auth.uid())::text || '/' || (storage.foldername(storage.objects.name))[2] || '/source.json');
alter policy sources_insert on storage.objects with check (bucket_id='project-sources' and (storage.foldername(storage.objects.name))[1]=(select auth.uid())::text
and exists(select 1 from public.projects p where p.id::text=(storage.foldername(storage.objects.name))[2] and p.owner_id=(select auth.uid()))
and storage.objects.name=(select auth.uid())::text || '/' || (storage.foldername(storage.objects.name))[2] || '/source.json');
alter policy sources_update on storage.objects using (bucket_id='project-sources' and (storage.foldername(storage.objects.name))[1]=(select auth.uid())::text
and exists(select 1 from public.projects p where p.id::text=(storage.foldername(storage.objects.name))[2] and p.owner_id=(select auth.uid()))
and storage.objects.name=(select auth.uid())::text || '/' || (storage.foldername(storage.objects.name))[2] || '/source.json') with check (bucket_id='project-sources' and (storage.foldername(storage.objects.name))[1]=(select auth.uid())::text
and exists(select 1 from public.projects p where p.id::text=(storage.foldername(storage.objects.name))[2] and p.owner_id=(select auth.uid()))
and storage.objects.name=(select auth.uid())::text || '/' || (storage.foldername(storage.objects.name))[2] || '/source.json');
