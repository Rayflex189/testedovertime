from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import CustomUser, UserProfile

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    
    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'first_name', 'last_name', 'password1', 'password2')
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            # Create profile for the user
            UserProfile.objects.create(user=user)
        return user

class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'first_name', 'last_name', 'phone', 
                 'address', 'city', 'state', 'zip_code', 'country',
                 'profile_picture', 'date_of_birth', 'shipping_address',
                 'shipping_city', 'shipping_state', 'shipping_zip',
                 'newsletter_subscribed')

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ('bio', 'preferences')
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4}),
        }