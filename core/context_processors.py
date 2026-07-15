from users.models import Favorite
from cart.models import Cart
from products.models import Category
from core.demo_store import get_store_context


def global_counts(request):
    cart_count = 0
    fav_count = 0

    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
        cart_count = cart.items.count() if cart else 0
        fav_count = Favorite.objects.filter(user=request.user).count()

    return {
        'cart_count': cart_count,
        'favorite_count': fav_count,
    }


def categories_processor(request):
    return {
        'categories': Category.objects.all()
    }


def store_settings(request):
    return get_store_context()