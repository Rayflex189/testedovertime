from django import forms
from .models import Review, Order

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'title', 'comment']
        widgets = {
            'rating': forms.Select(choices=[(i, f'{i} star{"s" if i != 1 else ""}') for i in range(1, 6)]),
            'comment': forms.Textarea(attrs={'rows': 4}),
        }

class CheckoutForm(forms.ModelForm):
    use_same_billing = forms.BooleanField(
        required=False, 
        initial=True,
        label="Use shipping address for billing"
    )
    
    class Meta:
        model = Order
        fields = [
            'shipping_address', 'shipping_city', 'shipping_state', 
            'shipping_zip', 'shipping_country',
            'billing_address', 'billing_city', 'billing_state',
            'billing_zip', 'billing_country',
            'payment_method', 'notes'
        ]
        widgets = {
            'shipping_address': forms.Textarea(attrs={'rows': 3}),
            'billing_address': forms.Textarea(attrs={'rows': 3}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['payment_method'].initial = 'COD'
    
    def clean(self):
        cleaned_data = super().clean()
        use_same_billing = cleaned_data.get('use_same_billing')
        
        if use_same_billing:
            cleaned_data['billing_address'] = cleaned_data.get('shipping_address')
            cleaned_data['billing_city'] = cleaned_data.get('shipping_city')
            cleaned_data['billing_state'] = cleaned_data.get('shipping_state')
            cleaned_data['billing_zip'] = cleaned_data.get('shipping_zip')
            cleaned_data['billing_country'] = cleaned_data.get('shipping_country')
        
        return cleaned_data