import time
from datetime import timedelta

from django.core.cache import cache
from django.conf import settings
from django.db.models import Count, F
from django.db.models.functions import TruncDate
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.utils import timezone
from rest_framework import mixins, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.generics import CreateAPIView
from rest_framework.response import Response

from .models import Click, Link
from .serializers import LinkSerializer, LinkUpdateSerializer, RegisterSerializer


def cache_key(code):
    return f"link:{code}"


class RegisterView(CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class LinkViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Create, list, update and delete the logged-in user's short links."""

    def get_queryset(self):
        return Link.objects.filter(owner=self.request.user)

    def get_serializer_class(self):
        if self.action in ("update", "partial_update"):
            return LinkUpdateSerializer
        return LinkSerializer

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    def perform_update(self, serializer):
        link = serializer.save()
        cache.delete(cache_key(link.short_code))

    def perform_destroy(self, instance):
        cache.delete(cache_key(instance.short_code))
        instance.delete()

    @action(detail=True, methods=["get"])
    def stats(self, request, pk=None):
        link = self.get_object()
        since = timezone.now() - timedelta(days=7)
        daily = (
            link.clicks.filter(clicked_at__gte=since)
            .annotate(day=TruncDate("clicked_at"))
            .values("day")
            .annotate(count=Count("id"))
            .order_by("day")
        )
        referrers = (
            link.clicks.exclude(referrer="")
            .values("referrer")
            .annotate(count=Count("id"))
            .order_by("-count")[:5]
        )
        return Response(
            {
                "short_code": link.short_code,
                "total_clicks": link.click_count,
                "last_7_days": list(daily),
                "top_referrers": list(referrers),
            }
        )


def redirect_view(request, code):
    """Public redirect. Looks up the link in cache first, then the DB."""
    data = cache.get(cache_key(code))
    if data is None:
        link = Link.objects.filter(short_code=code).first()
        if link is None:
            raise Http404("Short link not found")
        data = {
            "id": link.id,
            "url": link.original_url,
            "active": link.is_active,
            "expires": link.expires_at.timestamp() if link.expires_at else None,
        }
        cache.set(cache_key(code), data, settings.REDIRECT_CACHE_SECONDS)

    if not data["active"] or (data["expires"] and data["expires"] < time.time()):
        return HttpResponse("This link is no longer available.", status=410)

    Link.objects.filter(id=data["id"]).update(click_count=F("click_count") + 1)
    Click.objects.create(
        link_id=data["id"],
        user_agent=request.META.get("HTTP_USER_AGENT", "")[:300],
        referrer=request.META.get("HTTP_REFERER", "")[:500],
        ip_address=request.META.get("REMOTE_ADDR"),
    )
    return HttpResponseRedirect(data["url"])
