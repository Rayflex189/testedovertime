from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Avg, Prefetch
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.generic import ListView, DetailView, TemplateView
from decimal import Decimal
from .models import Product, Category, Review, Cart as CartModel, CartItem, Order, OrderItem, ProductImage, Order # <-- Add OrderItem here
from .cart import Cart
# shop/views.py
from django.core.mail import send_mail
from django.conf import settings
from .models import Order
from .forms import ContactSupportForm
from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Layout, Field
from .forms import ReviewForm, CheckoutForm

# In views.py, add these views:
from django.contrib.admin.views.decorators import staff_member_required
from django.utils import timezone
import random
import string

import json
from django.http import JsonResponse


@login_required
def order_detail(request, order_id):
    """View individual order details"""
    order = get_object_or_404(Order, id=order_id, user=request.user)

    # Initialize variables
    order_items = []
    subtotal = order.subtotal or 0

    # Try to get order items - check multiple possibilities
    try:
        # First, try to import OrderItem to check if it exists
        from .models import OrderItem

        # Check all possible relationship names
        possible_relations = ['orderitem_set', 'order_items', 'items', 'orderitem']

        for rel_name in possible_relations:
            if hasattr(order, rel_name):
                items = getattr(order, rel_name).all()
                if items.exists():
                    order_items = items
                    print(f"Found order items via {rel_name}: {len(order_items)} items")
                    break

        # If still no items, try direct query
        if not order_items:
            order_items = OrderItem.objects.filter(order=order)
            print(f"Found order items via direct query: {len(order_items)} items")

    except ImportError:
        print("OrderItem model not found")
    except Exception as e:
        print(f"Error getting order items: {e}")

    # If no OrderItems found, try to get items from cart
    if not order_items and order.cart:
        try:
            cart_items = order.cart.items.all()
            # Create a list of dicts to mimic OrderItem structure
            for cart_item in cart_items:
                order_items.append({
                    'product': cart_item.product,
                    'quantity': cart_item.quantity,
                    'price': cart_item.product.price,
                    'total_price': cart_item.total_price,
                    'is_cart_item': True  # Flag to indicate this came from cart
                })
            print(f"Found {len(order_items)} items from cart")
        except Exception as e:
            print(f"Error getting cart items: {e}")

    # Calculate subtotal if we have items
    if order_items:
        if hasattr(order_items[0], 'total_price'):
            # Real OrderItem objects
            subtotal = sum(item.total_price for item in order_items)
        elif isinstance(order_items[0], dict) and 'total_price' in order_items[0]:
            # Dictionary items from cart
            subtotal = sum(item['total_price'] for item in order_items)

    # Calculate time left for PIN if it exists
    time_left = None
    if order.payment_pin and order.is_payment_pin_valid():
        time_left = order.payment_pin_expires_in

    return render(request, 'shop/order_detail.html', {
        'order': order,
        'order_items': order_items,
        'time_left': time_left,
        'subtotal': subtotal,
    })

