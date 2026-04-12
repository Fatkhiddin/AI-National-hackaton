from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from .forms import CustomAuthenticationForm, CustomUserCreationForm
from .models import CustomUser


@require_http_methods(["GET", "POST"])
def login_view(request):
    """
    User login view
    """
    if request.user.is_authenticated:
        return redirect('welcome')
    
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome {user.username}!')
                return redirect('welcome')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = CustomAuthenticationForm()
    
    return render(request, 'user/login.html', {'form': form})


@require_http_methods(["GET", "POST"])
def register_view(request):
    """
    User registration view
    """
    if request.user.is_authenticated:
        return redirect('welcome')
    
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Account created successfully!')
            return redirect('welcome')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'user/register.html', {'form': form})


@login_required(login_url='user:login')
def logout_view(request):
    """
    User logout view
    """
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('user:login')


@login_required(login_url='user:login')
def welcome_view(request):
    """
    Welcome page showing 'RoofAI' after login
    """
    context = {
        'user': request.user,
        'app_name': 'RoofAI'
    }
    return render(request, 'user/welcome.html', context)
