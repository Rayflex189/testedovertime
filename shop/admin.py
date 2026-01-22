# shop/admin.py
from django.contrib import admin
from django.utils.html import format_html, mark_safe
from django.urls import reverse
from django.utils import timezone
from django import forms
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.http import HttpResponseRedirect
from .models import (
    Category, Product, ProductImage, Review,
    Cart, CartItem, Order, OrderItem, Coupon
)

# ==================== PRODUCT ADMIN ====================
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ['image', 'caption', 'is_primary']
    verbose_name = "Product Image"
    verbose_name_plural = "Product Images"

class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'stock', 'is_active', 'is_featured', 'created_at']
    list_filter = ['category', 'is_active', 'is_featured', 'created_at']
    search_fields = ['name', 'description', 'sku', 'category__name']
    list_editable = ['price', 'stock', 'is_active', 'is_featured']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductImageInline]
    # Remove view_count from readonly_fields since it doesn't exist on your model
    readonly_fields = ['created_at', 'updated_at']  # Removed 'view_count'
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'category', 'description', 'sku')
        }),
        ('Pricing & Inventory', {
            'fields': ('price', 'stock', 'is_active', 'is_featured')
        }),
        ('Additional Information', {
            # Remove 'view_count' from fields
            'fields': ('created_at', 'updated_at')
        }),
    )
    ordering = ['-created_at']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('category')

# ==================== ORDER ITEM INLINE ====================
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    fields = ['product', 'quantity', 'price', 'get_total_price']
    readonly_fields = ['get_total_price']
    can_delete = False
    extra = 0
    verbose_name = "Order Item"
    verbose_name_plural = "Order Items"

    def get_total_price(self, obj):
        """Safe method to get total price"""
        try:
            if hasattr(obj, 'total_price'):
                total = obj.total_price
                if total is not None:
                    return f"${float(total):.2f}"
        except (AttributeError, TypeError, ValueError):
            pass
        return "$0.00"
    get_total_price.short_description = "Total"

