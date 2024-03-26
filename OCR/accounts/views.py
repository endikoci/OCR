

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from .forms import CustomUserCreationForm
from django.contrib import messages
from django.urls import reverse
from django.contrib.auth.decorators import login_required


def clear_messages(request):
    storage = messages.get_messages(request)
    for message in storage:
        # Mark message as used
        storage.used = True


def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            # Redirect to login page after successful registration
            return redirect('login')
    else:
        form = CustomUserCreationForm()
    return render(request, 'registration/register.html', {'form': form})


def user_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, 'Invalid email or password.')
            return redirect('login')
    return render(request, 'registration/login.html')


@login_required
def user_logout(request):
    logout(request)
    # Redirect to a specific URL after logout
    return redirect(reverse('login'))