@login_required
def verify_payment_pin(request, order_id):
    """Customer view to verify payment PIN"""
    order = get_object_or_404(Order, id=order_id, user=request.user)

    # Debug: Print current state
    print(f"\n=== CUSTOMER PIN VERIFICATION ===")
    print(f"Order: {order.order_number}")
    print(f"Payment Status: {order.payment_status}")
    print(f"Current PIN: {order.payment_pin}")
    print(f"PIN Generated: {order.payment_pin_generated_at}")
    print(f"PIN Expires: {order.payment_pin_expires_at}")
    print(f"Is PIN Valid: {order.is_payment_pin_valid()}")
    print(f"Payment Attempts: {order.payment_attempts}")
    print(f"Customer: {request.user.username}")
    print(f"===============================\n")

    # Check if payment is already confirmed
    if order.payment_status:
        messages.info(request, "Payment has already been confirmed for this order.")
        return redirect('shop:order_detail', order_id=order.id)  # Add 'shop:'

    # Check if PIN exists
    if not order.payment_pin:
        messages.error(request, "No payment PIN has been generated for this order. Please contact support.")
        return redirect('shop:order_detail', order_id=order.id)  # Add 'shop:'

    # Check if PIN is valid (not expired)
    if not order.is_payment_pin_valid():
        messages.error(request, "Payment PIN has expired. Please contact support for a new PIN.")
        return redirect('shop:order_detail', order_id=order.id)  # Add 'shop:'

    # Check for too many failed attempts
    if order.payment_attempts >= 5 and order.last_payment_attempt:
        time_since_last = timezone.now() - order.last_payment_attempt
        if time_since_last.total_seconds() < 300:  # 5 minutes
            messages.error(request, "Too many failed attempts. Please wait 5 minutes and try again, or contact support.")
            return redirect('shop:order_detail', order_id=order.id)  # Add 'shop:'

    if request.method == 'POST':
        pin = request.POST.get('payment_pin', '').strip()

        # Debug: Print verification attempt
        print(f"=== PIN VERIFICATION ATTEMPT ===")
        print(f"Entered PIN: {pin}")
        print(f"Expected PIN: {order.payment_pin}")
        print(f"Match: {pin == order.payment_pin}")
        print(f"==============================\n")

        # Verify the PIN
        is_valid, message = order.verify_payment_pin(pin, increment_attempts=True)

        if is_valid:
            # PIN is correct, confirm payment
            confirm_success, confirm_message = order.confirm_payment()

            if confirm_success:
                messages.success(request, f"Payment confirmed successfully for Order #{order.order_number}! Your order is now being processed.")

                # Debug: Print after confirmation
                print(f"=== AFTER PAYMENT CONFIRMATION ===")
                print(f"Payment Status: {order.payment_status}")
                print(f"PIN Cleared: {order.payment_pin == ''}")
                print(f"Status Updated: {order.status}")
                print(f"===============================\n")

                return redirect('shop:order_detail', order_id=order.id)  # Add 'shop:'
            else:
                messages.error(request, f"Error confirming payment: {confirm_message}")
        else:
            messages.error(request, message)

            # If too many failed attempts, redirect
            if order.payment_attempts >= 5:
                messages.error(request, "Too many failed attempts. Please contact support.")
                return redirect('shop:order_detail', order_id=order.id)  # Add 'shop:'

    return render(request, 'shop/verify_payment_pin.html', {
        'order': order,
        'is_pin_valid': order.is_payment_pin_valid(),
        'remaining_attempts': 5 - order.payment_attempts,
        'time_left': order.payment_pin_expires_in if order.is_payment_pin_valid() else "Expired",
    })



