import httpx

from lessoncanvas.settings import get_settings


class ClerkAdminError(Exception):
    pass


class ClerkAdminAdapter:
    def delete_user(self, clerk_user_id: str) -> None:
        settings = get_settings()
        if not settings.clerk_secret_key:
            raise ClerkAdminError("clerk secret key not configured")
        try:
            response = httpx.delete(
                f"{settings.clerk_api_base}/v1/users/{clerk_user_id}",
                headers={"Authorization": f"Bearer {settings.clerk_secret_key}"},
                timeout=30,
            )
            response.raise_for_status()
        except httpx.HTTPError as error:
            raise ClerkAdminError("clerk user deletion failed") from error


def get_clerk_admin() -> ClerkAdminAdapter:
    return ClerkAdminAdapter()
