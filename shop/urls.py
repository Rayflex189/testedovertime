from django.urls import path
from . import views

app_name = 'shop'

urlpatterns = [
    # Home
    path('', views.HomeView.as_view(), name='home'),
    
    # Products
    path('products/', views.ProductListView.as_view(), name='product_list'),
    path('products/<slug:slug>/', views.ProductDetailView.as_view(), name='product_detail'),
    
    # Cart
    path('cart/', views.cart_detail, name='cart_detail'),
    path('cart/clear/', views.clear_cart, name='clear_cart'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:product_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/update/<int:product_id>/', views.update_cart, name='update_cart'),
    
    # Checkout & Orders
    path('checkout/', views.checkout, name='checkout'),
    path('orders/', views.order_list, name='order_list'),
    path('orders/<int:order_id>/', views.order_detail, name='order_detail'),
    
    # Reviews
    path('products/<int:product_id>/review/', views.add_review, name='add_review'),
    
    # Wishlist
    path('wishlist/', views.wishlist_view, name='wishlist'),
    path('wishlist/toggle/<int:product_id>/', views.wishlist_toggle, name='wishlist_toggle'),
]