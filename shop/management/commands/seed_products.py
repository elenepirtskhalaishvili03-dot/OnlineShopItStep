from decimal import Decimal
from random import Random

from django.core.management.base import BaseCommand
from django.db.models.deletion import ProtectedError
from django.utils.text import slugify

from shop.models import CartItem, Order, OrderItem, Product


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
            "--hard-clear",
            action="store_true",
            help=(
                "Delete orders/order items/cart items and then delete all products. "
                "Use only when you want a full data reset."
            ),
        )
        parser.add_argument(
            "--seed",
            type=int,
            default=42,
            help="Random seed for deterministic output (default: 42).",
        )
        parser.add_argument(
            "--with-images",
            dest="with_images",
            action="store_true",
            default=True,
            help="Attach seed image URLs to products (default: enabled).",
        )
        parser.add_argument(
            "--without-images",
            dest="with_images",
            action="store_false",
            help="Do not attach image URLs.",
        )

    def handle(self, *args, **options):
        count = max(0, options["count"])
        clear = options["clear"]
        hard_clear = options["hard_clear"]
        with_images = options["with_images"]
        rng = Random(options["seed"])

        if hard_clear:
            deleted_order_items, _ = OrderItem.objects.all().delete()
            deleted_orders, _ = Order.objects.all().delete()
            deleted_cart_items, _ = CartItem.objects.all().delete()
            deleted_products, _ = Product.objects.all().delete()
            self.stdout.write(
                self.style.WARNING(
                    "Hard clear completed: "
                    f"order_items={deleted_order_items}, "
                    f"orders={deleted_orders}, "
                    f"cart_items={deleted_cart_items}, "
                    f"products={deleted_products}"
                )
            )
        elif clear:
            self._safe_clear_products()

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
                image_url=self._build_seed_image_url(name, model_number) if with_images else "",
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

    @staticmethod
    def _build_seed_image_url(name: str, model_number: int) -> str:
        """
        Uses Picsum seeded URLs so each product gets a stable photo-like placeholder.
        """
        slug = slugify(name) or f"product-{model_number}"
        return f"https://picsum.photos/seed/{slug}/1200/800"

    def _safe_clear_products(self) -> None:
        """
        Clear products while preserving order history.
        Products referenced by OrderItem are deactivated instead of deleted.
        """
        try:
            deleted_products, _ = Product.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Deleted existing products rows: {deleted_products}"))
            return
        except ProtectedError:
            pass

        protected_ids = set(OrderItem.objects.values_list("product_id", flat=True))
        deleted_products, _ = Product.objects.exclude(id__in=protected_ids).delete()
        deactivated = Product.objects.filter(id__in=protected_ids).update(is_active=False, stock=0)

        self.stdout.write(
            self.style.WARNING(
                "Safe clear completed with order history preserved: "
                f"deleted={deleted_products}, "
                f"deactivated_protected={deactivated}"
            )
        )
