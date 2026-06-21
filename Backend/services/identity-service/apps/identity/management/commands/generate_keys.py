"""Generate RSA keys for JWT signing."""

from pathlib import Path

from django.core.management.base import BaseCommand
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend


class Command(BaseCommand):
    """Generate RSA key pair for JWT signing."""

    help = "Generate RSA private and public keys for JWT signing"

    def add_arguments(self, parser):
        parser.add_argument(
            "--keys-dir",
            type=str,
            default="/app/keys",
            help="Directory to store keys (default: /app/keys)",
        )

    def handle(self, *args, **options):
        keys_dir = Path(options["keys_dir"])
        keys_dir.mkdir(parents=True, exist_ok=True)

        private_key_path = keys_dir / "private.pem"
        public_key_path = keys_dir / "public.pem"

        # Check if keys already exist
        if private_key_path.exists() and public_key_path.exists():
            self.stdout.write(
                self.style.WARNING("Keys already exist. Skipping generation.")
            )
            return

        self.stdout.write("Generating RSA key pair...")

        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            Backend=default_backend(),
        )

        # Serialize private key
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

        # Write private key
        with open(private_key_path, "wb") as f:
            f.write(private_pem)
        self.stdout.write(
            self.style.SUCCESS(f"Private key saved to {private_key_path}")
        )

        # Get public key
        public_key = private_key.public_key()

        # Serialize public key
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

        # Write public key
        with open(public_key_path, "wb") as f:
            f.write(public_pem)
        self.stdout.write(self.style.SUCCESS(f"Public key saved to {public_key_path}"))

        self.stdout.write(self.style.SUCCESS("RSA key pair generated successfully!"))
