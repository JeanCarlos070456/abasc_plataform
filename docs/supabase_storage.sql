-- Buckets públicos para leitura. Escrita realizada pelo backend com Service Role.
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values
    (
        'abasc-news',
        'abasc-news',
        true,
        5242880,
        array['image/jpeg', 'image/png', 'image/webp']
    ),
    (
        'abasc-avatars',
        'abasc-avatars',
        true,
        5242880,
        array['image/jpeg', 'image/png', 'image/webp']
    )
on conflict (id) do update set
    public = excluded.public,
    file_size_limit = excluded.file_size_limit,
    allowed_mime_types = excluded.allowed_mime_types;
