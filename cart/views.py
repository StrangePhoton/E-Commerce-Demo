from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from django.utils.crypto import get_random_string
from django.contrib import messages
from orders.models import Order, OrderItem
from users.models import Favorite
from .models import Cart, CartItem
from products.models import Product

def get_or_create_cart(request):
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
    else:
        if not request.session.session_key:
            request.session.create()
        session_key = request.session.session_key
        cart, created = Cart.objects.get_or_create(session_key=session_key, user=None)
    return cart

@login_required
@require_POST
@csrf_protect
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_active=True)
    
    # Check the inactive product
    if not product.is_active:
        messages.error(request, "Bu ürün şu anda satışta değildir.")
        return redirect('home')
    
    # Get the size and color parameters
    size = request.POST.get('size', '').strip() or None
    color = request.POST.get('color', '').strip() or None
    
    # If the product has size/color options but not selected, error
    if product.has_sizes and not size:
        messages.error(request, "Lütfen bir beden seçiniz.")
        return redirect('product_detail', slug=product.slug)
    if product.has_colors and not color:
        messages.error(request, "Lütfen bir renk seçiniz.")
        return redirect('product_detail', slug=product.slug)
    
    # Stock check - if variant exists, check the variant stock
    available_stock = product.get_stock(size=size, color=color)
    if available_stock <= 0:
        messages.error(request, f"Maalesef {product.name} ürünümüzün stoğu tükenmiştir.")
        return redirect('product_detail', slug=product.slug)
    
    cart = get_or_create_cart(request)
    
    # Find or create the cart item for the same product, size and color combination
    item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        size=size,
        color=color,
        defaults={'quantity': 1}
    )
    
    if not created:
        # Check if the stock is sufficient before adding 1 to the current quantity
        if item.quantity < available_stock:
            item.quantity += 1
            item.save()
            messages.success(request, "Ürün miktarı güncellendi.")
        else:
            messages.warning(request, f"Stok miktarından fazlasını sepete ekleyemezsiniz. (Mevcut stok: {available_stock})")
    else:
        messages.success(request, "Ürün sepete eklendi.")

    return redirect('view_cart')

@require_POST
@csrf_protect
def update_cart(request):
    cart = get_or_create_cart(request)
    for item in cart.items.all():
        quantity = request.POST.get(f'quantity_{item.id}')
        if quantity:
            new_qty = int(quantity)
            # Stock check - if variant exists, check the variant stock
            available_stock = item.product.get_stock(size=item.size, color=item.color)
            if new_qty <= available_stock:
                item.quantity = new_qty
                item.save()
            else:
                messages.warning(request, f"{item.product.name} için maksimum stok ({available_stock}) sınırına ulaşıldı.")
    return redirect('view_cart')

def remove_from_cart(request, item_id):
    item = get_object_or_404(CartItem, id=item_id)
    item.delete()
    return redirect('view_cart')

def view_cart(request):
    cart = get_or_create_cart(request)
    
    # Check the inactive products in the cart and remove them
    inactive_items = []
    for item in cart.items.all():
        if not item.product.is_active:
            inactive_items.append(item.product.name)
            item.delete()
    
    if inactive_items:
        messages.warning(request, f"Sepetinizdeki şu ürünler artık satışta değil ve sepetten kaldırıldı: {', '.join(inactive_items)}")
    
    return render(request, 'cart/cart.html', {'cart': cart})

@login_required
def go_to_checkout(request):
    cart = get_or_create_cart(request)

    if not cart.items.exists():
        messages.warning(request, "Sepetiniz boş.")
        return redirect("view_cart")
    
    # Check the inactive products in the cart
    inactive_items = []
    for item in cart.items.all():
        if not item.product.is_active:
            inactive_items.append(item.product.name)
    
    if inactive_items:
        messages.error(request, f"Sepetinizdeki şu ürünler artık satışta değil: {', '.join(inactive_items)}. Lütfen sepetinizi kontrol edin.")
        return redirect("view_cart")

    order, created = Order.objects.get_or_create(
        user=request.user,
        status="draft"
    )

    if created:
        order.items.all().delete()
        for item in cart.items.all():
            # Check again (for security)
            if item.product.is_active:
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    quantity=item.quantity,
                    price=item.get_unit_price(),
                    size=item.size,
                    color=item.color
                )

        order.calculate_totals()  # shipping + total
        order.save()

    request.session["checkout_order_id"] = order.id
    return redirect("checkout-address")