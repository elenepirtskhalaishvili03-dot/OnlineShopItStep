from django.urls import path

from . import views

urlpatterns = [
    # Public shop pages
    path('', views.product_list, name='product_list'),
    path('product/<int:pk>/', views.product_detail, name='product_detail'),

    # Authentication
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Cart and orders
    path('cart/', views.cart_view, name='cart'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('orders/place/', views.place_order, name='place_order'),
    path('orders/history/', views.order_history, name='order_history'),

    # Custom admin dashboard
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('dashboard/products/add/', views.admin_add_product, name='admin_add_product'),
    path('dashboard/products/<int:pk>/edit/', views.admin_edit_product, name='admin_edit_product'),
    path('dashboard/products/<int:pk>/delete/', views.admin_delete_product, name='admin_delete_product'),
    path('dashboard/products/<int:pk>/activate/', views.admin_activate_product, name='admin_activate_product'),
    path('dashboard/orders/', views.admin_order_list, name='admin_order_list'),
]