@staff_member_required
def support_payment_management(request, order_id):
    """Support view to manage payments for specific orders"""
    order = get_object_or_404(Order, id=order_id)

    # Debug: Print current state
    print(f"\n=== SUPPORT PAYMENT MANAGEMENT ===")
    print(f"Order: {order.order_number}")
    print(f"Payment Status: {order.payment_status}")
    print(f"Current PIN: {order.payment_pin}")
    print(f"PIN Generated: {order.payment_pin_generated_at}")
    print(f"PIN Expires: {order.payment_pin_expires_at}")
    print(f"Is PIN Valid: {order.is_payment_pin_valid()}")
    print(f"Payment Attempts: {order.payment_attempts}")
    print(f"===============================\n")

    if request.method == 'POST':
        action = request.POST.get('action')
        user = request.user  # The staff member performing the action

        if action == 'generate_pin':
            if order.payment_status:
                messages.error(request, f"Payment already confirmed for Order #{order.order_number}")
            else:
                try:
                    # Generate new payment PIN
                    pin = order.generate_payment_pin(user)

                    # Debug: Print after generation
                    print(f"=== AFTER PIN GENERATION ===")
                    print(f"Generated PIN: {pin}")
                    print(f"Order PIN: {order.payment_pin}")
                    print(f"PIN Generated at: {order.payment_pin_generated_at}")
                    print(f"PIN Expires at: {order.payment_pin_expires_at}")
                    print(f"===========================\n")

                    messages.success(request, f"Payment PIN generated for Order #{order.order_number}: {pin}")

                    # Store PIN in session for display (temporarily)
                    request.session['generated_pin'] = pin
                    request.session['generated_for_order'] = order.order_number

                except Exception as e:
                    messages.error(request, f"Error generating PIN: {str(e)}")

        elif action == 'confirm_payment':
            if order.payment_status:
                messages.warning(request, f"Payment already confirmed for Order #{order.order_number}")
            else:
                try:
                    # Manually confirm payment (for cases where PIN might not work)
                    success, message = order.confirm_payment(user)
                    if success:
                        messages.success(request, f"Payment manually confirmed for Order #{order.order_number}")
                    else:
                        messages.error(request, f"Error confirming payment: {message}")
                except Exception as e:
                    messages.error(request, f"Error confirming payment: {str(e)}")

        elif action == 'resend_pin':
            if order.payment_status:
                messages.error(request, f"Payment already confirmed for Order #{order.order_number}")
            else:
                try:
                    # Check if we can generate a new PIN
                    if not order.can_generate_new_pin():
                        messages.warning(request, f"Please wait before generating a new PIN. Current PIN is still active.")
                    else:
                        # Regenerate and resend PIN
                        pin = order.generate_payment_pin(user)
                        messages.success(request, f"New payment PIN generated for Order #{order.order_number}: {pin}")

                        # Store in session
                        request.session['generated_pin'] = pin
                        request.session['generated_for_order'] = order.order_number
                except Exception as e:
                    messages.error(request, f"Error generating PIN: {str(e)}")

        elif action == 'reset_pin':
            if order.payment_status:
                messages.error(request, f"Cannot reset PIN - payment already confirmed")
            else:
                order.reset_payment_pin()
                messages.success(request, f"Payment PIN reset for Order #{order.order_number}")

        elif action == 'clear_attempts':
            if order.payment_attempts > 0:
                order.payment_attempts = 0
                order.last_payment_attempt = None
                order.save(update_fields=['payment_attempts', 'last_payment_attempt', 'updated_at'])
                messages.success(request, f"Cleared payment attempts for Order #{order.order_number}")

        return redirect('shop:support_payment_management', order_id=order.id)  # Add 'shop:'

    # Check for previously generated PIN in session
    generated_pin = None
    if 'generated_pin' in request.session and 'generated_for_order' in request.session:
        if request.session['generated_for_order'] == order.order_number:
            generated_pin = request.session.get('generated_pin')
            # Clear it after showing once
            del request.session['generated_pin']
            del request.session['generated_for_order']

    return render(request, 'shop/support_payment_management.html', {
        'order': order,
        'is_pin_valid': order.is_payment_pin_valid(),
        'generated_pin': generated_pin,
        'current_time': timezone.now(),
        'can_generate_pin': order.can_generate_new_pin() if not order.payment_status else False,
    })

# AJAX view for checking PIN status (optional)
@login_required
def check_pin_status(request, order_id):
    """AJAX view to check PIN status without page reload"""
    order = get_object_or_404(Order, id=order_id, user=request.user)

    data = {
        'has_pin': bool(order.payment_pin),
        'is_valid': order.is_payment_pin_valid(),
        'payment_status': order.payment_status,
        'attempts_remaining': 5 - order.payment_attempts,
        'expires_in': order.payment_pin_expires_in if order.is_payment_pin_valid() else "Expired",
        'is_locked': order.payment_attempts >= 5,
    }

    return JsonResponse(data)

# API view for support to check order status
@staff_member_required
def api_order_payment_status(request, order_number):
    """API endpoint for support to check payment status"""
    order = get_object_or_404(Order, order_number=order_number)

    data = {
        'order_number': order.order_number,
        'payment_status': order.payment_status,
        'has_pin': bool(order.payment_pin),
        'pin_valid': order.is_payment_pin_valid(),
        'pin_generated': order.payment_pin_generated_at.isoformat() if order.payment_pin_generated_at else None,
        'pin_expires': order.payment_pin_expires_at.isoformat() if order.payment_pin_expires_at else None,
        'attempts': order.payment_attempts,
        'last_attempt': order.last_payment_attempt.isoformat() if order.last_payment_attempt else None,
        'status': order.status,
        'total': str(order.total),
        'user': order.user.username,
        'user_email': order.user.email,
    }

    return JsonResponse(data)