# ==================== ORDER ADMIN FORM ====================
class OrderAdminForm(forms.ModelForm):
    class Meta:
        model = Order
        exclude = []
        widgets = {
            'shipping_address': forms.Textarea(attrs={'rows': 3}),
            'billing_address': forms.Textarea(attrs={'rows': 3}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

# ==================== ORDER ADMIN ====================
class OrderAdmin(admin.ModelAdmin):
    form = OrderAdminForm
    list_display = ['order_number', 'user', 'total_display', 'status_display',
                    'payment_status_display', 'payment_pin_badge', 'payment_actions_quick',
                    'created_at_formatted']
    list_filter = ['status', 'payment_status', 'payment_method', 'created_at']
    search_fields = ['order_number', 'user__username', 'user__email',
                     'user__first_name', 'user__last_name']
    readonly_fields = ['order_number', 'created_at', 'updated_at',
                      'payment_pin_display', 'payment_pin_status',
                      'payment_pin_generated_at', 'payment_pin_expires_at',
                      'payment_pin_expires_in', 'payment_confirmed_at',
                      'payment_verified_by', 'payment_attempts',
                      'last_payment_attempt', 'payment_actions']
    inlines = [OrderItemInline]
    actions = ['generate_payment_pins', 'reset_payment_pins', 'confirm_payments',
               'mark_as_processing', 'mark_as_shipped', 'mark_as_delivered',
               'mark_as_cancelled']

    fieldsets = (
        ('Order Information', {
            'fields': ('order_number', 'user', 'cart', 'status', 'payment_status')
        }),
        ('Payment Information', {
            'fields': ('payment_pin_display', 'payment_pin_status', 'payment_pin_expires_in',
                      'payment_pin_generated_at', 'payment_pin_expires_at',
                      'payment_confirmed_at', 'payment_verified_by',
                      'payment_attempts', 'last_payment_attempt',
                      'payment_method', 'payment_id', 'payment_actions')
        }),
        ('Shipping Information', {
            'fields': ('shipping_address', 'shipping_city', 'shipping_state',
                      'shipping_zip', 'shipping_country')
        }),
        ('Billing Information', {
            'fields': ('billing_address', 'billing_city', 'billing_state',
                      'billing_zip', 'billing_country')
        }),
        ('Financial Details', {
            'fields': ('subtotal', 'tax', 'shipping_cost', 'total')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'shipped_at', 'delivered_at')
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
    )

    # ============ LIST DISPLAY METHODS ============
    def total_display(self, obj):
        try:
            return format_html('<strong>${:.2f}</strong>'.format(float(obj.total)))
        except (TypeError, ValueError):
            return format_html('<strong>$0.00</strong>')
    total_display.short_description = 'Total'
    total_display.admin_order_field = 'total'

    def status_display(self, obj):
        status_colors = {
            'PENDING': 'secondary',
            'PROCESSING': 'warning',
            'SHIPPED': 'info',
            'DELIVERED': 'success',
            'CANCELLED': 'danger',
            'REFUNDED': 'dark',
        }
        color = status_colors.get(obj.status, 'secondary')
        return format_html(
            '<span style="background-color: var(--{}-color, #6c757d); color: {}; padding: 4px 8px; border-radius: 12px; font-size: 12px; font-weight: 600;">{}</span>'.format(
                color, 
                'white' if color in ['success', 'danger', 'secondary', 'dark'] else 'black',
                obj.get_status_display()
            )
        )
    status_display.short_description = 'Status'
    status_display.admin_order_field = 'status'

    def payment_status_display(self, obj):
        if obj.payment_status:
            return format_html(
                '<span style="background-color: #198754; color: white; padding: 4px 8px; border-radius: 12px; font-size: 12px; font-weight: 600;">'
                '<i class="fas fa-check-circle" style="margin-right: 4px;"></i>Paid'
                '</span>'
            )
        return format_html(
            '<span style="background-color: #ffc107; color: black; padding: 4px 8px; border-radius: 12px; font-size: 12px; font-weight: 600;">'
            '<i class="fas fa-clock" style="margin-right: 4px;"></i>Pending'
            '</span>'
        )
    payment_status_display.short_description = 'Payment'

    def payment_pin_badge(self, obj):
        if not obj.payment_pin:
            return format_html(
                '<span style="background-color: #6c757d; color: white; padding: 4px 8px; border-radius: 12px; font-size: 12px; font-weight: 600;" title="No PIN">'
                '<i class="fas fa-times"></i>'
                '</span>'
            )

        if obj.is_payment_pin_valid():
            return format_html(
                '<span style="background-color: #198754; color: white; padding: 4px 8px; border-radius: 12px; font-size: 12px; font-weight: 600;" title="Active PIN: {}">'
                '<i class="fas fa-key" style="margin-right: 4px;"></i> {}'
                '</span>'.format(obj.payment_pin, obj.payment_pin)
            )
        else:
            return format_html(
                '<span style="background-color: #dc3545; color: white; padding: 4px 8px; border-radius: 12px; font-size: 12px; font-weight: 600;" title="Expired PIN">'
                '<i class="fas fa-key" style="margin-right: 4px;"></i> EXP'
                '</span>'
            )
    payment_pin_badge.short_description = 'PIN'

    def payment_actions_quick(self, obj):
        """Quick action buttons for list view"""
        if obj.payment_status:
            return format_html(
                '<span style="color: #28a745;" title="Payment Confirmed">'
                '<i class="fas fa-check-circle"></i>'
                '</span>'
            )
        
        if not obj.payment_pin or not obj.is_payment_pin_valid():
            return format_html(
                '<a href="{}" title="Generate PIN" style="color: #28a745; text-decoration: none;">'
                '<i class="fas fa-key"></i>'
                '</a>',
                reverse('admin:shop_order_generate_pin', args=[obj.id])
            )
        
        return format_html(
            '<div style="display: flex; gap: 5px;">'
            '<a href="{}" title="Regenerate PIN" style="color: #ffc107; text-decoration: none;">'
            '<i class="fas fa-redo"></i>'
            '</a>'
            '<a href="{}" title="Confirm Payment" style="color: #17a2b8; text-decoration: none;" '
            'onclick="return confirm(\'Confirm payment?\');">'
            '<i class="fas fa-check"></i>'
            '</a>'
            '</div>',
            reverse('admin:shop_order_generate_pin', args=[obj.id]),
            reverse('admin:shop_order_confirm_payment', args=[obj.id])
        )
    payment_actions_quick.short_description = 'Actions'

    def created_at_formatted(self, obj):
        return obj.created_at.strftime("%b %d, %Y %I:%M %p")
    created_at_formatted.short_description = 'Created'
    created_at_formatted.admin_order_field = 'created_at'

    # ============ READONLY FIELD METHODS ============
    def payment_pin_display(self, obj):
        if obj.payment_pin:
            if obj.is_payment_pin_valid():
                return format_html(
                    '<div style="background: #d1e7dd; border: 1px solid #badbcc; border-radius: 4px; padding: 15px; margin: 0;">'
                    '<div style="display: flex; align-items: center;">'
                    '<i class="fas fa-key" style="font-size: 24px; margin-right: 15px; color: #0f5132;"></i>'
                    '<div>'
                    '<h4 style="margin: 0 0 5px 0; color: #0f5132;">{}</h4>'
                    '<p style="margin: 0; color: #0f5132;">Active PIN - Expires in: {}</p>'
                    '</div>'
                    '</div>'
                    '</div>'.format(obj.payment_pin, obj.payment_pin_expires_in)
                )
            else:
                return format_html(
                    '<div style="background: #f8d7da; border: 1px solid #f5c2c7; border-radius: 4px; padding: 15px; margin: 0;">'
                    '<div style="display: flex; align-items: center;">'
                    '<i class="fas fa-key" style="font-size: 24px; margin-right: 15px; color: #842029;"></i>'
                    '<div>'
                    '<h4 style="margin: 0 0 5px 0; color: #842029;">{}</h4>'
                    '<p style="margin: 0; color: #842029;">Expired PIN</p>'
                    '</div>'
                    '</div>'
                    '</div>'.format(obj.payment_pin)
                )
        return format_html(
            '<div style="background: #e2e3e5; border: 1px solid #d4d6d8; border-radius: 4px; padding: 15px; margin: 0;">'
            '<div style="display: flex; align-items: center;">'
            '<i class="fas fa-key" style="font-size: 24px; margin-right: 15px; color: #41464b;"></i>'
            '<div>'
            '<h5 style="margin: 0; color: #41464b;">No PIN Generated</h5>'
            '</div>'
            '</div>'
            '</div>'
        )
    payment_pin_display.short_description = 'Payment PIN'

    def payment_pin_status(self, obj):
        if obj.payment_status:
            return format_html(
                '<div style="background: #d1e7dd; border: 1px solid #badbcc; border-radius: 4px; padding: 10px; margin: 0;">'
                '<i class="fas fa-check-circle" style="color: #0f5132; margin-right: 8px;"></i>'
                '<strong style="color: #0f5132;">Payment Verified</strong>'
                '</div>'
            )

        if not obj.payment_pin:
            return format_html(
                '<span style="color: #6c757d;">No PIN generated</span>'
            )

        if obj.is_payment_pin_valid():
            return format_html(
                '<span style="color: #198754;">'
                '<i class="fas fa-check-circle" style="margin-right: 5px;"></i>'
                'Active (expires in {})'
                '</span>'.format(obj.payment_pin_expires_in)
            )
        else:
            return format_html(
                '<span style="color: #dc3545;">'
                '<i class="fas fa-times-circle" style="margin-right: 5px;"></i>'
                'Expired'
                '</span>'
            )
    payment_pin_status.short_description = 'PIN Status'

    def payment_pin_expires_in(self, obj):
        if obj.payment_pin and obj.payment_pin_expires_at:
            if obj.is_payment_pin_valid():
                time_left = obj.payment_pin_expires_at - timezone.now()
                if time_left.total_seconds() < 3600:
                    minutes = int(time_left.total_seconds() / 60)
                    return f"{minutes} minutes"
                else:
                    hours = int(time_left.total_seconds() / 3600)
                    minutes = int((time_left.total_seconds() % 3600) / 60)
                    return f"{hours}h {minutes}m"
            else:
                return "Expired"
        return "N/A"
    payment_pin_expires_in.short_description = 'Expires In'

    def payment_actions(self, obj):
        """Display payment action buttons"""
        if obj.payment_status:
            return format_html(
                '<div style="background: #d4edda; padding: 10px; border-radius: 4px; border: 1px solid #c3e6cb;">'
                '<i class="fas fa-check-circle" style="color: #155724; margin-right: 8px;"></i>'
                '<strong style="color: #155724;">Payment Confirmed</strong>'
                '</div>'
            )

        # Create buttons with inline styles for admin
        buttons = []

        # Generate/Regenerate PIN button
        if not obj.payment_pin or not obj.is_payment_pin_valid():
            buttons.append(
                format_html(
                    '<a href="{}" style="{}">'
                    '<i class="fas fa-key" style="margin-right: 5px;"></i>Generate PIN'
                    '</a>',
                    reverse('admin:shop_order_generate_pin', args=[obj.id]),
                    'background: #28a745; color: white; padding: 6px 12px; border-radius: 4px; '
                    'text-decoration: none; display: inline-block; margin-right: 8px; font-size: 13px;'
                )
            )
        else:
            buttons.append(
                format_html(
                    '<a href="{}" style="{}">'
                    '<i class="fas fa-redo" style="margin-right: 5px;"></i>Regenerate PIN'
                    '</a>',
                    reverse('admin:shop_order_generate_pin', args=[obj.id]),
                    'background: #ffc107; color: black; padding: 6px 12px; border-radius: 4px; '
                    'text-decoration: none; display: inline-block; margin-right: 8px; font-size: 13px;'
                )
            )

        # Confirm Payment button
        buttons.append(
            format_html(
                '<a href="{}" style="{}" onclick="{}">'
                '<i class="fas fa-check" style="margin-right: 5px;"></i>Confirm Payment'
                '</a>',
                reverse('admin:shop_order_confirm_payment', args=[obj.id]),
                'background: #17a2b8; color: white; padding: 6px 12px; border-radius: 4px; '
                'text-decoration: none; display: inline-block; margin-right: 8px; font-size: 13px;',
                "return confirm('Are you sure you want to manually confirm payment?');"
            )
        )

        # Reset PIN button
        if obj.payment_pin:
            buttons.append(
                format_html(
                    '<a href="{}" style="{}" onclick="{}">'
                    '<i class="fas fa-eraser" style="margin-right: 5px;"></i>Reset PIN'
                    '</a>',
                    reverse('admin:shop_order_reset_pin', args=[obj.id]),
                    'background: #dc3545; color: white; padding: 6px 12px; border-radius: 4px; '
                    'text-decoration: none; display: inline-block; font-size: 13px;',
                    "return confirm('Are you sure you want to reset the PIN?');"
                )
            )

        return mark_safe('<div style="display: flex; flex-wrap: wrap; gap: 8px;">{}</div>'.format(''.join(buttons)))
    payment_actions.short_description = 'Payment Actions'

    # ============ ADMIN ACTIONS ============
    @admin.action(description="Generate payment PIN for selected orders")
    def generate_payment_pins(self, request, queryset):
        successful = 0
        failed = 0

        for order in queryset:
            if order.payment_status:
                self.message_user(
                    request,
                    f"Order {order.order_number} already has verified payment",
                    level='warning'
                )
                failed += 1
                continue

            try:
                pin = order.generate_payment_pin(request.user)
                self.message_user(
                    request,
                    f"Generated PIN {pin} for order {order.order_number}",
                    level='success'
                )
                successful += 1
            except Exception as e:
                self.message_user(
                    request,
                    f"Failed to generate PIN for {order.order_number}: {str(e)}",
                    level='error'
                )
                failed += 1

        if successful:
            self.message_user(
                request,
                f"Successfully generated payment PINs for {successful} order(s)",
                level='success'
            )

    @admin.action(description="Reset payment PINs for selected orders")
    def reset_payment_pins(self, request, queryset):
        successful = 0
        for order in queryset:
            if not order.payment_status:
                order.reset_payment_pin()
                successful += 1

        self.message_user(
            request,
            f"Reset payment PINs for {successful} order(s)",
            level='success'
        )

    @admin.action(description="Confirm payments for selected orders")
    def confirm_payments(self, request, queryset):
        successful = 0
        failed = 0

        for order in queryset:
            if not order.payment_status:
                try:
                    success, message = order.confirm_payment(request.user)
                    if success:
                        self.message_user(
                            request,
                            f"Confirmed payment for order {order.order_number}",
                            level='success'
                        )
                        successful += 1
                    else:
                        self.message_user(
                            request,
                            f"Failed to confirm payment for {order.order_number}: {message}",
                            level='warning'
                        )
                        failed += 1
                except Exception as e:
                    self.message_user(
                        request,
                        f"Error confirming payment for {order.order_number}: {str(e)}",
                        level='error'
                    )
                    failed += 1

        if successful:
            self.message_user(
                request,
                f"Successfully confirmed payments for {successful} order(s)",
                level='success'
            )

    @admin.action(description="Mark selected as Processing")
    def mark_as_processing(self, request, queryset):
        for order in queryset:
            if order.status == 'PENDING' and order.payment_status:
                order.status = 'PROCESSING'
                order.save()
        self.message_user(request, f"Marked {queryset.count()} order(s) as Processing")

    @admin.action(description="Mark selected as Shipped")
    def mark_as_shipped(self, request, queryset):
        for order in queryset:
            if order.status == 'PROCESSING':
                order.status = 'SHIPPED'
                order.shipped_at = timezone.now()
                order.save()
        self.message_user(request, f"Marked {queryset.count()} order(s) as Shipped")

    @admin.action(description="Mark selected as Delivered")
    def mark_as_delivered(self, request, queryset):
        for order in queryset:
            if order.status == 'SHIPPED':
                order.status = 'DELIVERED'
                order.delivered_at = timezone.now()
                order.save()
        self.message_user(request, f"Marked {queryset.count()} order(s) as Delivered")

    @admin.action(description="Mark selected as Cancelled")
    def mark_as_cancelled(self, request, queryset):
        for order in queryset:
            if order.status in ['PENDING', 'PROCESSING']:
                order.status = 'CANCELLED'
                order.save()
        self.message_user(request, f"Marked {queryset.count()} order(s) as Cancelled")

    # ============ CUSTOM URLS ============
    def get_urls(self):
        from django.urls import path

        urls = super().get_urls()
        custom_urls = [
            path('<int:order_id>/generate-pin/',
                 self.admin_site.admin_view(self.generate_pin_view),
                 name='shop_order_generate_pin'),
            path('<int:order_id>/confirm-payment/',
                 self.admin_site.admin_view(self.confirm_payment_view),
                 name='shop_order_confirm_payment'),
            path('<int:order_id>/reset-pin/',
                 self.admin_site.admin_view(self.reset_pin_view),
                 name='shop_order_reset_pin'),
        ]
        return custom_urls + urls

    def generate_pin_view(self, request, order_id):
        """View to generate PIN for a specific order"""
        order = get_object_or_404(Order, id=order_id)

        if order.payment_status:
            messages.error(request, f"Payment already confirmed for order {order.order_number}")
        else:
            try:
                pin = order.generate_payment_pin(request.user)
                messages.success(request, f"✅ Generated PIN: <strong>{pin}</strong> for order {order.order_number}")
            except Exception as e:
                messages.error(request, f"❌ Error generating PIN: {str(e)}")

        return HttpResponseRedirect(reverse('admin:shop_order_change', args=[order_id]))

    def confirm_payment_view(self, request, order_id):
        """View to confirm payment for a specific order"""
        order = get_object_or_404(Order, id=order_id)

        if order.payment_status:
            messages.warning(request, f"Payment already confirmed for order {order.order_number}")
        else:
            try:
                success, message = order.confirm_payment(request.user)
                if success:
                    messages.success(request, f"✅ Payment confirmed for order {order.order_number}")
                else:
                    messages.error(request, f"❌ Error confirming payment: {message}")
            except Exception as e:
                messages.error(request, f"❌ Error confirming payment: {str(e)}")

        return HttpResponseRedirect(reverse('admin:shop_order_change', args=[order_id]))

    def reset_pin_view(self, request, order_id):
        """View to reset PIN for a specific order"""
        order = get_object_or_404(Order, id=order_id)

        if order.payment_status:
            messages.error(request, "Cannot reset PIN - payment already confirmed")
        else:
            order.reset_payment_pin()
            messages.success(request, f"✅ Reset PIN for order {order.order_number}")

        return HttpResponseRedirect(reverse('admin:shop_order_change', args=[order_id]))

    # ============ CUSTOM QUERYSET ============
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user', 'cart').prefetch_related('items')

# ==================== CART ADMIN ====================
class CartItemInline(admin.TabularInline):
    model = CartItem
    fields = ['product', 'quantity', 'price', 'get_total_price']
    readonly_fields = ['get_total_price']
    extra = 0

    def get_total_price(self, obj):
        """Safe method to get total price"""
        try:
            if hasattr(obj, 'total_price'):
                total = obj.total_price
                if total is not None:
                    return f"${float(total):.2f}"
        except (AttributeError, TypeError, ValueError):
            pass
        return "$0.00"
    get_total_price.short_description = "Total"

class CartAdmin(admin.ModelAdmin):
    list_display = ['id', 'user_display', 'session_key_short', 'total_items',
                    'subtotal_display', 'created_at_formatted']
    list_filter = ['created_at']
    search_fields = ['user__username', 'user__email', 'session_key']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [CartItemInline]

    def user_display(self, obj):
        if obj.user:
            return obj.user.username
        return "Anonymous"
    user_display.short_description = 'User'

    def session_key_short(self, obj):
        if obj.session_key:
            return obj.session_key[:15] + '...' if len(obj.session_key) > 15 else obj.session_key
        return "N/A"
    session_key_short.short_description = 'Session'

    def subtotal_display(self, obj):
        try:
            return f"${float(obj.subtotal):.2f}"
        except (TypeError, ValueError):
            return "$0.00"
    subtotal_display.short_description = 'Subtotal'

    def created_at_formatted(self, obj):
        return obj.created_at.strftime("%b %d, %Y")
    created_at_formatted.short_description = 'Created'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')

# ==================== CATEGORY ADMIN ====================
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'product_count', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at', 'updated_at']

    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = 'Products'

# ==================== COUPON ADMIN ====================
class CouponAdmin(admin.ModelAdmin):
    list_display = ['code', 'discount_type', 'discount_value', 'valid_from',
                    'valid_to', 'is_active', 'used_count']
    list_filter = ['discount_type', 'is_active']  # Removed 'created_at' from list_filter
    search_fields = ['code', 'description']
    readonly_fields = ['used_count']  # Removed 'created_at', 'updated_at'
    list_editable = ['is_active']

    def used_count(self, obj):
        return obj.orders.count()
    used_count.short_description = 'Used'

# ==================== REVIEW ADMIN ====================
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['product', 'user', 'rating_stars', 'is_approved', 'created_at']
    list_filter = ['rating', 'is_approved', 'created_at']
    search_fields = ['product__name', 'user__username', 'comment']
    readonly_fields = ['created_at', 'updated_at']
    list_editable = ['is_approved']

    def rating_stars(self, obj):
        stars = '★' * obj.rating + '☆' * (5 - obj.rating)
        return format_html('<span style="color: gold;">{}</span>'.format(stars))
    rating_stars.short_description = 'Rating'

# ==================== REGISTER MODELS ====================
admin.site.register(Category, CategoryAdmin)
admin.site.register(Product, ProductAdmin)
admin.site.register(Review, ReviewAdmin)
admin.site.register(Cart, CartAdmin)
admin.site.register(Order, OrderAdmin)
admin.site.register(Coupon, CouponAdmin)

# ==================== ADMIN SITE CUSTOMIZATION ====================
admin.site.site_header = "Tested Overtime Admin"
admin.site.site_title = "Tested Overtime Admin Portal"
admin.site.index_title = "Dashboard"
