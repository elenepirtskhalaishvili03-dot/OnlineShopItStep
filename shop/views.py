from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

from .forms import LoginForm, ProductForm, UserRegistrationForm
from .middleware import create_jwt_for_user
from .models import Cart, CartItem, Order, OrderItem, Product


def product_list(request):
    products_qs = Product.objects.filter(is_active=True)

    search_query = request.GET.get('q', '').strip()
    min_price_raw = request.GET.get('min_price', '').strip()
    max_price_raw = request.GET.get('max_price', '').strip()
    sort = request.GET.get('sort', 'newest').strip()
    in_stock_only = request.GET.get('in_stock') in {'1', 'true', 'on'}

    if search_query:
        products_qs = products_qs.filter(
            Q(name__icontains=search_query) | Q(description__icontains=search_query)
        )

    try:
        if min_price_raw:
            min_price = Decimal(min_price_raw)
            if min_price >= 0:
                products_qs = products_qs.filter(price__gte=min_price)
    except InvalidOperation:
        min_price_raw = ''

    try:
        if max_price_raw:
            max_price = Decimal(max_price_raw)
            if max_price >= 0:
                products_qs = products_qs.filter(price__lte=max_price)
    except InvalidOperation:
        max_price_raw = ''

    if in_stock_only:
        products_qs = products_qs.filter(stock__gt=0)

    sort_map = {
        'newest': '-created_at',
        'price_asc': 'price',
        'price_desc': '-price',
        'name_asc': 'name',
    }
    if sort not in sort_map:
        sort = 'newest'
    products_qs = products_qs.order_by(sort_map[sort], 'id')

    paginator = Paginator(products_qs, 9)
    page_obj = paginator.get_page(request.GET.get('page'))
    page_numbers = paginator.get_elided_page_range(number=page_obj.number, on_each_side=1, on_ends=1)

    query_params = request.GET.copy()
    query_params.pop('page', None)
    preserved_query = query_params.urlencode()

    return render(
        request,
        'shop/product_list.html',
        {
            'products': page_obj.object_list,
            'page_obj': page_obj,
            'page_numbers': page_numbers,
            'preserved_query': preserved_query,
            'search_query': search_query,
            'min_price': min_price_raw,
            'max_price': max_price_raw,
            'sort': sort,
            'in_stock_only': in_stock_only,
        },
    )


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
                    secure=settings.JWT_COOKIE_SECURE,
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


def _redirect_to_next(request, fallback_url_name='cart'):
    next_url = request.POST.get('next', '').strip()
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return HttpResponseRedirect(next_url)
    return redirect(fallback_url_name)


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
    if product.stock == 0:
        messages.error(request, f'"{product.name}" is out of stock.')
        return _redirect_to_next(request)

    quantity_raw = request.POST.get('quantity', '1').strip()
    try:
        quantity = int(quantity_raw)
    except ValueError:
        quantity = 1
    quantity = max(1, quantity)

    cart = _get_or_create_cart_for_user(request.user)
    item, created = CartItem.objects.get_or_create(cart=cart, product=product)
    old_quantity = item.quantity if not created else 0
    item.quantity = min(product.stock, old_quantity + quantity)
    item.save(update_fields=['quantity'])

    if item.quantity == old_quantity and not created:
        messages.warning(request, f'You already have the maximum available stock of "{product.name}" in your cart.')
    elif item.quantity < old_quantity + quantity:
        messages.warning(request, f'Only {product.stock} item(s) of "{product.name}" are available.')
    else:
        messages.success(request, f"Added {quantity} x {product.name} to your cart.")

    return _redirect_to_next(request)


@login_required
def update_cart_item_quantity(request, item_id):
    if request.method != 'POST':
        return HttpResponseForbidden("Only POST allowed")

    cart = _get_or_create_cart_for_user(request.user)
    item = get_object_or_404(CartItem, id=item_id, cart=cart)
    action = request.POST.get('action', '').strip()

    if action == 'increment':
        if item.quantity >= item.product.stock:
            messages.warning(request, f'Only {item.product.stock} item(s) of "{item.product.name}" are available.')
        else:
            item.quantity += 1
            item.save(update_fields=['quantity'])
    elif action == 'decrement':
        if item.quantity > 1:
            item.quantity -= 1
            item.save(update_fields=['quantity'])
    else:
        messages.error(request, "Invalid quantity update action.")

    return _redirect_to_next(request)


@login_required
def remove_from_cart(request, item_id):
    if request.method != 'POST':
        return HttpResponseForbidden("Only POST allowed")

    cart = _get_or_create_cart_for_user(request.user)
    item = get_object_or_404(CartItem, id=item_id, cart=cart)
    item_name = item.product.name
    item.delete()
    messages.success(request, f'"{item_name}" removed from your cart.')
    return _redirect_to_next(request)


@login_required
def place_order(request):
    if request.method != 'POST':
        return HttpResponseForbidden("Only POST allowed")

    cart = _get_or_create_cart_for_user(request.user)
    items = list(cart.items.select_related('product'))
    if not items:
        messages.error(request, "Your cart is empty.")
        return redirect('cart')

    unavailable_items = [item for item in items if item.quantity > item.product.stock]
    if unavailable_items:
        messages.error(
            request,
            "Some quantities in your cart exceed current stock. Please review your cart before checkout.",
        )
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
        item.product.save(update_fields=['stock'])

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
        form = ProductForm(request.POST, request.FILES)
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
        form = ProductForm(request.POST, request.FILES, instance=product)
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

