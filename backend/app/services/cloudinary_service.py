"""Cloudinary storage service with graceful degradation.

Stores user documents (legal files, images) on Cloudinary. When Cloudinary is
not configured, calls raise DocumentStorageError which routers convert into a
clear 503 response rather than crashing.
"""

import logging
from typing import Any, Optional

from app.config import settings

logger = logging.getLogger("legalconnect.cloudinary")


class DocumentStorageError(Exception):
    """Raised when Cloudinary is unavailable or unconfigured."""


class CloudinaryService:
    def __init__(self) -> None:
        import cloudinary

        self._cloudinary = cloudinary

    @property
    def is_configured(self) -> bool:
        return settings.is_cloudinary_configured

    def _configure(self) -> None:
        if not self.is_configured:
            raise DocumentStorageError(
                "Cloudinary is not configured. Set CLOUDINARY_CLOUD_NAME, "
                "CLOUDINARY_API_KEY, and CLOUDINARY_API_SECRET in your .env file."
            )
        self._cloudinary.config(
            cloud_name=settings.cloudinary_cloud_name,
            api_key=settings.cloudinary_api_key,
            api_secret=settings.cloudinary_api_secret,
            secure=True,
        )

    async def upload_bytes(
        self,
        *,
        data: bytes,
        filename: str,
        resource_type: str = "raw",
        folder: Optional[str] = None,
    ) -> dict[str, Any]:
        """Upload raw bytes and return Cloudinary metadata for a new document."""
        self._configure()
        from cloudinary import uploader

        folder = folder or settings.cloudinary_folder
        try:
            info = uploader.upload(
                data,
                resource_type=resource_type,
                folder=folder,
                public_id="",
                use_filename=True,
                unique_filename=True,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Cloudinary upload failed: %s", exc)
            raise DocumentStorageError("Could not upload document to Cloudinary") from exc
        return {
            "public_id": info.get("public_id", ""),
            "url": info.get("url", ""),
            "secure_url": info.get("secure_url", ""),
            "bytes": int(info.get("bytes", 0)),
            "format": info.get("format"),
            "resource_type": info.get("resource_type", resource_type),
        }

    async def delete(self, public_id: str, resource_type: str = "raw") -> None:
        """Delete a resource from Cloudinary."""
        self._configure()
        from cloudinary import api

        try:
            await self._async_delete(api, public_id, resource_type)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Cloudinary delete failed for %s: %s", public_id, exc)
            raise DocumentStorageError("Could not delete document from Cloudinary") from exc

    async def _async_delete(self, api, public_id: str, resource_type: str) -> None:
        # api.delete_resources is synchronous and network-bound; run in a thread.
        import anyio

        await anyio.to_thread.run_sync(
            lambda: api.delete_resources([public_id], resource_type=resource_type)
        )

    def signed_url(self, public_id: str, resource_type: str = "raw") -> str:
        """Return a time-limited signed URL for a resource."""
        self._configure()
        from cloudinary import utils

        try:
            url, _ = utils.cloudinary_url(
                public_id,
                resource_type=resource_type,
                sign_url=True,
                secure=True,
            )
            return url
        except Exception as exc:  # noqa: BLE001
            logger.warning("Cloudinary signed URL failed: %s", exc)
            raise DocumentStorageError("Could not generate a download link") from exc


cloudinary_service = CloudinaryService()
