import logging
import time

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.database import SessionLocal
from app.schemas import RequestCreate
from app.services import RequestService

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    A middleware that catches the app's exceptions,
    logs it, and re-raises exceptions.
    Stores request data in the database
    and logs request and response details.
    """

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        db = SessionLocal()

        req_service = RequestService(db)

        request_data = RequestCreate(
            method=request.method,
            url=str(request.url),
            headers=self.obtain_necessary_headers(request),
        )
        saved_req = req_service.create_request(request_data)
        request.state.request_data = saved_req

        response = None
        logger.info(
            "Processing request %s %s",
            request.client.host,
            request.url.path,
        )

        try:
            response = await call_next(request)

            if response.status_code >= 400:
                if response.status_code >= 500:
                    logger.critical(
                        "Server error response status_code: %s",
                        response.status_code,
                    )
                else:
                    logger.warning(
                        "Error response %s",
                        response.status_code,
                        extra={"request_id": saved_req.id},
                    )
            else:
                logger.info(
                    "Request completed %s",
                    response.status_code,
                    extra={"request_id": saved_req.id},
                )
            return response
        except HTTPException as exc:
            logger.error(
                "HTTP Exception occurred %s",
                exc.detail,
                extra={
                    "request_id": saved_req.id,
                },
            )
            raise exc
        except Exception as exc:
            logger.critical(
                "Unhandled exception occurred %s",
                str(exc),
                extra={
                    "request_id": saved_req.id,
                },
            )
            raise exc
        finally:
            elapsed_time = time.time() - start_time
            logger.info(
                "Request processed in %.2f seconds",
                elapsed_time,
                extra={"request_id": saved_req.id},
            )
            req_service.update_request(saved_req, request_data)
            db.close()

    def obtain_necessary_headers(self, request: Request) -> dict:
        """
        Extract necessary headers from the request.
        """
        return {
            "User-Agent": request.headers.get("User-Agent", ""),
            "Accept": request.headers.get("Accept", ""),
            "Content-Type": request.headers.get("Content-Type", ""),
            "Host": request.headers.get("Host", ""),
        }

    def get_user_location(self, request: Request) -> str:
        """
        Extract user location from the request headers.
        This method can be customized to include
        any additional logic for determining user location.
        """
        return request.headers.get("X-User-Location", "Unknown")

    def get_client_ip(self, request: Request) -> str:
        """
        Extract client IP address from the request headers.
        """
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0]
        return request.client.host
