# utils/supabase_storage.py (continuação)

from supabase import create_client
from django.conf import settings
import uuid

supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)


def upload_file(file, folder='uploads'):
    """Upload de arquivo para Supabase Storage"""
    file_extension = file.name.split('.')[-1]
    file_name = f"{folder}/{uuid.uuid4()}.{file_extension}"

    # Upload
    response = supabase.storage.from_(settings.SUPABASE_STORAGE_BUCKET).upload(
        file_name,
        file.read(),
        file_options={"content-type": file.content_type}
    )

    # Retorna URL pública
    public_url = supabase.storage.from_(settings.SUPABASE_STORAGE_BUCKET).get_public_url(file_name)

    return {
        'url': public_url,
        'path': file_name,
        'size': file.size,
        'content_type': file.content_type
    }


def delete_file(file_path):
    """Delete arquivo do Supabase Storage"""
    response = supabase.storage.from_(settings.SUPABASE_STORAGE_BUCKET).remove([file_path])
    return response


def get_signed_url(file_path, expires_in=3600):
    """Gera URL assinada temporária (para arquivos privados)"""
    response = supabase.storage.from_(settings.SUPABASE_STORAGE_BUCKET).create_signed_url(
        file_path,
        expires_in
    )
    return response['signedURL']