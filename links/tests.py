from datetime import timedelta

from django.contrib.auth.models import User
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from .models import Link


class AuthTests(APITestCase):
    def test_register_and_login(self):
        client = APIClient()
        res = client.post("/api/auth/register/", {"username": "bob", "password": "strongpass1"})
        self.assertEqual(res.status_code, 201)
        res = client.post("/api/auth/login/", {"username": "bob", "password": "strongpass1"})
        self.assertEqual(res.status_code, 200)
        self.assertIn("access", res.data)

    def test_links_require_auth(self):
        res = APIClient().get("/api/links/")
        self.assertEqual(res.status_code, 401)


class LinkTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user("alice", password="pass12345")
        self.client.force_authenticate(self.user)

    def create_link(self, **extra):
        payload = {"original_url": "https://example.com/page"}
        payload.update(extra)
        return self.client.post("/api/links/", payload, format="json")

    def test_create_with_generated_code(self):
        res = self.create_link()
        self.assertEqual(res.status_code, 201)
        self.assertEqual(len(res.data["short_code"]), 6)

    def test_create_with_custom_alias(self):
        res = self.create_link(short_code="my-alias")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["short_code"], "my-alias")

    def test_duplicate_alias_rejected(self):
        self.create_link(short_code="taken1")
        res = self.create_link(short_code="taken1")
        self.assertEqual(res.status_code, 400)

    def test_reserved_alias_rejected(self):
        res = self.create_link(short_code="admin")
        self.assertEqual(res.status_code, 400)

    def test_invalid_url_rejected(self):
        res = self.create_link(original_url="not-a-url")
        self.assertEqual(res.status_code, 400)

    def test_past_expiry_rejected(self):
        past = (timezone.now() - timedelta(days=1)).isoformat()
        res = self.create_link(expires_at=past)
        self.assertEqual(res.status_code, 400)

    def test_redirect_counts_click(self):
        self.create_link(short_code="abc123")
        res = self.client.get("/abc123/", HTTP_REFERER="https://google.com")
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res["Location"], "https://example.com/page")
        link = Link.objects.get(short_code="abc123")
        self.assertEqual(link.click_count, 1)
        self.assertEqual(link.clicks.count(), 1)

    def test_unknown_code_returns_404(self):
        self.assertEqual(self.client.get("/nope99/").status_code, 404)

    def test_expired_link_returns_410(self):
        Link.objects.create(
            owner=self.user, original_url="https://example.com",
            short_code="old123", expires_at=timezone.now() - timedelta(hours=1),
        )
        self.assertEqual(self.client.get("/old123/").status_code, 410)

    def test_deactivated_link_returns_410(self):
        res = self.create_link(short_code="live12")
        self.client.get("/live12/")  # warm the cache
        self.client.patch(f"/api/links/{res.data['id']}/", {"is_active": False}, format="json")
        self.assertEqual(self.client.get("/live12/").status_code, 410)

    def test_user_sees_only_own_links(self):
        self.create_link(short_code="mine12")
        other = User.objects.create_user("eve", password="pass12345")
        Link.objects.create(owner=other, original_url="https://x.com", short_code="theirs")
        res = self.client.get("/api/links/")
        codes = [item["short_code"] for item in res.data["results"]]
        self.assertEqual(codes, ["mine12"])

    def test_cannot_access_other_users_link(self):
        other = User.objects.create_user("eve", password="pass12345")
        link = Link.objects.create(owner=other, original_url="https://x.com", short_code="theirs")
        self.assertEqual(self.client.get(f"/api/links/{link.id}/").status_code, 404)

    def test_stats(self):
        res = self.create_link(short_code="stat12")
        self.client.get("/stat12/")
        self.client.get("/stat12/")
        stats = self.client.get(f"/api/links/{res.data['id']}/stats/")
        self.assertEqual(stats.status_code, 200)
        self.assertEqual(stats.data["total_clicks"], 2)

    def test_delete_link(self):
        res = self.create_link(short_code="del123")
        self.assertEqual(self.client.delete(f"/api/links/{res.data['id']}/").status_code, 204)
        self.assertEqual(self.client.get("/del123/").status_code, 404)
