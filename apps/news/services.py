import logging

from django.core.exceptions import ImproperlyConfigured, ValidationError

from apps.core.storage import upload_public_image


logger = logging.getLogger(__name__)


class StorageUploadError(Exception):
    """Erro controlado durante upload de imagens de notícias."""


def upload_news_image(uploaded_file, request=None) -> str:
    """
    Envia uma imagem de notícia para o Supabase Storage.

    O argumento request é mantido por compatibilidade com as views atuais.
    """

    try:
        return upload_public_image(
            uploaded_file,
            folder="noticias",
        )

    except ValidationError as exc:
        message = (
            exc.messages[0]
            if getattr(exc, "messages", None)
            else str(exc)
        )
        raise StorageUploadError(message) from exc

    except ImproperlyConfigured as exc:
        logger.exception("Configuração do Supabase Storage inválida.")
        raise StorageUploadError(
            "O armazenamento de imagens não está configurado."
        ) from exc

    except Exception as exc:
        logger.exception(
            "Erro inesperado ao enviar imagem de notícia ao Supabase."
        )
        raise StorageUploadError(
            "Não foi possível enviar a imagem. Tente novamente."
        ) from exc