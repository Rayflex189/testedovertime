from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
import uuid
import random
import string
from datetime import timedelta


User = get_user_model()

class Category(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='categories/', blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']

    def __str__(self):
        return self.name

class Product(models.Model):
    SIZE_CHOICES = [
        ('XS', 'Extra Small'),
        ('S', 'Small'),
        ('M', 'Medium'),
        ('L', 'Large'),
        ('XL', 'Extra Large'),
        ('XXL', '2X Large'),
    ]

    COLOR_CHOICES = [
        ('RED', 'Red'),
        ('BLUE', 'Blue'),
        ('GREEN', 'Green'),
        ('BLACK', 'Black'),
        ('WHITE', 'White'),
        ('GRAY', 'Gray'),
        ('NAVY', 'Navy'),
        ('BROWN', 'Brown'),
    ]

    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    size = models.CharField(max_length=10, choices=SIZE_CHOICES, blank=True)
    color = models.CharField(max_length=20, choices=COLOR_CHOICES, blank=True)
    sku = models.CharField(max_length=100, unique=True)
    stock = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def current_price(self):
        return self.discount_price if self.discount_price else self.price

    @property
    def discount_percentage(self):
        if self.discount_price and self.price > 0:
            return int(((self.price - self.discount_price) / self.price) * 100)
        return 0

    @property
    def in_stock(self):
        return self.stock > 0

    def __str__(self):
        return self.name

class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/')
    is_primary = models.BooleanField(default=False)
    alt_text = models.CharField(max_length=200, blank=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f"Image for {self.product.name}"

class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    title = models.CharField(max_length=200)
    comment = models.TextField()
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['product', 'user']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username}'s review of {self.product.name}"

class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='carts', null=True, blank=True)
    session_key = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())

    @property
    def subtotal(self):
        return sum(item.total_price for item in self.items.all())

    def __str__(self):
        if self.user:
            return f"Cart for {self.user.username}"
        return f"Cart (Session: {self.session_key})"

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    @property
    def total_price(self):
        return self.product.current_price * self.quantity

    class Meta:
        unique_together = ['cart', 'product']

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"


