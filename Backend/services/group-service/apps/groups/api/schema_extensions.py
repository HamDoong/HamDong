"""drf-spectacular extensions for group-service authentication."""

from drf_spectacular.extensions import OpenApiAuthenticationExtension


class JWTAuthenticationScheme(OpenApiAuthenticationExtension):
    """Expose the custom Bearer JWT authentication scheme in Swagger."""

    target_class = "apps.groups.infrastructure.jwt_authentication.JWTAuthentication"
    name = "BearerAuth"

    def get_security_definition(self, auto_schema):
        return {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }