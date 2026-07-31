from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from urllib.parse import unquote, urlparse
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, ValidationError
from supabase import Client, create_client


logger = logging.getLogger(__name__)


ALLOWED_IMAGE_TYPES = {
    'image/jpeg': '.jpg',
    'image/png': '.png',
    'image/webp': '.webp',
}

AVATAR_MAX_SIZE = 2 * 1024 * 1024


@lru_cache(maxsize=1)
def get_supabase_admin_client() -> Client:
    if not settings.SUPABASE_URL:
        raise ImproperlyConfigured('SUPABASE_URL não configurada.')

    if not settings.SUPABASE_SERVICE_ROLE_KEY:
        raise ImproperlyConfigured(
            'SUPABASE_SERVICE_ROLE_KEY não configurada.'
        )

    return create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_SERVICE_ROLE_KEY,
    )


def upload_public_image(
    uploaded_file,
    *,
    folder: str = 'noticias',
) -> str:
    content_type = uploaded_file.content_type

    if content_type not in ALLOWED_IMAGE_TYPES:
        raise ValidationError(
            'Formato inválido. Envie JPG, PNG ou WEBP.'
        )

    extension = ALLOWED_IMAGE_TYPES[content_type]
    filename = f'{uuid4().hex}{extension}'
    storage_path = str(Path(folder) / filename).replace('\\', '/')

    client = get_supabase_admin_client()
    bucket = settings.SUPABASE_STORAGE_BUCKET_NEWS

    uploaded_file.seek(0)

    client.storage.from_(bucket).upload(
        path=storage_path,
        file=uploaded_file.read(),
        file_options={
            'content-type': content_type,
            'cache-control': '31536000',
            'upsert': 'false',
        },
    )

    return client.storage.from_(bucket).get_public_url(storage_path)


def extract_public_storage_path(
    file_url: str,
    *,
    bucket: str,
) -> str | None:
    if not file_url:
        return None

    parsed_url = urlparse(file_url)
    supabase_host = urlparse(settings.SUPABASE_URL).netloc

    if parsed_url.netloc != supabase_host:
        return None

    expected_prefix = f'/storage/v1/object/public/{bucket}/'

    if not parsed_url.path.startswith(expected_prefix):
        return None

    storage_path = parsed_url.path.removeprefix(expected_prefix)
    storage_path = unquote(storage_path).strip('/')

    return storage_path or None


def delete_public_image(file_url: str) -> bool:
    bucket = settings.SUPABASE_STORAGE_BUCKET_NEWS
    storage_path = extract_public_storage_path(file_url, bucket=bucket)

    if not storage_path:
        return False

    try:
        client = get_supabase_admin_client()
        client.storage.from_(bucket).remove([storage_path])
        return True
    except Exception:
        logger.exception(
            'Não foi possível remover o arquivo %s do bucket %s.',
            storage_path,
            bucket,
        )
        return False


def upload_private_file(
    uploaded_file,
    *,
    bucket: str,
    folder: str,
    allowed_content_types: set[str],
    max_size: int,
) -> str:
    content_type = (uploaded_file.content_type or '').lower()

    if content_type not in allowed_content_types:
        raise ValidationError('Formato de arquivo não permitido.')

    if uploaded_file.size > max_size:
        max_mb = max_size // (1024 * 1024)
        raise ValidationError(
            f'O arquivo deve ter no máximo {max_mb} MB.'
        )

    original_suffix = Path(uploaded_file.name).suffix.lower()
    safe_suffixes = {
        'application/pdf': '.pdf',
        'image/jpeg': '.jpg',
        'image/png': '.png',
        'image/webp': '.webp',
    }
    extension = safe_suffixes.get(content_type, original_suffix)
    filename = f'{uuid4().hex}{extension}'
    storage_path = str(Path(folder) / filename).replace('\\', '/')

    uploaded_file.seek(0)
    get_supabase_admin_client().storage.from_(bucket).upload(
        path=storage_path,
        file=uploaded_file.read(),
        file_options={
            'content-type': content_type,
            'cache-control': '3600',
            'upsert': 'false',
        },
    )
    return storage_path


def create_private_signed_url(
    storage_path: str,
    *,
    bucket: str,
    expires_in: int = 300,
) -> str:
    response = (
        get_supabase_admin_client()
        .storage.from_(bucket)
        .create_signed_url(storage_path, expires_in)
    )

    if isinstance(response, str):
        return response

    if isinstance(response, dict):
        for key in ('signedURL', 'signedUrl', 'signed_url'):
            if response.get(key):
                return response[key]

        data = response.get('data')
        if isinstance(data, dict):
            for key in ('signedURL', 'signedUrl', 'signed_url'):
                if data.get(key):
                    return data[key]

    data = getattr(response, 'data', None)
    for source in (response, data):
        if source is None:
            continue
        for attribute in ('signed_url', 'signedURL', 'signedUrl'):
            value = getattr(source, attribute, None)
            if value:
                return value

    raise RuntimeError('O Supabase não retornou uma URL assinada.')


def delete_private_files(
    storage_paths: list[str],
    *,
    bucket: str,
) -> bool:
    valid_paths = [path for path in storage_paths if path]
    if not valid_paths:
        return False

    try:
        get_supabase_admin_client().storage.from_(bucket).remove(valid_paths)
        return True
    except Exception:
        logger.exception(
            'Não foi possível remover arquivos privados do bucket %s.',
            bucket,
        )
        return False


def upload_avatar(uploaded_file, *, user_id: int | str) -> str:
    """
    Envia um avatar validado ao bucket privado de avatares.

    O arquivo é gravado em uma pasta própria do usuário e o banco guarda
    somente o caminho interno, nunca uma URL assinada temporária.
    """
    bucket = settings.SUPABASE_STORAGE_BUCKET_AVATARS

    return upload_private_file(
        uploaded_file,
        bucket=bucket,
        folder=f'usuarios/{user_id}',
        allowed_content_types=set(ALLOWED_IMAGE_TYPES),
        max_size=AVATAR_MAX_SIZE,
    )


def create_avatar_signed_url(
    storage_path: str,
    *,
    expires_in: int = 3600,
) -> str:
    if not storage_path:
        return ''

    return create_private_signed_url(
        storage_path,
        bucket=settings.SUPABASE_STORAGE_BUCKET_AVATARS,
        expires_in=expires_in,
    )


def delete_avatar(storage_path: str) -> bool:
    if not storage_path:
        return False

    return delete_private_files(
        [storage_path],
        bucket=settings.SUPABASE_STORAGE_BUCKET_AVATARS,
    )