class Order(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('SHIPPED', 'Shipped'),
        ('DELIVERED', 'Delivered'),
        ('CANCELLED', 'Cancelled'),
        ('REFUNDED', 'Refunded'),
    ]

    PAYMENT_CHOICES = [
        ('ZELLE', 'Zelle'),
        ('PAYPAL', 'PayPal'),
        ('CASHAPP', 'Cash App'),
    ]

    order_number = models.CharField(max_length=20, unique=True, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    cart = models.ForeignKey('Cart', on_delete=models.SET_NULL, null=True, blank=True)

    # Shipping information
    shipping_address = models.TextField()
    shipping_city = models.CharField(max_length=100)
    shipping_state = models.CharField(max_length=100)
    shipping_zip = models.CharField(max_length=20)
    shipping_country = models.CharField(max_length=100)

    # Billing information
    billing_address = models.TextField(blank=True)
    billing_city = models.CharField(max_length=100, blank=True)
    billing_state = models.CharField(max_length=100, blank=True)
    billing_zip = models.CharField(max_length=20, blank=True)
    billing_country = models.CharField(max_length=100, blank=True)

    # Order details
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2)

    # Status and payment
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES)
    payment_status = models.BooleanField(default=False)
    payment_id = models.CharField(max_length=100, blank=True)

    # Payment PIN verification system
    payment_pin = models.CharField(max_length=6, blank=True, editable=False, help_text="6-digit verification PIN generated by support")
    payment_pin_generated_at = models.DateTimeField(null=True, blank=True, help_text="When the PIN was generated")
    payment_pin_expires_at = models.DateTimeField(null=True, blank=True, help_text="When the PIN expires (24 hours after generation)")
    payment_confirmed_at = models.DateTimeField(null=True, blank=True, help_text="When payment was confirmed via PIN")
    payment_verified_by = models.ForeignKey(User, on_delete=models.SET_NULL,
                                           null=True, blank=True,
                                           related_name='verified_payments',
                                           help_text="Support staff who verified the payment")
    payment_attempts = models.IntegerField(default=0, help_text="Number of failed PIN attempts")
    last_payment_attempt = models.DateTimeField(null=True, blank=True, help_text="Last failed PIN attempt")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['payment_pin']),
            models.Index(fields=['payment_status', 'status']),
            models.Index(fields=['user', 'created_at']),
        ]

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = f"ORD-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"

        if not self.billing_address:
            self.billing_address = self.shipping_address
            self.billing_city = self.shipping_city
            self.billing_state = self.shipping_state
            self.billing_zip = self.shipping_zip
            self.billing_country = self.shipping_country

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Order #{self.order_number} - {self.user.username}"

    # Payment PIN Methods
    def generate_payment_pin(self, user=None):
        """Generate a secure 6-digit payment verification PIN"""
        from django.utils import timezone

        # Generate random 6-digit PIN (numbers only)
        pin = ''.join(random.choices(string.digits, k=6))

        # Ensure PIN is unique (very low probability of collision, but let's be safe)
        while Order.objects.filter(payment_pin=pin, payment_pin_expires_at__gt=timezone.now()).exists():
            pin = ''.join(random.choices(string.digits, k=6))

        self.payment_pin = pin
        self.payment_pin_generated_at = timezone.now()
        self.payment_pin_expires_at = timezone.now() + timedelta(hours=24)  # PIN valid for 24 hours
        self.payment_attempts = 0  # Reset failed attempts
        self.last_payment_attempt = None

        if user:
            self.payment_verified_by = user

        self.save(update_fields=[
            'payment_pin',
            'payment_pin_generated_at',
            'payment_pin_expires_at',
            'payment_attempts',
            'last_payment_attempt',
            'payment_verified_by',
            'updated_at'
        ])

        return pin

    def verify_payment_pin(self, pin, increment_attempts=True):
        """
        Verify if the provided PIN is correct and not expired.
        Returns (success, message) tuple.
        """
        from django.utils import timezone

        # Check if payment already confirmed
        if self.payment_status:
            return False, "Payment has already been confirmed for this order."

        # Check if there's a PIN generated
        if not self.payment_pin or not self.payment_pin_generated_at:
            return False, "No payment PIN generated for this order. Please contact support."

        # Check if PIN is expired
        if timezone.now() > self.payment_pin_expires_at:
            return False, "Payment PIN has expired. Please contact support for a new PIN."

        # Check for too many failed attempts (rate limiting)
        if self.payment_attempts >= 5 and self.last_payment_attempt:
            time_since_last_attempt = timezone.now() - self.last_payment_attempt
            if time_since_last_attempt.total_seconds() < 300:  # 5 minutes
                return False, "Too many failed attempts. Please wait 5 minutes and try again."

        # Verify the PIN
        if self.payment_pin != pin.strip():
            if increment_attempts:
                self.payment_attempts += 1
                self.last_payment_attempt = timezone.now()
                self.save(update_fields=['payment_attempts', 'last_payment_attempt', 'updated_at'])

            attempts_left = 5 - self.payment_attempts
            if attempts_left > 0:
                return False, f"Invalid payment PIN. {attempts_left} attempt(s) remaining."
            else:
                return False, "Invalid payment PIN. Too many failed attempts. Please contact support."

        # PIN is correct
        return True, "Payment PIN verified successfully."

    def confirm_payment_with_pin(self, pin, user=None):
        """Verify PIN and confirm payment if correct"""
        success, message = self.verify_payment_pin(pin)

        if success:
            return self.confirm_payment(user)

        return False, message

    def confirm_payment(self, user=None):
        """Confirm payment and update order status"""
        from django.utils import timezone

        self.payment_status = True
        self.payment_confirmed_at = timezone.now()
        self.status = 'PROCESSING'
        self.payment_verified_by = user

        # Clear PIN for security
        self.payment_pin = ''
        self.payment_attempts = 0
        self.last_payment_attempt = None

        self.save(update_fields=[
            'payment_status',
            'payment_confirmed_at',
            'status',
            'payment_verified_by',
            'payment_pin',
            'payment_attempts',
            'last_payment_attempt',
            'updated_at'
        ])

        return True, "Payment confirmed successfully. Order is now being processed."

    def is_payment_pin_valid(self):
        """Check if payment PIN is still valid (not expired and exists)"""
        from django.utils import timezone

        if not self.payment_pin or not self.payment_pin_expires_at:
            return False

        return timezone.now() <= self.payment_pin_expires_at

    def get_payment_pin_status(self):
        """Get human-readable PIN status"""
        if not self.payment_pin:
            return "No PIN generated"

        if not self.is_payment_pin_valid():
            return "Expired"

        return "Active"

    def reset_payment_pin(self):
        """Reset/clear the payment PIN"""
        self.payment_pin = ''
        self.payment_pin_generated_at = None
        self.payment_pin_expires_at = None
        self.payment_attempts = 0
        self.last_payment_attempt = None
        self.save(update_fields=[
            'payment_pin',
            'payment_pin_generated_at',
            'payment_pin_expires_at',
            'payment_attempts',
            'last_payment_attempt',
            'updated_at'
        ])

    def can_generate_new_pin(self):
        """Check if a new PIN can be generated (cooldown period)"""
        from django.utils import timezone

        if not self.payment_pin_generated_at:
            return True

        # Allow new PIN generation if current PIN is expired
        if not self.is_payment_pin_valid():
            return True

        # Otherwise, check cooldown (at least 1 hour between PIN generations)
        time_since_last = timezone.now() - self.payment_pin_generated_at
        return time_since_last.total_seconds() >= 3600  # 1 hour

    @property
    def payment_pin_expires_in(self):
        """Get time until PIN expires (in hours/minutes)"""
        from django.utils import timezone

        if not self.payment_pin_expires_at or not self.is_payment_pin_valid():
            return "Expired"

        time_left = self.payment_pin_expires_at - timezone.now()

        if time_left.total_seconds() <= 0:
            return "Expired"
        elif time_left.total_seconds() < 3600:  # Less than 1 hour
            minutes = int(time_left.total_seconds() / 60)
            return f"{minutes} minutes"
        else:
            hours = int(time_left.total_seconds() / 3600)
            return f"{hours} hours"

    # Helper properties for templates
    @property
    def is_paid(self):
        return self.payment_status

    @property
    def needs_payment(self):
        return not self.payment_status and self.status != 'CANCELLED'

    @property
    def payment_verified_by_name(self):
        if self.payment_verified_by:
            return self.payment_verified_by.get_full_name() or self.payment_verified_by.username
        return "System"

