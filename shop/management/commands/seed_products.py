from decimal import Decimal
from random import Random

from django.core.management.base import BaseCommand

from shop.models import Product


ADJECTIVES = [
    "Smart",
    "Ultra",
    "Classic",
    "Modern",
    "Pro",
    "Compact",
    "Premium",
    "Eco",
    "Portable",
    "Dynamic",
]

PRODUCT_TYPES = [
    "Wireless Mouse",
    "Mechanical Keyboard",
    "Gaming Headset",
    "USB-C Hub",
    "Portable SSD",
    "4K Monitor",
    "Webcam",
    "Bluetooth Speaker",
    "Power Bank",
    "Smartwatch",
    "Laptop Stand",
    "Desk Lamp",
    "Phone Holder",
    "Noise Cancelling Earbuds",
    "Action Camera",
]

HIGHLIGHTS = [
    "built for daily productivity",
    "optimized for remote work",
    "perfect for gaming setups",
    "designed with premium materials",
    "engineered for long battery life",
    "made for compact desks",
    "great for travel and office use",
    "focused on comfort and reliability",
]


class Command(BaseCommand):
    help = "Seed sample products."

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=50,
            help="Number of products to create (default: 50).",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete existing products before seeding.",
        )
        parser.add_argument(
            "--seed",
            type=int,
            default=42,
            help="Random seed for deterministic output (default: 42).",
        )

    def handle(self, *args, **options):
        count = max(0, options["count"])
        clear = options["clear"]
        rng = Random(options["seed"])

        if clear:
            deleted, _ = Product.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Deleted existing products rows: {deleted}"))

        existing_names = set(Product.objects.values_list("name", flat=True))
        created = 0
        attempts = 0
        max_attempts = max(200, count * 25)

        while created < count and attempts < max_attempts:
            attempts += 1
            adjective = rng.choice(ADJECTIVES)
            product_type = rng.choice(PRODUCT_TYPES)
            model_number = rng.randint(100, 999)
            name = f"{adjective} {product_type} {model_number}"

            if name in existing_names:
                continue

            highlight = rng.choice(HIGHLIGHTS)
            warranty_years = rng.choice([1, 2, 3])
            description = (
                f"{name} is {highlight}. "
                f"It includes modern connectivity and a {warranty_years}-year warranty."
            )

            price = (Decimal(rng.randint(1299, 25999)) / Decimal("100")).quantize(Decimal("0.01"))
            stock = rng.randint(5, 120)

            Product.objects.create(
                name=name,
                description=description,
                price=price,
                stock=stock,
                image_url="",
                is_active=True,
            )

            existing_names.add(name)
            created += 1

        if created < count:
            self.stdout.write(
                self.style.WARNING(
                    f"Created {created} products out of requested {count}. "
                    "Run again with a different --seed for more."
                )
            )
        else:
            self.stdout.write(self.style.SUCCESS(f"Successfully created {created} products."))
