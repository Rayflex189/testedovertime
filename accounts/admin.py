from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, UserProfile

class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ['username', 'email', 'first_name', 'last_name', 'is_staff']
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Information', {
            'fields': ('phone', 'address', 'city', 'state', 'zip_code', 'country',
                      'profile_picture', 'date_of_birth', 'shipping_address',
                      'shipping_city', 'shipping_state', 'shipping_zip', 
                      'newsletter_subscribed'),
        }),
    )

class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'bio']
    filter_horizontal = ['wishlist']

admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(UserProfile, UserProfileAdmin)