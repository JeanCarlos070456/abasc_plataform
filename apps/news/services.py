import logging
from uuid import uuid4

import httpx
from django.conf import settings
from django.core.files.storage import default_storage

logger = logging.getLogger(__name__)

class StorageUploadError(Exception):
    pass

def upload_news_image(uploaded_file, request=None):
    image_format = getattr(
        getattr(uploaded_file, 'image', None),
        'format',
        '',
    ).upper()
    formats = {
        'JPEG': ('.jpg', 'image/jpeg'),
        'PNG': ('.png', 'image/png'),
        'WEBP': ('.webp', 'image/webp'),
    }
    if image_format not in formats:
        raise StorageUploadError(
            'Formato inválido. Use JPEG, PNG ou WEBP.'
        )
    extension, content_type = formats[image_format]
    object_name = f'news/{uuid4().hex}{extension}'
    uploaded_file.seek(0)

    if settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY:
        endpoint = (
            f'{settings.SUPABASE_URL}/storage/v1/object/'
            f'{settings.SUPABASE_STORAGE_BUCKET_NEWS}/{object_name}'
        )
        headers = {
            'apikey': settings.SUPABASE_SERVICE_ROLE_KEY,
            'Authorization': (
                f'Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}'
            ),
            'Content-Type': content_type,
            'x-upsert': 'false',
        }
        try:
            response = httpx.post(
                endpoint,
                headers=headers,
                content=uploaded_file.read(),
                timeout=30.0,
            )
        except httpx.HTTPError as exc:
            logger.exception(
                'Erro ao enviar imagem ao Supabase Storage'
            )
            raise StorageUploadError(
                'Não foi possível enviar a imagem ao armazenamento.'
            ) from exc

        if response.status_code >= 400:
            logger.error(
                'Supabase Storage respondeu %s: %s',
                response.status_code,
                response.text,
            )
            raise StorageUploadError(
                'O Supabase Storage recusou o upload. '
                'Verifique o bucket e as credenciais.'
            )
        return (
            f'{settings.SUPABASE_URL}/storage/v1/object/public/'
            f'{settings.SUPABASE_STORAGE_BUCKET_NEWS}/{object_name}'
        )

    if not settings.DEBUG:
        raise StorageUploadError(
            'O Supabase Storage não está configurado para uploads.'
        )

    saved_path = default_storage.save(object_name, uploaded_file)
    url = default_storage.url(saved_path)
    return request.build_absolute_uri(url) if request else url
