from time import monotonic

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.metrics.prometheus import HTTP_REQUEST_DURATION_SECONDS, HTTP_REQUESTS_TOTAL


class PrometheusMetricsMiddleware(BaseHTTPMiddleware):
    """
    Собирать метрики всех входящих HTTP-запросов.

    Метрики фиксируются в finally-блоке, поэтому учитываются и успешные
    ответы, и необработанные исключения, для которых используется статус 500.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Измерить время обработки запроса и обновить Prometheus-метрики."""
        start_time = monotonic()
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code

            return response
        finally:
            endpoint = self._get_endpoint(request)
            duration_seconds = monotonic() - start_time

            HTTP_REQUESTS_TOTAL.labels(
                method=request.method,
                endpoint=endpoint,
                status=str(status_code),
            ).inc()

            HTTP_REQUEST_DURATION_SECONDS.labels(
                method=request.method,
                endpoint=endpoint,
            ).observe(duration_seconds)

    @staticmethod
    def _get_endpoint(request: Request) -> str:
        """
        Вернуть шаблон маршрута для label endpoint.

        Например, запрос к /api/tickets/<uuid> будет учтён как
        /api/tickets/{ticket_id}. Для несуществующих путей используется
        постоянная метка /unmatched без роста кардинальности метрик.
        """
        route = request.scope.get("route")
        route_path = getattr(route, "path", None)

        if isinstance(route_path, str):
            return route_path

        return "/unmatched"
