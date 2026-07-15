from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from pages.forms import AddressForm
from users.forms import UserProfileForm
from .models import Favorite, Address
from products.models import Product

@login_required
def favorites_list(request):
    favorites = Favorite.objects.filter(user=request.user).select_related('product')
    return render(request, 'products/favorites.html', {'favorites': favorites})

@login_required
def add_to_favorites(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    Favorite.objects.get_or_create(user=request.user, product=product)
    return redirect(request.META.get('HTTP_REFERER', 'home'))

@login_required
def remove_from_favorites(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    Favorite.objects.filter(user=request.user,product=product).delete()
    return redirect(request.META.get('HTTP_REFERER', 'home'))

@login_required
def add_address_ajax(request):
    if request.method == "POST":
        form = AddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user  # Connect to the logged in user
            address.save()
            
            # Return the information to display the newly added address in the list
            return JsonResponse({
                "success": True,
                "address": {
                    "id": address.id,
                    "title": address.title,
                    "full_name": address.full_name,
                    "address_line": address.address_line,
                    "city": address.city,
                    "district": address.district,
                }
            })
        else:
            return JsonResponse({"success": False, "errors": form.errors})
    return JsonResponse({"success": False, "message": "Geçersiz istek"})


@login_required
def edit_address(request, address_id):
    address = get_object_or_404(Address, id=address_id, user=request.user)
    if request.method == 'POST':
        # Process the data from the form to the model
        address.title = request.POST.get('title')
        address.full_name = request.POST.get('full_name')
        address.phone = request.POST.get('phone')
        address.city = request.POST.get('city')
        address.district = request.POST.get('district')
        address.address_line = request.POST.get('address_line')
        address.save()
        messages.success(request, "Adres başarıyla güncellendi.")
    return redirect('profile') # Return to the profile page

@login_required
def delete_address(request, address_id):
    address = get_object_or_404(Address, id=address_id, user=request.user)

    if request.method == 'POST':
        address.delete()
        messages.success(request, 'Adres başarıyla silindi.')
        return redirect('profile')
    
    return render('profile')

@login_required
def update_profile(request):
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profil başarıyla güncellendi.')
            return redirect('profile') # 'update_profile' not, your main profile URL
    else:
        form = UserProfileForm(instance=request.user)
    return render(request, 'accounts/profile.html', {'form': form}) # 'profile' not, your main profile URL