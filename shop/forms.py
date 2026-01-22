from django import forms
from .models import Review, Order
from django.core.validators import validate_email
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Layout, Row, Column, Field

class ContactSupportForm(forms.Form):
    """Form for contacting customer support"""
    ISSUE_TYPES = [
        ('', 'Select an issue type'),
        ('order', 'Order Issue'),
        ('payment', 'Payment Issue'),
        ('shipping', 'Shipping/Delivery'),
        ('product', 'Product Question'),
        ('return', 'Return/Exchange'),
        ('account', 'Account Issue'),
        ('other', 'Other')
    ]

    name = forms.CharField(
        label='Full Name',
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Your full name',
            'autocomplete': 'name'
        })
    )

    email = forms.EmailField(
        label='Email Address',
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Your email address',
            'autocomplete': 'email'
        })
    )

    issue_type = forms.ChoiceField(
        label='Issue Type',
        choices=ISSUE_TYPES,
        required=True,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )

    order_number = forms.CharField(
        label='Order Number (if applicable)',
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., ORD-20260120-XXXXXX'
        })
    )

    subject = forms.CharField(
        label='Subject',
        max_length=200,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Brief description of your issue'
        })
    )

    message = forms.CharField(
        label='Message',
        required=True,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 6,
            'placeholder': 'Please describe your issue in detail...',
            'style': 'resize: vertical;'
        })
    )

    attach_file = forms.FileField(
        label='Attach File (optional)',
        required=False,
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control',
            'accept': '.jpg,.jpeg,.png,.pdf,.doc,.docx'
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'needs-validation'
        self.helper.form_id = 'supportForm'
        self.helper.form_enctype = 'multipart/form-data'
        self.helper.add_input(Submit('submit', 'Send Message', css_class='btn-primary'))

        # Add crispy form layout
        self.helper.layout = Layout(
            Row(
                Column('name', css_class='col-md-6 mb-3'),
                Column('email', css_class='col-md-6 mb-3'),
            ),
            Row(
                Column('issue_type', css_class='col-md-6 mb-3'),
                Column('order_number', css_class='col-md-6 mb-3'),
            ),
            Field('subject', css_class='mb-3'),
            Field('message', css_class='mb-3'),
            Field('attach_file', css_class='mb-4'),
        )

    def clean_email(self):
        email = self.cleaned_data.get('email')
        try:
            validate_email(email)
        except forms.ValidationError:
            raise forms.ValidationError("Please enter a valid email address.")
        return email

    def clean_message(self):
        message = self.cleaned_data.get('message')
        if len(message.strip()) < 10:
            raise forms.ValidationError("Please provide more details about your issue.")
        return message

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
