from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Avg
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.generic import ListView, DetailView, TemplateView
from .models import Product, Category, Review, Cart as CartModel, CartItem, Order
from .cart import Cart
from .forms import ReviewForm, CheckoutForm

class HomeView(TemplateView):
    template_name = 'shop/home.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['featured_products'] = Product.objects.filter(is_featured=True, is_active=True)[:8]
        context['new_products'] = Product.objects.filter(is_active=True).order_by('-created_at')[:8]
        context['categories'] = Category.objects.filter(is_active=True)
        return context

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
                Q(description__icontains=query) |
                Q(category__name__icontains=query)
            )
        
        # Filter by price range
        min_price = self.request.GET.get('min_price')
        max_price = self.request.GET.get('max_price')
        if min_price:
            queryset = queryset.filter(price__gte=min_price)
        if max_price:
            queryset = queryset.filter(price__lte=max_price)
        
        # Sorting
        sort_by = self.request.GET.get('sort', 'name')
        if sort_by == 'price_low':
            queryset = queryset.order_by('price')
        elif sort_by == 'price_high':
            queryset = queryset.order_by('-price')
        elif sort_by == 'newest':
            queryset = queryset.order_by('-created_at')
        elif sort_by == 'popular':
            queryset = queryset.annotate(avg_rating=Avg('reviews__rating')).order_by('-avg_rating')
        else:
            queryset = queryset.order_by('name')
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.filter(is_active=True)
        context['selected_category'] = self.request.GET.get('category')
        context['search_query'] = self.request.GET.get('q', '')
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
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'shop/order_detail.html', {'order': order})

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