class HomeView(TemplateView):
    template_name = 'shop/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Prefetch primary images for products
        primary_images_prefetch = Prefetch(
            'images',
            queryset=ProductImage.objects.filter(is_primary=True),
            to_attr='primary_images'
        )

        # Get featured products with primary images
        context['featured_products'] = Product.objects.filter(
            is_featured=True,
            is_active=True
        ).prefetch_related(primary_images_prefetch)[:8]

        # Get new products with primary images
        context['new_products'] = Product.objects.filter(
            is_active=True
        ).prefetch_related(primary_images_prefetch).order_by('-created_at')[:8]

        # Get active categories
        context['categories'] = Category.objects.filter(is_active=True)

        return context

def clear_cart(request):
    cart = Cart(request)
    cart.clear()
    messages.success(request, "Cart cleared successfully.")
    return redirect('shop:cart_detail')


class ProductListView(ListView):
    model = Product
    template_name = 'shop/product_list.html'
    context_object_name = 'products'
    paginate_by = 12

    def get_queryset(self):
        queryset = Product.objects.filter(is_active=True)

        # Filter by category
        category_slug = self.request.GET.get('category')
        if category_slug:
            category = get_object_or_404(Category, slug=category_slug)
            queryset = queryset.filter(category=category)

        # Filter by search query
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query) |
                Q(description__icontains=query)
            )

        # Sorting
        sort_by = self.request.GET.get('sort', 'name')
        if sort_by == 'price_low':
            queryset = queryset.order_by('price')
        elif sort_by == 'price_high':
            queryset = queryset.order_by('-price')
        elif sort_by == 'newest':
            queryset = queryset.order_by('-created_at')
        else:
            queryset = queryset.order_by('name')

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.filter(is_active=True)
        context['selected_category'] = self.request.GET.get('category')
        context['search_query'] = self.request.GET.get('q', '')

        # Get sort label for display
        sort_by = self.request.GET.get('sort', 'name')
        sort_labels = {
            'name': 'Name (A-Z)',
            'price_low': 'Price: Low to High',
            'price_high': 'Price: High to Low',
            'newest': 'Newest First'
        }
        context['sort_label'] = sort_labels.get(sort_by, 'Name (A-Z)')

        return context

class ProductDetailView(DetailView):
    model = Product
    template_name = 'shop/product_detail.html'
    context_object_name = 'product'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.get_object()

        # Get related products
        context['related_products'] = Product.objects.filter(
            category=product.category,
            is_active=True
        ).exclude(id=product.id)[:4]

        # Get reviews
        context['reviews'] = product.reviews.filter(is_approved=True)
        context['review_form'] = ReviewForm()

        # Check if user has reviewed this product
        if self.request.user.is_authenticated:
            context['user_review'] = product.reviews.filter(user=self.request.user).first()

        # Get average rating
        avg_rating = product.reviews.filter(is_approved=True).aggregate(Avg('rating'))['rating__avg']
        context['avg_rating'] = avg_rating or 0

        return context

def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart = Cart(request)

    quantity = int(request.POST.get('quantity', 1))

    # Check stock availability
    if quantity > product.stock:
        messages.error(request, f"Only {product.stock} items available in stock.")
        return redirect('shop:product_detail', slug=product.slug)

    cart.add(product, quantity)
    messages.success(request, f"Added {quantity} x {product.name} to cart.")

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'cart_count': cart.get_total_items(),
            'message': f"Added {product.name} to cart"
        })

    return redirect('shop:cart_detail')

def remove_from_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart = Cart(request)
    cart.remove(product)
    messages.success(request, f"Removed {product.name} from cart.")

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'cart_count': cart.get_total_items(),
            'message': f"Removed {product.name} from cart"
        })

    return redirect('shop:cart_detail')

def update_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart = Cart(request)

    quantity = int(request.POST.get('quantity', 1))

    # Check stock availability
    if quantity > product.stock:
        messages.error(request, f"Only {product.stock} items available in stock.")
        return redirect('shop:cart_detail')

    cart.add(product, quantity, override_quantity=True)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'cart_count': cart.get_total_items(),
            'subtotal': str(cart.get_subtotal()),
            'message': f"Updated {product.name} quantity"
        })

    messages.success(request, f"Updated {product.name} quantity.")
    return redirect('shop:cart_detail')

def cart_detail(request):
    cart = Cart(request)
    cart_data = cart.get_cart_data()
    return render(request, 'shop/cart.html', cart_data)