# shop/models.py - Update OrderItem model
class OrderItem(models.Model):
    """Items within an order"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('Product', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Order Item'
        verbose_name_plural = 'Order Items'

    @property
    def total_price(self):
        """Calculate total price for this item"""
        if self.price is None or self.quantity is None:
            return 0
        return self.price * self.quantity

    def save(self, *args, **kwargs):
        # Auto-set price from product if not set
        if self.price is None and self.product:
            self.price = self.product.price
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.quantity} x {self.product.name} (Order: {self.order.order_number})"

class Coupon(models.Model):
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    discount_type = models.CharField(max_length=10, choices=[
        ('PERCENT', 'Percentage'),
        ('FIXED', 'Fixed Amount'),
    ])
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    min_order_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    max_discount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    usage_limit = models.IntegerField(null=True, blank=True)
    used_count = models.IntegerField(default=0)

    def is_valid(self, order_amount=0):
        now = timezone.now()
        if not self.is_active:
            return False
        if not (self.valid_from <= now <= self.valid_to):
            return False
        if self.min_order_amount and order_amount < self.min_order_amount:
            return False
        if self.usage_limit and self.used_count >= self.usage_limit:
            return False
        return True

    def calculate_discount(self, order_amount):
        if not self.is_valid(order_amount):
            return 0

        if self.discount_type == 'PERCENT':
            discount = order_amount * (self.discount_value / 100)
            if self.max_discount:
                discount = min(discount, self.max_discount)
        else:
            discount = min(self.discount_value, order_amount)

        return discount

    def __str__(self):
        return self.code
