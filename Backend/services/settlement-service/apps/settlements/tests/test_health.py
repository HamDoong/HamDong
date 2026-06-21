from django.conf import settings
from django.test import TestCase


class HealthEndpointTests(TestCase):
    def test_health_endpoint(self):
        response = self.client.get("/health/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["service"], settings.SERVICE_NAME)
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["version"], settings.SERVICE_VERSION)