@login_required
def checkout(request):
    cart = Cart(request)

    if not cart:
        messages.warning(request, "Your cart is empty.")
        return redirect('shop:product_list')

    # Check stock availability for all items
    for item in cart:
        product = item['product']
        if product.stock < item['quantity']:
            messages.error(request, f"Sorry, {product.name} only has {product.stock} items in stock.")
            return redirect('shop:cart_detail')

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            # Create order
            order = form.save(commit=False)
            order.user = request.user
            order.subtotal = cart.get_subtotal()
            order.shipping_cost = Decimal('10.00')  # Fixed shipping for now
            order.tax = order.subtotal * Decimal('0.08')  # 8% tax
            order.total = order.subtotal + order.shipping_cost + order.tax

            # Save order first
            order.save()

            # Create order items
            for item in cart:
                OrderItem.objects.create(
                    order=order,
                    product=item['product'],
                    quantity=item['quantity'],
                    price=item['price']
                )

                # Update product stock
                product = item['product']
                product.stock -= item['quantity']
                product.save()

            # Clear cart
            cart.clear()

            # Create cart model record for history
            cart_model = CartModel.objects.create(user=request.user)
            for item in cart:
                CartItem.objects.create(
                    cart=cart_model,
                    product=item['product'],
                    quantity=item['quantity']
                )

            messages.success(request, f"Order #{order.order_number} created successfully!")
            return redirect('shop:order_detail', order_id=order.id)
    else:
        # Pre-fill form with user's shipping info
        initial_data = {
            'shipping_address': request.user.shipping_address or request.user.address,
            'shipping_city': request.user.shipping_city or request.user.city,
            'shipping_state': request.user.shipping_state or request.user.state,
            'shipping_zip': request.user.shipping_zip or request.user.zip_code,
            'shipping_country': request.user.country,
        }
        form = CheckoutForm(initial=initial_data)

    cart_data = cart.get_cart_data()
    return render(request, 'shop/checkout.html', {
        'form': form,
        **cart_data
    })

@login_required
def order_list(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'shop/order_list.html', {'orders': orders})

@login_required
def add_review(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.product = product
            review.user = request.user

            # Check if user already reviewed
            existing_review = Review.objects.filter(product=product, user=request.user).first()
            if existing_review:
                messages.info(request, "You have already reviewed this product.")
                return redirect('shop:product_detail', slug=product.slug)

            review.save()
            messages.success(request, "Thank you for your review!")

    return redirect('shop:product_detail', slug=product.slug)

@login_required
def wishlist_toggle(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    profile = request.user.profile

    if product in profile.wishlist.all():
        profile.wishlist.remove(product)
        added = False
        message = "Removed from wishlist"
    else:
        profile.wishlist.add(product)
        added = True
        message = "Added to wishlist"

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'added': added,
            'message': message
        })

    messages.success(request, message)
    return redirect(request.META.get('HTTP_REFERER', 'shop:home'))

@login_required
def wishlist_view(request):
    profile = request.user.profile
    wishlist_items = profile.wishlist.all()
    return render(request, 'shop/wishlist.html', {'wishlist_items': wishlist_items})

@login_required
def cancel_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    if request.method == 'POST':
        if order.status == 'PENDING':
            order.status = 'CANCELLED'
            order.save()

            # Restore product stock
            for item in order.items.all():
                product = item.product
                product.stock += item.quantity
                product.save()

            messages.success(request, f"Order #{order.order_number} has been cancelled.")
        else:
            messages.error(request, "This order cannot be cancelled.")

        return redirect('shop:order_detail', order_id=order.id)

    # If not POST, show confirmation page or redirect
    return render(request, 'shop/cancel_order.html', {'order': order})

# shop/views.py

# Add this form class at the top of your views.py or within the view function
class ContactSupportForm(forms.Form):
    name = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Your full name'
        })
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Your email address'
        })
    )
    subject = forms.CharField(
        max_length=200,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Subject of your inquiry'
        })
    )
    order_number = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.HiddenInput()
    )
    message = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 6,
            'placeholder': 'Please describe your issue in detail...'
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'needs-validation'
        self.helper.form_id = 'supportForm'
        self.helper.add_input(Submit('submit', 'Send Message', css_class='btn-primary'))
  # Import the form

