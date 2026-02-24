from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models.deletion import ProtectedError
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .forms import LoginForm, ProductForm, UserRegistrationForm
from .middleware import create_jwt_for_user
from .models import Cart, CartItem, Order, OrderItem, Product


def product_list(request):
    products = Product.objects.filter(is_active=True)
    return render(request, 'shop/product_list.html', {'products': products})


def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk, is_active=True)
    return render(request, 'shop/product_detail.html', {'product': product})


def register_view(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Registration successful. Please log in.")
            return redirect('login')
    else:
        form = UserRegistrationForm()
    return render(request, 'shop/register.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                token = create_jwt_for_user(user)
                response = redirect('product_list')
                # HttpOnly cookie so JS can't read it
                response.set_cookie(
                    'access_token',
                    token,
                    httponly=True,
                    samesite='Lax',
                    secure=False,  # set to True when using HTTPS in production
                )
                return response
            else:
                messages.error(request, "Invalid username or password.")
    else:
        form = LoginForm()
    return render(request, 'shop/login.html', {'form': form})


def logout_view(request):
    response = redirect('login')
    response.delete_cookie('access_token')
    return response


def _get_or_create_cart_for_user(user):
    cart, _ = Cart.objects.get_or_create(user=user)
    return cart


@login_required
def cart_view(request):
    cart = _get_or_create_cart_for_user(request.user)
    items = cart.items.select_related('product')
    return render(request, 'shop/cart.html', {'cart': cart, 'items': items})


@login_required
def add_to_cart(request, product_id):
    if request.method != 'POST':
        return HttpResponseForbidden("Only POST allowed")

    product = get_object_or_404(Product, pk=product_id, is_active=True)
    cart = _get_or_create_cart_for_user(request.user)
    item, created = CartItem.objects.get_or_create(cart=cart, product=product)
    if not created:
        item.quantity += 1
        item.save()
    messages.success(request, f"Added {product.name} to your cart.")
    return redirect('cart')


@login_required
def remove_from_cart(request, item_id):
    if request.method != 'POST':
        return HttpResponseForbidden("Only POST allowed")

    cart = _get_or_create_cart_for_user(request.user)
    item = get_object_or_404(CartItem, id=item_id, cart=cart)
    item.delete()
    messages.success(request, "Item removed from your cart.")
    return redirect('cart')


@login_required
def place_order(request):
    if request.method != 'POST':
        return HttpResponseForbidden("Only POST allowed")

    cart = _get_or_create_cart_for_user(request.user)
    items = list(cart.items.select_related('product'))
    if not items:
        messages.error(request, "Your cart is empty.")
        return redirect('cart')

    order = Order.objects.create(user=request.user, status='completed', total_amount=Decimal('0.00'))

    total = Decimal('0.00')
    for item in items:
        price = item.product.price
        OrderItem.objects.create(
            order=order,
            product=item.product,
            quantity=item.quantity,
            price_at_purchase=price,
        )
        total += price * item.quantity

        # Decrease product stock
        item.product.stock = max(0, item.product.stock - item.quantity)
        item.product.save()

    order.total_amount = total
    order.save()

    # Clear cart
    cart.items.all().delete()

    messages.success(request, f"Order #{order.id} placed successfully.")
    return redirect('order_history')


@login_required
def order_history(request):
    orders = request.user.orders.prefetch_related('items__product').order_by('-created_at')
    return render(request, 'shop/order_history.html', {'orders': orders})


def _is_admin(user):
    return user.is_staff


@user_passes_test(_is_admin)
def admin_dashboard(request):
    product_count = Product.objects.count()
    order_count = Order.objects.count()
    products = Product.objects.order_by('name')
    return render(
        request,
        'shop/admin_dashboard.html',
        {
            'product_count': product_count,
            'order_count': order_count,
            'products': products,
        },
    )


@user_passes_test(_is_admin)
def admin_add_product(request):
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Product added successfully.")
            return redirect('admin_dashboard')
    else:
        form = ProductForm()
    return render(
        request,
        'shop/admin_product_form.html',
        {
            'form': form,
            'is_edit': False,
            'product': None,
        },
    )


@user_passes_test(_is_admin)
def admin_edit_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, "Product updated successfully.")
            return redirect('admin_dashboard')
    else:
        form = ProductForm(instance=product)
    return render(
        request,
        'shop/admin_product_form.html',
        {
            'form': form,
            'is_edit': True,
            'product': product,
        },
    )


@user_passes_test(_is_admin)
def admin_delete_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        product_name = product.name
        try:
            product.delete()
            messages.success(request, f'Product "{product_name}" was deleted.')
        except ProtectedError:
            # Product is referenced by existing order items; keep history and just deactivate it
            product.is_active = False
            product.save(update_fields=['is_active'])
            messages.warning(
                request,
                f'Product "{product_name}" is used in existing orders, so it was deactivated instead of deleted.',
            )
        return redirect('admin_dashboard')

    return render(
        request,
        'shop/admin_product_confirm_delete.html',
        {'product': product},
    )


@user_passes_test(_is_admin)
def admin_order_list(request):
    orders = Order.objects.select_related('user').prefetch_related('items__product').order_by('-created_at')
    return render(request, 'shop/admin_orders.html', {'orders': orders})


@user_passes_test(_is_admin)
def admin_activate_product(request, pk):
    if request.method != 'POST':
        return HttpResponseForbidden("Only POST allowed")

    product = get_object_or_404(Product, pk=pk)
    product.is_active = True
    product.save(update_fields=['is_active'])
    messages.success(request, f'Product "{product.name}" was activated.')
    return redirect('admin_dashboard')

