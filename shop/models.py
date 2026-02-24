from django.db import models
from django.contrib.auth.models import User
from urllib.parse import quote


DEFAULT_PRODUCT_IMAGE_SVG = """
<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 640 400' role='img' aria-label='Product image placeholder'>
  <defs>
    <linearGradient id='bg' x1='0' y1='0' x2='1' y2='1'>
      <stop offset='0%' stop-color='#0f766e' stop-opacity='0.22'/>
      <stop offset='100%' stop-color='#ea580c' stop-opacity='0.22'/>
    </linearGradient>
  </defs>
  <rect width='640' height='400' fill='#f8fafc'/>
  <rect x='20' y='20' width='600' height='360' rx='22' fill='url(#bg)' stroke='#94a3b8' stroke-opacity='0.35'/>
  <rect x='170' y='95' width='300' height='210' rx='18' fill='#ffffff' stroke='#94a3b8' stroke-opacity='0.45'/>
  <circle cx='245' cy='165' r='28' fill='#0f766e' fill-opacity='0.22'/>
  <path d='M208 252l56-62 40 44 36-31 54 49H208z' fill='#0f766e' fill-opacity='0.3'/>
  <text x='320' y='338' fill='#334155' font-size='26' font-family='Arial, sans-serif' text-anchor='middle'>No Product Photo</text>
</svg>
""".strip()
DEFAULT_PRODUCT_IMAGE_DATA_URI = f"data:image/svg+xml;utf8,{quote(DEFAULT_PRODUCT_IMAGE_SVG)}"


class Product(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    image_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name

    @property
    def display_image_url(self) -> str:
        if self.image:
            return self.image.url
        if self.image_url:
            return self.image_url
        return DEFAULT_PRODUCT_IMAGE_DATA_URI


class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Cart of {self.user.username}"

    @property
    def total_amount(self):
        return sum(item.subtotal for item in self.items.all())


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ('cart', 'product')

    def __str__(self) -> str:
        return f"{self.product.name} x {self.quantity}"

    @property
    def subtotal(self):
        return self.product.price * self.quantity


class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self) -> str:
        return f"Order #{self.id} by {self.user.username}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    price_at_purchase = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self) -> str:
        return f"{self.product.name} x {self.quantity}"