@login_required
def contact_support(request, order_number=None):
    """
    View for contacting customer support
    """
    # Get order if order_number is provided
    order = None
    if order_number:
        try:
            order = Order.objects.get(order_number=order_number, user=request.user)
        except Order.DoesNotExist:
            messages.warning(request, "Order not found or you don't have permission to view it.")
            order_number = None

    if request.method == 'POST':
        form = ContactSupportForm(request.POST, request.FILES)
        if form.is_valid():
            # Process the form data
            name = form.cleaned_data['name']
            email = form.cleaned_data['email']
            issue_type = form.cleaned_data['issue_type']
            order_num = form.cleaned_data.get('order_number', '')
            subject = form.cleaned_data['subject']
            message = form.cleaned_data['message']
            attach_file = request.FILES.get('attach_file')

            # Prepare email content
            email_subject = f"Support Request: {subject}"
            email_message = f"""
            New Support Request Received

            Customer Details:
            ----------------
            Name: {name}
            Email: {email}
            Issue Type: {dict(form.ISSUE_TYPES).get(issue_type, issue_type)}
            Order Number: {order_num or 'N/A'}

            Message:
            --------
            {message}

            Submitted at: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}
            """

            # Send email to support team
            try:
                send_mail(
                    email_subject,
                    email_message,
                    settings.DEFAULT_FROM_EMAIL,
                    [settings.SUPPORT_EMAIL],  # Add this to settings.py
                    fail_silently=False,
                )

                # Also send confirmation to customer
                confirmation_subject = "Support Request Received - Tested Over Time"
                confirmation_message = f"""
                Dear {name},

                Thank you for contacting Tested Over Time support.

                We have received your message regarding:
                "{subject}"

                Our support team will review your inquiry and get back to you within 24-48 hours.

                For your reference:
                - Issue Type: {dict(form.ISSUE_TYPES).get(issue_type, issue_type)}
                - Order Number: {order_num or 'N/A'}
                - Case ID: {hashlib.md5(f"{email}{timezone.now()}".encode()).hexdigest()[:8].upper()}

                If you need to add more information, please reply to this email.

                Best regards,
                Tested Over Time Support Team
                """

                send_mail(
                    confirmation_subject,
                    confirmation_message,
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                    fail_silently=True,
                )

                messages.success(
                    request,
                    'Thank you for contacting us! We have received your message and will get back to you soon. '
                    'A confirmation email has been sent to your email address.'
                )

                # Redirect based on context
                if order_num:
                    return redirect('shop:order_detail', order_id=order_num)
                return redirect('shop:order_list')

            except Exception as e:
                # Log the error but still show success to user
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to send support email: {str(e)}")

                messages.success(
                    request,
                    'Thank you for contacting us! Your message has been received. '
                    'We will get back to you soon.'
                )
                return redirect('shop:order_list')
    else:
        # Pre-fill form with user and order data
        initial_data = {}

        # Add user info if authenticated
        if request.user.is_authenticated:
            user = request.user
            initial_data['name'] = f"{user.first_name} {user.last_name}".strip()
            if not initial_data['name']:
                initial_data['name'] = user.username
            initial_data['email'] = user.email

        # Add order info if provided
        if order_number:
            initial_data['order_number'] = order_number
            if order:
                initial_data['subject'] = f"Question about order {order_number}"
                initial_data['issue_type'] = 'order'

        form = ContactSupportForm(initial=initial_data)

    return render(request, 'shop/contact_support.html', {
        'form': form,
        'order_number': order_number,
        'order': order,
    })

@login_required
def confirm_payment(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    if request.method == 'POST':
        payment_confirmation = request.POST.get('payment_confirmation', '').strip()

        if payment_confirmation:
            # Update order with payment confirmation
            order.payment_confirmation = payment_confirmation
            order.payment_status = True  # Mark as paid
            order.status = 'PROCESSING'  # Move to processing
            order.save()

            messages.success(request, f"Payment confirmed for order #{order.order_number}! Your order is now being processed.")
            return redirect('shop:order_detail', order_id=order.id)
        else:
            messages.error(request, "Please provide a payment confirmation number.")

    return redirect('shop:order_detail', order_id=order.id)
