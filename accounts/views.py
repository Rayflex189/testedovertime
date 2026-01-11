from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate
from django.contrib import messages
from .forms import CustomUserCreationForm, UserProfileForm, CustomUserChangeForm, CustomAuthenticationForm

@login_required
def delete_account(request):
    if request.method == 'POST':
        # Delete the user
        user = request.user
        logout(request)  # Logout first
        user.delete()  # Delete the user
        
        messages.success(request, "Your account has been deleted successfully.")
        return redirect('shop:home')
    
    # If not POST, redirect to profile edit
    return redirect('accounts:profile_edit')

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # Don't login automatically - just show success message
            messages.success(request, "Registration successful! Please login to continue.")
            
            # Redirect to login page
            return redirect('accounts:login')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'accounts/register.html', {'form': form})

def custom_login(request):
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            
            if user is not None:
                login(request, user)
                messages.success(request, f"Welcome back, {username}!")
                
                # Redirect to the next page if specified, otherwise home
                next_page = request.GET.get('next', 'shop:home')
                return redirect(next_page)
    else:
        form = CustomAuthenticationForm()
    
    return render(request, 'accounts/login.html', {'form': form})

@login_required
def profile(request):
    return render(request, 'accounts/profile.html')

@login_required
def profile_edit(request):
    if request.method == 'POST':
        user_form = CustomUserChangeForm(request.POST, instance=request.user)
        profile_form = UserProfileForm(request.POST, request.FILES, instance=request.user.profile)
        
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect('accounts:profile')
    else:
        user_form = CustomUserChangeForm(instance=request.user)
        profile_form = UserProfileForm(instance=request.user.profile)
    
    return render(request, 'accounts/profile_edit.html', {
        'user_form': user_form,
        'profile_form': profile_form
    })


@login_required
def order_history(request):
    orders = request.user.orders.all().order_by('-created_at')
    return render(request, 'accounts/order_history.html', {'orders': orders})