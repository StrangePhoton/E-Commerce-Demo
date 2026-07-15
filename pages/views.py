from datetime import timedelta
from decimal import Decimal, InvalidOperation
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.urls import reverse
from django.utils import timezone
from django.db.models import Count, Sum, Avg, Q
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods
from django.core.mail import send_mail, EmailMultiAlternatives
from django.utils.html import format_html, strip_tags
from django.utils.safestring import mark_safe
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.db.models import Sum as SumFunc, F

from .forms import ProductForm, OrderStatusForm, EmailForm, ProductImageFormSet, SignUpForm, UserProfileForm, AddressForm, HomeSlideForm, BulkDiscountForm
from .models import HomeSlide
from products.models import Category, Product, ProductRating, BulkDiscount
from orders.models import Order, OrderItem, OrderSetting
from users.models import Address, Favorite
from users.tokens import account_activation_token
from users.models import CustomUser, ContactMessage
from orders.models import ReturnRequest

def home(request):
    filter_type = request.GET.get('filter', 'yeni')
    slides = HomeSlide.objects.all().order_by('order')

    # 1. Data Filtering (Query Set Creation) - Only active products
    if filter_type == 'yeni':
        two_months_ago = timezone.now() - timedelta(days=60)
        products_query = Product.objects.filter(is_active=True, created_at__gte=two_months_ago).order_by('-created_at')
        if products_query.count() < 20:
            products_query = Product.objects.filter(is_active=True).order_by('-created_at')
    
    elif filter_type == 'cok-satan':
        products_query = (Product.objects.filter(is_active=True)
                         .annotate(order_count=Count('orderitem'))
                         .filter(order_count__gt=0).order_by('-order_count'))
    
    elif filter_type == 'kampanya':
        products_query = Product.objects.filter(is_active=True, bulk_discounts__isnull=False).distinct()
    
    else:
        products_query = Product.objects.filter(is_active=True).order_by('-id')

    # 2. Pagination Settings
    paginator = Paginator(products_query, 20) # 20 products per page
    page_number = request.GET.get('page', 1)

    # 3. AJAX Request Control (More View Button)
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        try:
            # If the requested page is greater than the total number of pages, return empty (Prevents repetition)
            if int(page_number) > paginator.num_pages:
                return HttpResponse("")
            
            page_obj = paginator.get_page(page_number)
            return render(request, 'includes/product_list_partial.html', {'products': page_obj})
        except:
            return HttpResponse("")

    # 4. Normal Page Load
    page_obj = paginator.get_page(page_number)

    favorites = []
    if request.user.is_authenticated:
        favorites = Favorite.objects.filter(user=request.user).values_list('product_id', flat=True)
    
    return render(request, 'index.html', {
        'slides': slides,
        'page_obj': page_obj,
        'current_filter': filter_type,
        'favorites': favorites,
    })

def search_results(request):
    """Search results page"""
    query = request.GET.get('q', '').strip()
    favorites = []
    
    if request.user.is_authenticated:
        favorites = Favorite.objects.filter(user=request.user).values_list('product_id', flat=True)
    
    if query:
        # Search in product name, description, and category
        products = Product.objects.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(category__name__icontains=query)
        ).filter(is_active=True).distinct()
    else:
        products = Product.objects.none()
    
    title = f'Arama Sonuçları: "{query}"' if query else 'Arama'
    
    return render(request, 'categories/category-template.html', {
        'title': title,
        'products': products,
        'favorites': favorites,
        'search_query': query
    })

def hasta_bakim_malzemeleri(request):
    category = get_object_or_404(Category, name='Hasta Bakım Malzemeleri')
    products = Product.objects.filter(category=category, is_active=True)
    favorites = []
    if request.user.is_authenticated:
        favorites = Favorite.objects.filter(user=request.user).values_list('product_id', flat=True)
    return render(request, 'categories/category-template.html', {'title': category.name, 'products': products, 'favorites': favorites})

def medikal_sarf_malzemeleri(request):
    category = get_object_or_404(Category, name='Medikal Sarf Malzemeleri')
    products = Product.objects.filter(category=category, is_active=True)
    favorites = []
    if request.user.is_authenticated:
        favorites = Favorite.objects.filter(user=request.user).values_list('product_id', flat=True)
    return render(request, 'categories/category-template.html', {'title': category.name, 'products': products, 'favorites': favorites})

def medikal_malzemeler(request):
    category = get_object_or_404(Category, name='Medikal Malzemeler')
    products = Product.objects.filter(category=category, is_active=True)
    favorites = []
    if request.user.is_authenticated:
        favorites = Favorite.objects.filter(user=request.user).values_list('product_id', flat=True)
    return render(request, 'categories/category-template.html', {'title': category.name, 'products': products, 'favorites': favorites})

def kisisel_yasam_malzemeleri(request):
    category = get_object_or_404(Category, name='Kişisel Yaşam Malzemeleri')
    products = Product.objects.filter(category=category, is_active=True)
    favorites = []
    if request.user.is_authenticated:
        favorites = Favorite.objects.filter(user=request.user).values_list('product_id', flat=True)
    return render(request, 'categories/category-template.html', {'title': category.name, 'products': products, 'favorites': favorites})

def vitamin_ve_takviyeler(request):
    category = get_object_or_404(Category, name='Vitamin ve Takviyeler')
    products = Product.objects.filter(category=category, is_active=True)
    favorites = []
    if request.user.is_authenticated:
        favorites = Favorite.objects.filter(user=request.user).values_list('product_id', flat=True)
    return render(request, 'categories/category-template.html', {'title': category.name, 'products': products, 'favorites': favorites})

def ev_ve_yasam(request):
    category = get_object_or_404(Category, name='Ev ve Yaşam')
    products = Product.objects.filter(category=category, is_active=True)
    favorites = []
    if request.user.is_authenticated:
        favorites = Favorite.objects.filter(user=request.user).values_list('product_id', flat=True)
    return render(request, 'categories/category-template.html', {'title': category.name, 'products': products, 'favorites': favorites})

def elektronik_cihazlar(request):
    category = get_object_or_404(Category, name='Elektronik Cihazlar')
    products = Product.objects.filter(category=category, is_active=True)
    favorites = []
    if request.user.is_authenticated:
        favorites = Favorite.objects.filter(user=request.user).values_list('product_id', flat=True)
    return render(request, 'categories/category-template.html', {'title': category.name, 'products': products, 'favorites': favorites})

def best_sellers(request):
    products = Product.objects.filter(is_active=True).annotate(order_count=Count('orderitem')).filter(order_count__gt=0).order_by('-order_count')[:40]
    favorites = []
    if request.user.is_authenticated:
        favorites = Favorite.objects.filter(user=request.user).values_list('product_id', flat=True)
    return render(request, 'categories/category-template.html', {'title': 'En Çok Satanlar', 'products': products, 'favorites': favorites})

def new_arrivals(request):
    two_months_ago = timezone.now() - timedelta(days=60)
    new_products = Product.objects.filter(is_active=True, created_at__gte=two_months_ago).order_by('-created_at')
    if new_products.count() < 40:
        products = Product.objects.filter(is_active=True).order_by('-created_at')[:40]
    else:
        products = new_products
    favorites = []
    if request.user.is_authenticated:
        favorites = Favorite.objects.filter(user=request.user).values_list('product_id', flat=True)
    return render(request, 'categories/category-template.html', {'title': 'Yeni Ürünler', 'products': products, 'favorites': favorites})

def campaigns(request):
    category = get_object_or_404(Category, name='Kampanyalar')
    products = Product.objects.filter(category=category, is_active=True)
    favorites = []
    if request.user.is_authenticated:
        favorites = Favorite.objects.filter(user=request.user).values_list('product_id', flat=True)
    return render(request, 'categories/category-template.html', {'title': category.name, 'products': products, 'favorites': favorites})

def login_view(request):
    if request.method == "POST":
        email = request.POST["username"]
        password = request.POST["password"]

        user = authenticate(request, username=email, password=password)

        if user is not None:
            if not user.is_active:
                messages.warning(
                    request,
                    "Mail aktivasyonu yapmadan giriş yapamazsınız."
                )
                return redirect("login")

            login(request, user)
            # if next parameter is present, redirect to it, otherwise redirect to home
            next_url = request.GET.get("next") or request.POST.get("next") or request.session.pop("next", None)
            if next_url:
                return redirect(next_url)
            return redirect("home")

        messages.error(request, "Email veya şifre hatalı.")

    return render(request, "accounts/login.html")

@csrf_protect
def signup_view(request):
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.save()

            # 🔐 Token + UID (Base64 encoded user ID)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = account_activation_token.make_token(user)

            current_site = get_current_site(request)
            activation_link = request.build_absolute_uri(
                reverse(
                    "activate-account",
                    kwargs={"uidb64": uid, "token": token},
                )
            )

            subject = f"Hesabınızı Aktifleştirin | {settings.STORE_NAME}"

            html_content = render_to_string(
                "emails/account-activation.html",
                {
                    "user": user,
                    "activation_link": activation_link,
                }
            )

            text_content = strip_tags(html_content)

            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email],
            )

            email.attach_alternative(html_content, "text/html")
            email.send()

            return render(
                request,
                "accounts/before-activation.html",
                {"email": user.email}
            )

    else:
        form = SignUpForm()

    return render(request, "accounts/signup.html", {"form": form})

def activate_account(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = CustomUser.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
        user = None

    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save()
        return render(request, "accounts/after-activation.html")
    else:
        return render(request, "accounts/activation-invalid.html")

def resend_activation_mail(request):
    if request.method == "POST":
        email = request.POST.get("email")

        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            messages.error(request, "Bu email adresiyle kayıtlı kullanıcı bulunamadı.")
            return redirect("login")

        if user.is_active:
            messages.info(request, "Bu hesap zaten aktif.")
            return redirect("login")

        send_activation_mail(request, user)  # we will write it later
        return render(
            request,
            "accounts/before-activation.html",
            {"email": user.email}
        )

    return redirect("login")


def category_products(request, category_id):
    category = Category.objects.get(id=category_id)
    products = Product.objects.filter(category=category, is_active=True)
    favorites = []
    if request.user.is_authenticated:
        favorites = Favorite.objects.filter(user=request.user).values_list('product_id', flat=True)
    return render(request, 'category.html', {'category': category, 'products': products, 'favorites': favorites})

def product_detail(request, slug):
    from products.models import ProductVariant
    
    # Block inactive products (except admin pages)
    product = get_object_or_404(Product, pk=slug, is_active=True) if slug.isdigit() else get_object_or_404(Product, slug=slug, is_active=True)
    favorites = []
    user_rating = None
    can_rate = False
    
    if request.user.is_authenticated:
        favorites = Favorite.objects.filter(user=request.user).values_list('product_id', flat=True)
        try:
            user_rating = ProductRating.objects.get(user=request.user, product=product)
        except ProductRating.DoesNotExist:
            pass
        
        delivered_orders = Order.objects.filter(user=request.user, status='delivered')
        can_rate = OrderItem.objects.filter(order__in=delivered_orders, product=product).exists()
    
    ratings = ProductRating.objects.filter(product=product).select_related('user').order_by('-created_at')
    average_rating = product.get_average_rating()
    rating_count = product.get_rating_count()
    
    # Prefetch variants and calculate available sizes/colors
    product = Product.objects.prefetch_related('variants').get(pk=product.pk)
    
    # Debug: Check variants
    variant_count = product.variants.count()
    if product.has_sizes or product.has_colors:
        if variant_count == 0:
            messages.warning(request, f"Bu ürün için variant seçenekleri açık ama henüz variant eklenmemiş. Lütfen admin panelinden variant ekleyin.")
    
    available_sizes = product.get_available_sizes() if product.has_sizes else []
    available_colors = product.get_available_colors() if product.has_colors else []
    
    return render(request, 'products/product-detail.html', {
        'product': product,
        'favorites': favorites,
        'user_rating': user_rating,
        'ratings': ratings,
        'average_rating': average_rating,
        'rating_count': rating_count,
        'can_rate': can_rate,
        'available_sizes': available_sizes,
        'available_colors': available_colors,
    })



def product_stock_api(request, product_id):
    """Ürün stok bilgisini döndüren API endpoint"""
    product = get_object_or_404(Product, id=product_id, is_active=True)
    size = request.GET.get('size', '').strip() or None
    color = request.GET.get('color', '').strip() or None
    
    stock = product.get_stock(size=size, color=color)
    
    return JsonResponse({
        'stock': stock,
        'available': stock > 0
    })

@csrf_protect
@login_required
def profile_view(request):
    # Filter orders in draft and awaiting payment status
    orders = Order.objects.filter(
        user=request.user
    ).exclude(
        status__in=['draft', 'awaiting_payment']
    ).prefetch_related('items__product').order_by('-created_at')

    ratings = ProductRating.objects.filter(user=request.user)
    ratings_dict = {r.product_id: r for r in ratings}

    for order in orders:
        for item in order.items.all():
            item.user_rating = ratings_dict.get(item.product_id)

    favorites = Favorite.objects.filter(user=request.user).select_related('product')
    addresses = Address.objects.filter(user=request.user)
    
    # Return requests
    return_requests = ReturnRequest.objects.filter(user=request.user).select_related('order', 'order_item__product').order_by('-created_at')

    profile_form = UserProfileForm(instance=request.user)
    address_form = AddressForm()

    if request.method == 'POST':
        if 'address_line' in request.POST:
            address_form = AddressForm(request.POST)
            if address_form.is_valid():
                address = address_form.save(commit=False)
                address.user = request.user
                address.save()
                return redirect('profile')

        elif 'first_name' in request.POST:
            profile_form = UserProfileForm(request.POST, instance=request.user)
            if profile_form.is_valid():
                profile_form.save()
                return redirect('profile')

    return render(request, 'accounts/profile.html', {
        'orders': orders,
        'favorites': favorites,
        'addresses': addresses,
        'return_requests': return_requests,
        'profile_form': profile_form,
        'address_form': address_form,
    })

@user_passes_test(lambda u: u.is_staff)
def admin_dashboard(request):
    from datetime import timedelta
    import json
    
    # Get statistics
    total_products = Product.objects.count()
    contact_messages = ContactMessage.objects.count()
    
    # New detailed order statistics
    # Awaiting orders -> Orders in paid status
    awaiting_orders = Order.objects.filter(status='paid').count()
    
    # Preparing orders -> Orders in preparing status
    preparing_orders = Order.objects.filter(status='preparing').count()
    
    # Shipped orders -> Orders in shipped status
    shipped_orders = Order.objects.filter(status='shipped').count()
    
    # Total orders -> Paid+Preparing+Shipped+Delivered+Cancelled
    total_orders = Order.objects.filter(
        status__in=['paid', 'preparing', 'shipped', 'delivered', 'cancelled']
    ).count()
    
    # Cancelled orders
    cancelled_orders = Order.objects.filter(status='cancelled').count()
    
    # Returned orders -> Orders from ReturnRequest's completed status
    returned_orders = ReturnRequest.objects.filter(status='completed').count()
    
    # Old pending_orders (for backward compatibility)
    pending_orders = awaiting_orders + preparing_orders
    
    # Sales data for charts (last 30 days)
    today = timezone.now().date()
    thirty_days_ago = today - timedelta(days=30)
    
    # Daily sales (last 30 days)
    daily_sales = []
    dates = []
    for i in range(30):
        date = today - timedelta(days=29-i)
        sales = Order.objects.filter(
            created_at__date=date,
            status__in=['paid', 'approved', 'preparing', 'shipped', 'delivered']
        ).aggregate(total=Sum('total_price'))['total'] or 0
        daily_sales.append(float(sales))
        dates.append(date.strftime('%d/%m'))
    
    # Sales by status (count and total price)
    status_data = Order.objects.values('status').annotate(
        count=Count('id'),
        total=Sum('total_price')
    ).order_by('-count')
    
    status_labels = []
    status_counts = []
    status_totals = []
    for item in status_data:
        status_labels.append(dict(Order.STATUS_CHOICES).get(item['status'], item['status']))
        status_counts.append(item['count'])
        status_totals.append(float(item['total'] or 0))
    
    # Total revenue (paid+approved+preparing+shipped+delivered)
    total_revenue = Order.objects.filter(
        status__in=['paid', 'approved', 'preparing', 'shipped', 'delivered']
    ).aggregate(total=Sum('total_price'))['total'] or 0
    
    # Today's sales
    today_sales = Order.objects.filter(
        created_at__date=today,
        status__in=['paid', 'approved', 'preparing', 'shipped', 'delivered']
    ).aggregate(total=Sum('total_price'))['total'] or 0
    today_orders_count = Order.objects.filter(
        created_at__date=today,
        status__in=['paid', 'approved', 'preparing', 'shipped', 'delivered']
    ).count()
    
    # This week sales
    week_start = today - timedelta(days=today.weekday())
    week_sales = Order.objects.filter(
        created_at__date__gte=week_start,
        status__in=['paid', 'approved', 'preparing', 'shipped', 'delivered']
    ).aggregate(total=Sum('total_price'))['total'] or 0
    week_orders_count = Order.objects.filter(
        created_at__date__gte=week_start,
        status__in=['paid', 'approved', 'preparing', 'shipped', 'delivered']
    ).count()
    
    # This month sales
    month_start = today.replace(day=1)
    month_sales = Order.objects.filter(
        created_at__date__gte=month_start,
        status__in=['paid', 'approved', 'preparing', 'shipped', 'delivered']
    ).aggregate(total=Sum('total_price'))['total'] or 0
    month_orders_count = Order.objects.filter(
        created_at__date__gte=month_start,
        status__in=['paid', 'approved', 'preparing', 'shipped', 'delivered']
    ).count()
    
    # Average order value
    completed_orders = Order.objects.filter(
        status__in=['paid', 'approved', 'preparing', 'shipped', 'delivered']
    )
    avg_order_value = completed_orders.aggregate(avg=Avg('total_price'))['avg'] or 0
    top_products = OrderItem.objects.filter(
        order__created_at__gte=thirty_days_ago,
        order__status__in=['paid', 'approved', 'preparing', 'shipped', 'delivered']
    ).values('product__name').annotate(
        total_sold=SumFunc('quantity'),
        total_revenue=SumFunc(F('price') * F('quantity'))
    ).order_by('-total_sold')[:10]
    
    top_product_names = [item['product__name'] or 'Bilinmeyen Ürün' for item in top_products]
    top_product_sales = [item['total_sold'] for item in top_products]
    top_product_revenue = [float(item['total_revenue'] or 0) for item in top_products]
    
    # Order counts graph (last 30 days)
    daily_order_counts = []
    for i in range(30):
        date = today - timedelta(days=29-i)
        count = Order.objects.filter(
            created_at__date=date,
            status__in=['paid', 'approved', 'preparing', 'shipped', 'delivered']
        ).count()
        daily_order_counts.append(count)
    
    # Cancellation and return rates
    total_completed_orders = Order.objects.filter(
        status__in=['paid', 'approved', 'preparing', 'shipped', 'delivered', 'cancelled']
    ).count()
    cancellation_rate = (cancelled_orders / total_completed_orders * 100) if total_completed_orders > 0 else 0
    return_rate = (returned_orders / total_completed_orders * 100) if total_completed_orders > 0 else 0
    
    # Customer statistics
    total_customers = CustomUser.objects.filter(is_staff=False).count()
    new_customers_this_month = CustomUser.objects.filter(
        date_joined__gte=month_start,
        is_staff=False
    ).count()
    
    # Monthly revenue (last 6 months)
    monthly_revenue = []
    monthly_labels = []
    monthly_order_counts = []
    for i in range(6):
        month_start_calc = today.replace(day=1) - timedelta(days=30*i)
        month_end = (month_start_calc + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        revenue = Order.objects.filter(
            created_at__date__gte=month_start_calc,
            created_at__date__lte=month_end,
            status__in=['paid', 'approved', 'preparing', 'shipped', 'delivered']
        ).aggregate(total=Sum('total_price'))['total'] or 0
        order_count = Order.objects.filter(
            created_at__date__gte=month_start_calc,
            created_at__date__lte=month_end,
            status__in=['paid', 'approved', 'preparing', 'shipped', 'delivered']
        ).count()
        monthly_revenue.append(float(revenue))
        monthly_order_counts.append(order_count)
        monthly_labels.append(month_start_calc.strftime('%b %Y'))
    
    monthly_revenue.reverse()
    monthly_labels.reverse()
    monthly_order_counts.reverse()
    
    context = {
        'total_products': total_products,
        'pending_orders': pending_orders,
        'contact_messages': contact_messages,
        'total_revenue': total_revenue,
        'daily_sales': json.dumps(daily_sales),
        'daily_dates': json.dumps(dates),
        'status_labels': json.dumps(status_labels),
        'status_counts': json.dumps(status_counts),
        'status_totals': json.dumps(status_totals),
        'monthly_revenue': json.dumps(monthly_revenue),
        'monthly_labels': json.dumps(monthly_labels),
        # New detailed statistics
        'awaiting_orders': awaiting_orders,
        'preparing_orders': preparing_orders,
        'shipped_orders': shipped_orders,
        'total_orders': total_orders,
        'cancelled_orders': cancelled_orders,
        'returned_orders': returned_orders,
        # Advanced sales analysis
        'today_sales': today_sales,
        'today_orders_count': today_orders_count,
        'week_sales': week_sales,
        'week_orders_count': week_orders_count,
        'month_sales': month_sales,
        'month_orders_count': month_orders_count,
        'avg_order_value': avg_order_value,
        'top_product_names': json.dumps(top_product_names),
        'top_product_sales': json.dumps(top_product_sales),
        'top_product_revenue': json.dumps(top_product_revenue),
        'daily_order_counts': json.dumps(daily_order_counts),
        'cancellation_rate': cancellation_rate,
        'return_rate': return_rate,
        'total_customers': total_customers,
        'new_customers_this_month': new_customers_this_month,
        'monthly_order_counts': json.dumps(monthly_order_counts),
    }
    return render(request, 'management/admin-dashboard.html', context)

@user_passes_test(lambda u: u.is_staff)
def admin_product_list(request):
    products = Product.objects.select_related('category').all()
    
    # Search filter
    search_query = request.GET.get('q', '').strip()
    if search_query:
        search_filter = Q(name__icontains=search_query) | Q(description__icontains=search_query) | Q(category__name__icontains=search_query)
        # If SKU exists, add it
        if hasattr(Product, 'sku'):
            search_filter |= Q(sku__icontains=search_query)
        products = products.filter(search_filter).distinct()
    
    favorites = []
    if request.user.is_authenticated:
        favorites = Favorite.objects.filter(user=request.user).values_list('product_id', flat=True)
    
    return render(request, 'management/admin-product-list.html', {
        'products': products,
        'favorites': favorites,
        'search_query': search_query
    })

@csrf_protect
@user_passes_test(lambda u: u.is_staff)
def admin_product_add(request):
    from products.models import ProductVariant
    
    if request.method == 'POST':
        form = ProductForm(request.POST)
        formset = ProductImageFormSet(request.POST, request.FILES)
        
        # Check form validation errors
        if not form.is_valid():
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Form hatası ({field}): {error}")
        
        if not formset.is_valid():
            # Check formset's general errors
            if formset.non_form_errors():
                for error in formset.non_form_errors():
                    messages.error(request, f"Formset hatası: {error}")
            # Check each form's errors
            for i, form in enumerate(formset.forms):
                if form.errors:
                    for field, errors in form.errors.items():
                        for error in errors:
                            messages.error(request, f"Görsel {i+1} hatası ({field}): {error}")
        
        if form.is_valid() and formset.is_valid():
            product = form.save()  # First create the product
            formset.instance = product  # Attach the images to the product
            formset.save()  # Save the images (and the quality optimization method)
            
            # Debug: Check POST data (for variants)
            variant_keys = [k for k in request.POST.keys() if 'variant' in k.lower()]
            messages.info(request, f"POST'ta {len(variant_keys)} variant anahtarı bulundu: {variant_keys[:5]}...")
            
            # Save variants (only when creating a new product, there is a separate view for editing)
            if product.has_sizes or product.has_colors:
                # Add new variants - collect all variant IDs
                variant_ids = set()
                for key in request.POST.keys():
                    if key.startswith('new_variant_size_'):
                        # 'new_variant_size_new_1' -> 'new_1' extract
                        variant_id = key.replace('new_variant_size_', '')
                        variant_ids.add(variant_id)
                    elif key.startswith('new_variant_color_'):
                        variant_id = key.replace('new_variant_color_', '')
                        variant_ids.add(variant_id)
                    elif key.startswith('new_variant_stock_'):
                        variant_id = key.replace('new_variant_stock_', '')
                        variant_ids.add(variant_id)
                
                # For each variant ID, create a variant
                for variant_id in variant_ids:
                    size_key = f'new_variant_size_{variant_id}'
                    color_key = f'new_variant_color_{variant_id}'
                    stock_key = f'new_variant_stock_{variant_id}'
                    
                    size = request.POST.get(size_key, '').strip() or None
                    color = request.POST.get(color_key, '').strip() or None
                    stock = request.POST.get(stock_key, '0').strip()
                    
                    # If only size exists, check size, if only color exists, check color
                    should_create = False
                    if product.has_sizes and product.has_colors:
                        # Both size and color exist, both must be filled
                        should_create = size and color
                    elif product.has_sizes:
                        # Only size exists
                        should_create = bool(size)
                    elif product.has_colors:
                        # Only color exists
                        should_create = bool(color)
                    
                    if should_create:
                        try:
                            stock_int = int(stock) if stock else 0
                            # Use get_or_create to prevent duplicates
                            variant, created = ProductVariant.objects.get_or_create(
                                product=product,
                                size=size if product.has_sizes else None,
                                color=color if product.has_colors else None,
                                defaults={'stock': stock_int}
                            )
                            if not created:
                                # If variant already exists, update the stock
                                variant.stock = stock_int
                                variant.save()
                            messages.success(request, f"Variant kaydedildi: Beden={size or '-'}, Renk={color or '-'}, Stok={stock_int}")
                        except Exception as e:
                            messages.error(request, f"Variant kaydedilirken hata oluştu: {str(e)}")
                            import traceback
                            import sys
                            exc_type, exc_value, exc_traceback = sys.exc_info()
                            traceback.print_exception(exc_type, exc_value, exc_traceback, file=sys.stderr)
                    else:
                        # Debug for variants
                        messages.warning(request, f"Variant atlandı: Beden='{size or '-'}', Renk='{color or '-'}', has_sizes={product.has_sizes}, has_colors={product.has_colors}, should_create={should_create}")
            
            messages.success(request, f"{product.name} başarıyla eklendi.")
            return redirect('admin-product-list')
        else:
            # If form validation errors exist, show the form again
            messages.error(request, "Lütfen form hatalarını düzeltin.")
    else:
        form = ProductForm()
        formset = ProductImageFormSet()
        
    return render(request, 'management/admin-product-form.html', {
        'form': form, 
        'formset': formset, # Send formset to the template
        'title': 'Yeni Ürün Ekle',
    })

@csrf_protect
@user_passes_test(lambda u: u.is_staff)
def admin_product_edit(request, pk):
    from products.models import ProductVariant
    
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        # Form and Formset with the current 'product' instance
        form = ProductForm(request.POST, instance=product)
        formset = ProductImageFormSet(request.POST, request.FILES, instance=product)
        
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save() # Update existing images, remove deleted ones, add new ones
            
            # Update variants
            if product.has_sizes or product.has_colors:
                # Update or delete existing variants
                for variant in product.variants.all():
                    delete_key = f'delete_variant_{variant.id}'
                    size_key = f'variant_size_{variant.id}'
                    color_key = f'variant_color_{variant.id}'
                    stock_key = f'variant_stock_{variant.id}'
                    
                    if delete_key in request.POST:
                        variant.delete()
                    else:
                        size = request.POST.get(size_key, '').strip() or None
                        color = request.POST.get(color_key, '').strip() or None
                        stock = request.POST.get(stock_key, '0').strip()
                        
                        try:
                            stock_int = int(stock) if stock else 0
                            variant.size = size
                            variant.color = color
                            variant.stock = stock_int
                            variant.save()
                        except (ValueError, Exception):
                            pass
                
                # Add new variants - collect all variant IDs
                variant_ids = set()
                for key in request.POST.keys():
                    if key.startswith('new_variant_size_'):
                        variant_id = key.replace('new_variant_size_', '')
                        variant_ids.add(variant_id)
                    elif key.startswith('new_variant_color_'):
                        variant_id = key.replace('new_variant_color_', '')
                        variant_ids.add(variant_id)
                    elif key.startswith('new_variant_stock_'):
                        variant_id = key.replace('new_variant_stock_', '')
                        variant_ids.add(variant_id)
                
                # For each variant ID, create a variant
                for variant_id in variant_ids:
                    size_key = f'new_variant_size_{variant_id}'
                    color_key = f'new_variant_color_{variant_id}'
                    stock_key = f'new_variant_stock_{variant_id}'
                    
                    size = request.POST.get(size_key, '').strip() or None
                    color = request.POST.get(color_key, '').strip() or None
                    stock = request.POST.get(stock_key, '0').strip()
                    
                    # If only size exists, check size, if only color exists, check color
                    should_create = False
                    if product.has_sizes and product.has_colors:
                        should_create = size and color
                    elif product.has_sizes:
                        should_create = bool(size)
                    elif product.has_colors:
                        should_create = bool(color)
                    
                    if should_create:
                        try:
                            stock_int = int(stock) if stock else 0
                            variant, created = ProductVariant.objects.get_or_create(
                                product=product,
                                size=size if product.has_sizes else None,
                                color=color if product.has_colors else None,
                                defaults={'stock': stock_int}
                            )
                            if not created:
                                variant.stock = stock_int
                                variant.save()
                            messages.success(request, f"Variant kaydedildi: Beden={size or '-'}, Renk={color or '-'}, Stok={stock_int}")
                        except (ValueError, Exception) as e:
                            messages.error(request, f"Variant kaydedilirken hata oluştu: {str(e)}")
            else:
                # If variant options are closed, delete all variants
                product.variants.all().delete()
            
            messages.success(request, f"{product.name} başarıyla güncellendi.")
            return redirect('admin-product-list')
    else:
        # On GET request, fill the form with the current information
        form = ProductForm(instance=product)
        formset = ProductImageFormSet(instance=product)
    
    return render(request, 'management/admin-product-form.html', {
        'form': form, 
        'formset': formset, 
        'title': 'Ürünü Düzenle',
        'product': product # If needed, in the template, for the delete button etc.
    })

@csrf_protect
@user_passes_test(lambda u: u.is_staff)
def admin_product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        product.delete()
        return redirect('admin-product-list')
    return redirect('admin-product-list')

@user_passes_test(lambda u: u.is_staff)
def admin_order_list(request):
    # Filter orders in draft and awaiting payment status
    orders = Order.objects.prefetch_related('items__product', 'user').exclude(
        status__in=['draft', 'awaiting_payment']
    ).order_by('-created_at')
    status_choices = Order.STATUS_CHOICES
    return render(request, 'management/admin-order-list.html', {
        'orders': orders,
        'status_choices': status_choices,
    })

@csrf_protect
@user_passes_test(lambda u: u.is_staff)
def admin_order_update_ajax(request, pk):
    order = get_object_or_404(Order, pk=pk)
    if request.method == 'POST':
        form = OrderStatusForm(request.POST, instance=order)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'errors': form.errors})
    return JsonResponse({'success': False, 'error': 'Invalid request'})

def _get_user_name(order):
    """Kullanıcı adını güvenli şekilde al"""
    if order.user:
        return format_html("{}", order.user.get_full_name() or order.user.email)
    return "Değerli Müşterimiz"

def _get_user_name_from_return(return_request):
    """İade talebinden kullanıcı adını güvenli şekilde al"""
    if return_request.user:
        return format_html("{}", return_request.user.get_full_name() or return_request.user.email)
    return "Değerli Müşterimiz"

TEMPLATE_MESSAGES = {
    'return_approved': {
        'subject': f'İade Talebiniz Onaylandı | {settings.STORE_NAME}',
        'message': lambda return_request, mng_code=None: mark_safe(
            f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f9f9f9;">
                <div style="background: linear-gradient(135deg, #27ae60, #229954); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                    <h1 style="color: white; margin: 0; font-size: 24px;">✅ İade Talebiniz Onaylandı</h1>
                </div>
                <div style="background: white; padding: 30px; border-radius: 0 0 10px 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                    <p style="color: #333; font-size: 16px; line-height: 1.6;">Merhaba <strong>{_get_user_name_from_return(return_request)}</strong>,</p>
                    <p style="color: #555; font-size: 15px; line-height: 1.6;">
                        <strong>#{return_request.id}</strong> numaralı iade talebiniz onaylanmıştır. Ürününüzü MNG Kargo ile gönderebilirsiniz.
                    </p>
                    <div style="background: #e8f8f5; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #27ae60;">
                        <p style="margin: 0 0 15px 0; color: #555; font-size: 14px;">
                            <strong>İade Bilgileri:</strong><br>
                            İade Talebi No: <strong>#{return_request.id}</strong><br>
                            Sipariş No: <strong>#{return_request.order.id}</strong><br>
                            Ürün: <strong>{return_request.order_item.product.name}</strong><br>
                            Miktar: <strong>{return_request.quantity} Adet</strong>
                        </p>
                    </div>
                    {f'''
                    <div style="background: #fff4e6; padding: 20px; border-radius: 8px; margin: 20px 0; border: 2px solid #f39c12; text-align: center;">
                        <p style="margin: 0 0 10px 0; color: #333; font-size: 14px; font-weight: 600;">
                            📦 MNG KARGO İADE KODU
                        </p>
                        <p style="margin: 0; color: #e67e22; font-size: 24px; font-weight: 700; letter-spacing: 2px; font-family: 'Courier New', monospace;">
                            {mng_code if mng_code else 'KOD GİRİLMEMİŞ'}
                        </p>
                        <p style="margin: 15px 0 0 0; color: #555; font-size: 12px;">
                            Bu kodu MNG Kargo şubesine vererek ürününüzü gönderebilirsiniz.
                        </p>
                    </div>
                    ''' if mng_code else '<div style="background: #fff4e6; padding: 20px; border-radius: 8px; margin: 20px 0; border: 2px solid #f39c12; text-align: center;"><p style="margin: 0; color: #e67e22; font-size: 18px; font-weight: 700;">MNG Kargo iade kodu yönetici tarafından eklenecektir.</p></div>'}
                    <div style="background: #f0f8ff; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #3498db;">
                        <p style="margin: 0; color: #555; font-size: 14px; line-height: 1.8;">
                            <strong>İade İşlemi Adımları:</strong><br>
                            1. Ürünü orijinal kutusu ve ambalajı ile birlikte hazırlayın<br>
                            2. MNG Kargo şubesine gidin ve iade kodunu verin<br>
                            3. Kargo ücreti tarafımıza aittir<br>
                            4. Ürün bize ulaştığında inceleme yapılacak ve iade işlemi tamamlanacaktır
                        </p>
                    </div>
                    <p style="color: #555; font-size: 14px; line-height: 1.6;">
                        İade sürecinizi <a href="f"{settings.APP_BASE_URL}/profile#iadelerim" style="color: #27ae60; text-decoration: none; font-weight: bold;">profil sayfanızdan</a> takip edebilirsiniz.
                    </p>
                    <p style="color: #888; font-size: 13px; margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee;">
                        Sorularınız için <a href="f"{settings.APP_BASE_URL}/iletisim" style="color: #27ae60; text-decoration: none;">iletişim</a> sayfamızdan bize ulaşabilirsiniz.<br>
                        <strong>{settings.STORE_NAME}</strong> - {settings.STORE_SLOGAN}
                    </p>
                </div>
            </div>
            """
        )
    },
    'approved': {
        'subject': f'Siparişiniz Onaylandı | {settings.STORE_NAME}',
        'message': lambda order: mark_safe(
            f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f9f9f9;">
                <div style="background: linear-gradient(135deg, #8e68ab, #69b3a2); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                    <h1 style="color: white; margin: 0; font-size: 24px;">Siparişiniz Onaylandı</h1>
                </div>
                <div style="background: white; padding: 30px; border-radius: 0 0 10px 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                    <p style="color: #333; font-size: 16px; line-height: 1.6;">Merhaba <strong>{_get_user_name(order)}</strong>,</p>
                    <p style="color: #555; font-size: 15px; line-height: 1.6;">
                        <strong>#{order.id}</strong> numaralı siparişiniz başarıyla onaylanmıştır. Siparişiniz en kısa sürede hazırlanmaya başlayacaktır.
                    </p>
                    <div style="background: #f0f8ff; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #8e68ab;">
                        <p style="margin: 0; color: #555; font-size: 14px;">
                            <strong>Sipariş Detayları:</strong><br>
                            Sipariş No: <strong>#{order.id}</strong><br>
                            Toplam Tutar: <strong>{order.total_price} ₺</strong>
                        </p>
                    </div>
                    <p style="color: #555; font-size: 14px; line-height: 1.6;">
                        Siparişinizin durumunu takip etmek için <a href="f"{settings.APP_BASE_URL}/profile" style="color: #8e68ab; text-decoration: none; font-weight: bold;">profil sayfanızdan</a> kontrol edebilirsiniz.
                    </p>
                    <p style="color: #888; font-size: 13px; margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee;">
                        Sorularınız için bizimle iletişime geçebilirsiniz.<br>
                        <strong>{settings.STORE_NAME}</strong> - {settings.STORE_SLOGAN}
                    </p>
                </div>
            </div>
            """
        )
    },
    'preparing': {
        'subject': f'Siparişiniz Hazırlanıyor | {settings.STORE_NAME}',
        'message': lambda order: mark_safe(
            f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f9f9f9;">
                <div style="background: linear-gradient(135deg, #f39c12, #e67e22); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                    <h1 style="color: white; margin: 0; font-size: 24px;">Siparişiniz Hazırlanıyor</h1>
                </div>
                <div style="background: white; padding: 30px; border-radius: 0 0 10px 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                    <p style="color: #333; font-size: 16px; line-height: 1.6;">Merhaba <strong>{_get_user_name(order)}</strong>,</p>
                    <p style="color: #555; font-size: 15px; line-height: 1.6;">
                        <strong>#{order.id}</strong> numaralı siparişiniz şu an hazırlanmaktadır. Ürünleriniz özenle paketleniyor.
                    </p>
                    <div style="background: #fff4e6; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #f39c12;">
                        <p style="margin: 0; color: #555; font-size: 14px;">
                            <strong>Sipariş Bilgileri:</strong><br>
                            Sipariş No: <strong>#{order.id}</strong><br>
                            Toplam Tutar: <strong>{order.total_price} ₺</strong>
                        </p>
                    </div>
                    <p style="color: #555; font-size: 14px; line-height: 1.6;">
                        Siparişiniz hazır olduğunda size bilgi vereceğiz. Sipariş durumunuzu <a href="f"{settings.APP_BASE_URL}/profile" style="color: #f39c12; text-decoration: none; font-weight: bold;">profil sayfanızdan</a> takip edebilirsiniz.
                    </p>
                    <p style="color: #888; font-size: 13px; margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee;">
                        Sorularınız için bizimle iletişime geçebilirsiniz.<br>
                        <strong>{settings.STORE_NAME}</strong> - {settings.STORE_SLOGAN}
                    </p>
                </div>
            </div>
            """
        )
    },
    'shipped': {
        'subject': f'Siparişiniz Kargoya Verildi | {settings.STORE_NAME}',
        'message': lambda order: mark_safe(
            f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f9f9f9;">
                <div style="background: linear-gradient(135deg, #3498db, #2980b9); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                    <h1 style="color: white; margin: 0; font-size: 24px;">🚚 Kargonuz Yola Çıktı</h1>
                </div>
                <div style="background: white; padding: 30px; border-radius: 0 0 10px 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                    <p style="color: #333; font-size: 16px; line-height: 1.6;">Merhaba <strong>{_get_user_name(order)}</strong>,</p>
                    <p style="color: #555; font-size: 15px; line-height: 1.6;">
                        <strong>#{order.id}</strong> numaralı siparişiniz kargoya verilmiştir. Paketiniz yola çıkmıştır!
                    </p>
                    <div style="background: #e8f4f8; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #3498db;">
                        <p style="margin: 0; color: #555; font-size: 14px;">
                            <strong>Teslimat Bilgileri:</strong><br>
                            Sipariş No: <strong>#{order.id}</strong><br>
                            Teslimat Adresi: <strong>{order.shipping_district}, {order.shipping_city}</strong><br>
                            Toplam Tutar: <strong>{order.total_price} ₺</strong>
                        </p>
                    </div>
                    <p style="color: #555; font-size: 14px; line-height: 1.6;">
                        Kargo takip bilgilerinizi <a href="f"{settings.APP_BASE_URL}/profile" style="color: #3498db; text-decoration: none; font-weight: bold;">profil sayfanızdan</a> görüntüleyebilirsiniz.
                    </p>
                    <p style="color: #888; font-size: 13px; margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee;">
                        Sorularınız için bizimle iletişime geçebilirsiniz.<br>
                        <strong>{settings.STORE_NAME}</strong> - {settings.STORE_SLOGAN}
                    </p>
                </div>
            </div>
            """
        )
    },
    'delivered': {
        'subject': f'Siparişiniz Teslim Edildi | {settings.STORE_NAME}',
        'message': lambda order: mark_safe(
            f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f9f9f9;">
                <div style="background: linear-gradient(135deg, #27ae60, #229954); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                    <h1 style="color: white; margin: 0; font-size: 24px;">✅ Teslimat Tamamlandı</h1>
                </div>
                <div style="background: white; padding: 30px; border-radius: 0 0 10px 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                    <p style="color: #333; font-size: 16px; line-height: 1.6;">Merhaba <strong>{_get_user_name(order)}</strong>,</p>
                    <p style="color: #555; font-size: 15px; line-height: 1.6;">
                        <strong>#{order.id}</strong> numaralı siparişiniz başarıyla teslim edilmiştir. Ürünlerinizi beğenmenizi umuyoruz!
                    </p>
                    <div style="background: #e8f8f5; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #27ae60;">
                        <p style="margin: 0; color: #555; font-size: 14px;">
                            <strong>Sipariş Özeti:</strong><br>
                            Sipariş No: <strong>#{order.id}</strong><br>
                            Toplam Tutar: <strong>{order.total_price} ₺</strong>
                        </p>
                    </div>
                    <p style="color: #555; font-size: 14px; line-height: 1.6;">
                        Ürünlerimiz hakkında görüşlerinizi bizimle paylaşmak ister misiniz? <a href="f"{settings.APP_BASE_URL}/profile" style="color: #27ae60; text-decoration: none; font-weight: bold;">Profil sayfanızdan</a> değerlendirme yapabilirsiniz.
                    </p>
                    <p style="color: #888; font-size: 13px; margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee;">
                        Tekrar görüşmek üzere!<br>
                        <strong>{settings.STORE_NAME}</strong> - {settings.STORE_SLOGAN}
                    </p>
                </div>
            </div>
            """
        )
    },
    'cancelled': {
        'subject': f'Siparişiniz İptal Edildi | {settings.STORE_NAME}',
        'message': lambda order: mark_safe(
            f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f9f9f9;">
                <div style="background: linear-gradient(135deg, #e74c3c, #c0392b); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                    <h1 style="color: white; margin: 0; font-size: 24px;">Siparişiniz İptal Edildi</h1>
                </div>
                <div style="background: white; padding: 30px; border-radius: 0 0 10px 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                    <p style="color: #333; font-size: 16px; line-height: 1.6;">Merhaba <strong>{_get_user_name(order)}</strong>,</p>
                    <p style="color: #555; font-size: 15px; line-height: 1.6;">
                        <strong>#{order.id}</strong> numaralı siparişiniz iptal edilmiştir.
                    </p>
                    <div style="background: #fdeaea; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #e74c3c;">
                        <p style="margin: 0; color: #555; font-size: 14px;">
                            <strong>İptal Edilen Sipariş:</strong><br>
                            Sipariş No: <strong>#{order.id}</strong><br>
                            {f'İptal Sebebi: <strong>{order.cancellation_reason}</strong><br>' if hasattr(order, 'cancellation_reason') and order.cancellation_reason else ''}
                            Toplam Tutar: <strong>{order.total_price} ₺</strong>
                        </p>
                    </div>
                    <p style="color: #555; font-size: 14px; line-height: 1.6;">
                        Ödeme yaptıysanız, tutar en geç 3-5 iş günü içinde hesabınıza iade edilecektir. Sorularınız için <a href="f"{settings.APP_BASE_URL}/iletisim" style="color: #e74c3c; text-decoration: none; font-weight: bold;">iletişim</a> sayfamızdan bize ulaşabilirsiniz.
                    </p>
                    <p style="color: #888; font-size: 13px; margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee;">
                        Üzgünüz, bu durumdan dolayı rahatsızlık verdiyseniz özür dileriz.<br>
                        <strong>{settings.STORE_NAME}</strong> - {settings.STORE_SLOGAN}
                    </p>
                </div>
            </div>
            """
        )
    },
}

@csrf_protect
@user_passes_test(lambda u: u.is_staff)
def admin_send_mail(request):
    # Filter orders in draft and awaiting payment status
    orders = Order.objects.select_related('user').exclude(
        status__in=['draft', 'awaiting_payment']
    ).order_by('-created_at')
    
    # Return requests (for return template - approved or received status)
    return_requests = ReturnRequest.objects.filter(
        status__in=['approved', 'received']
    ).select_related('order', 'order_item__product', 'user').order_by('-created_at')
    
    if request.method == 'POST':
        order_id = request.POST.get('order')
        template_key = request.POST.get('template')
        subject = request.POST.get('subject')
        message = request.POST.get('message')
        
        # For return template, order_id is not required, return_request_id is required
        if template_key == 'return_approved':
            return_request_id = request.POST.get('return_request_id')
            if not return_request_id:
                messages.error(request, "İade template'i için lütfen bir iade talebi seçiniz.")
                return render(request, 'management/admin-send-mail.html', {
                    'orders': orders, 
                    'return_requests': return_requests,
                    'title': 'Müşteriye Mail Gönder'
                })
            return_request = get_object_or_404(ReturnRequest, pk=return_request_id)
            order = return_request.order
        else:
            if not order_id:
                messages.error(request, "Lütfen bir sipariş seçiniz.")
                return render(request, 'management/admin-send-mail.html', {
                    'orders': orders, 
                    'return_requests': return_requests,
                    'title': 'Müşteriye Mail Gönder'
                })
            order = get_object_or_404(Order, pk=order_id)
        
        # Determine the email recipient
        if not order.user:
            messages.error(request, "Bu siparişe ait kullanıcı bulunamadı.")
            return render(request, 'management/admin-send-mail.html', {
        'orders': orders, 
        'return_requests': return_requests,
        'title': 'Müşteriye Mail Gönder'
    })
        
        recipient = order.user.email
        
        # Create the message
        # If template is selected, get the HTML from the template (not the message in the textarea)
        if template_key and template_key in TEMPLATE_MESSAGES:
            # Special processing for return template
            if template_key == 'return_approved':
                return_request_id = request.POST.get('return_request_id')
                mng_code = request.POST.get('mng_code', '').strip()
                
                if not return_request_id:
                    messages.error(request, "İade template'i için lütfen bir iade talebi seçiniz.")
                    return render(request, 'management/admin-send-mail.html', {
                        'orders': orders, 
                        'return_requests': return_requests,
                        'title': 'Müşteriye Mail Gönder'
                    })
                
                return_request = get_object_or_404(ReturnRequest, pk=return_request_id)
                order = return_request.order
                message_html = TEMPLATE_MESSAGES[template_key]['message'](return_request, mng_code)
            else:
                # For other templates, use order
                message_html = TEMPLATE_MESSAGES[template_key]['message'](order)
            # Convert from mark_safe to string
            message_html = str(message_html)
        elif message:
            # If manual message exists, convert to HTML format
            message_html = format_html(
                "<div style='font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f9f9f9;'>"
                "<div style='background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);'>"
                "<p style='color: #333; font-size: 16px; line-height: 1.6; white-space: pre-wrap;'>{}</p>"
                "</div></div>",
                message.replace("\n", "<br>")
            )
            message_html = str(message_html)
        else:
            messages.error(request, "Lütfen bir mesaj giriniz veya şablon seçiniz.")
            return render(request, 'management/admin-send-mail.html', {
                'orders': orders, 
                'return_requests': return_requests,
                'title': 'Müşteriye Mail Gönder'
            })
        
        if not subject:
            # Get subject from template
            if template_key and template_key in TEMPLATE_MESSAGES:
                subject = TEMPLATE_MESSAGES[template_key]['subject']
            else:
                messages.error(request, "Lütfen e-posta konusu giriniz.")
                return render(request, 'management/admin-send-mail.html', {
                    'orders': orders, 
                    'return_requests': return_requests,
                    'title': 'Müşteriye Mail Gönder'
                })
        
        # Create email
        email = EmailMultiAlternatives(
            subject=subject,
            body=strip_tags(message_html),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient]
        )
        email.attach_alternative(message_html, "text/html")
        
        # Add attachment (if exists)
        if 'attachment' in request.FILES:
            attachment = request.FILES['attachment']
            email.attach(attachment.name, attachment.read(), attachment.content_type)
        
        try:
            email.send()
            messages.success(request, f"E-posta başarıyla gönderildi: {recipient}")
        except Exception as e:
            messages.error(request, f"E-posta gönderilirken hata oluştu: {str(e)}")
        
        return redirect('admin-send-mail')
    
    return render(request, 'management/admin-send-mail.html', {
        'orders': orders, 
        'return_requests': return_requests,
        'title': 'Müşteriye Mail Gönder'
    })

@user_passes_test(lambda u: u.is_staff)
def admin_order_settings(request):
    """
    Sipariş ayarlarını (kargo ücreti, ücretsiz kargo limiti) düzenleme sayfası
    """
    # OrderSetting singleton - get the first record or create it
    order_setting = OrderSetting.objects.first()
    if not order_setting:
        order_setting = OrderSetting.objects.create()
    
    if request.method == 'POST':
        shipping_fee = request.POST.get('shipping_fee', '').strip()
        free_shipping_limit = request.POST.get('free_shipping_limit', '').strip()
        
        # Validation
        try:
            shipping_fee_decimal = Decimal(shipping_fee)
            free_shipping_limit_decimal = Decimal(free_shipping_limit)
            
            if shipping_fee_decimal < 0 or free_shipping_limit_decimal < 0:
                messages.error(request, "Kargo ücreti ve ücretsiz kargo limiti negatif olamaz.")
                return render(request, 'management/admin-order-settings.html', {
                    'order_setting': order_setting,
                    'title': 'Sipariş Ayarları'
                })
            
            # Update
            order_setting.shipping_fee = shipping_fee_decimal
            order_setting.free_shipping_limit = free_shipping_limit_decimal
            order_setting.save()
            
            messages.success(request, "Sipariş ayarları başarıyla güncellendi.")
            return redirect('admin-order-settings')
            
        except (ValueError, InvalidOperation) as e:
            messages.error(request, f"Geçersiz değer: {str(e)}")
    
    return render(request, 'management/admin-order-settings.html', {
        'order_setting': order_setting,
        'title': 'Sipariş Ayarları'
    })

@user_passes_test(lambda u: u.is_staff)
def get_mail_template(request):
    template_key = request.GET.get('key')
    order_id = request.GET.get('order_id')
    
    if not template_key or not order_id:
        return JsonResponse({"error": "Eksik parametre."}, status=400)
    
    order = get_object_or_404(Order, id=order_id)
    
    if template_key in TEMPLATE_MESSAGES:
        template = TEMPLATE_MESSAGES[template_key]
        subject = template["subject"]
        message_html = template["message"](order)
        # Convert HTML to plain text (for textarea)
        message_text = strip_tags(message_html)
        data = {
            "subject": subject,
            "message": message_text  # Plain text for textarea
        }
        return JsonResponse(data)
    
    return JsonResponse({"error": "Geçersiz şablon."}, status=400)

def order_tracking(request):
    orders = []
    if request.user.is_authenticated:
        # Filter orders in draft and awaiting payment status
        orders = Order.objects.filter(user=request.user).exclude(
            status__in=['draft', 'awaiting_payment']
        ).prefetch_related('items__product').order_by('-created_at')
        ratings = ProductRating.objects.filter(user=request.user).select_related('product')
        ratings_dict = {rating.product_id: rating for rating in ratings}
        for order in orders:
            for item in order.items.all():
                item.user_rating = ratings_dict.get(item.product_id)
    return render(request, 'pages/order-tracking.html', {'orders': orders})

@user_passes_test(lambda u: u.is_staff)
def admin_contact_requests(request):
    contact_messages = ContactMessage.objects.all().order_by('-created_at')
    return render(request, "management/admin-contact-requests.html", {
        "contact_messages": contact_messages
    })

@user_passes_test(lambda u: u.is_staff)
def admin_contact_detail(request, pk):
    contact_message = get_object_or_404(ContactMessage, pk=pk)

    if not contact_message.is_read:
        contact_message.is_read = True
        contact_message.save(update_fields=["is_read"])

    return JsonResponse({
        "name": contact_message.name,
        "email": contact_message.email,
        "phone": contact_message.phone or "-",
        "subject": contact_message.subject,
        "message": contact_message.message,
        "created_at": contact_message.created_at.strftime("%d %B %Y %H:%M"),
    })

def return_requests(request):
    """İade talepleri sayfası - orders/views.py'deki return_request_list'i kullan"""
    from orders.views import return_request_list
    return return_request_list(request)

def payment_options(request):
    return render(request, 'pages/payment-options.html')

def campaigns(request):
    products = Product.objects.filter(is_active=True, bulk_discounts__isnull=False).distinct()
    favorites = []
    if request.user.is_authenticated:
        favorites = Favorite.objects.filter(user=request.user).values_list('product_id', flat=True)
    return render(request, 'pages/campaigns.html', {'products': products, 'favorites': favorites})

def contact(request):
    if request.method == "POST":
        ContactMessage.objects.create(
            name=request.POST.get("name"),
            email=request.POST.get("email"),
            phone=request.POST.get("phone", ""),
            subject=request.POST.get("subject"),
            message=request.POST.get("message"),
        )

        messages.success(
            request,
            "Mesajınız başarıyla iletildi. En kısa sürede dönüş yapacağız."
        )
        return redirect("contact")

    return render(request, "pages/contact.html")

def warranty_and_returns(request):
    return render(request, 'pages/warranty-and-returns.html')

def privacy_policy(request):
    return render(request, 'pages/privacy-policy.html')

def security_policy(request):
    return render(request, 'pages/security-policy.html')

def about_us(request):
    return render(request, 'pages/about-us.html')

def vision_mission(request):
    return render(request, 'pages/vision-mission.html')

def new_privacy_policy(request):
    return render(request, 'pages/new-privacy-policy.html')

@csrf_protect
@login_required
@require_http_methods(["POST"])
def submit_rating(request, product_slug):
    product = get_object_or_404(Product, slug=product_slug)
    delivered_orders = Order.objects.filter(user=request.user, status='delivered')
    has_delivered_order = OrderItem.objects.filter(order__in=delivered_orders, product=product).exists()
    if not has_delivered_order:
        return JsonResponse({'success': False, 'error': 'Bu ürünü değerlendirmek için önce teslim almalısınız.'}, status=403)
    rating_value = request.POST.get('rating')
    review_text = request.POST.get('review', '').strip()
    try:
        rating_value = int(rating_value)
        if rating_value < 1 or rating_value > 5:
            return JsonResponse({'success': False, 'error': 'Geçersiz rating'}, status=400)
    except:
        return JsonResponse({'success': False, 'error': 'Rating sayı olmalı'}, status=400)
    rating, created = ProductRating.objects.get_or_create(user=request.user, product=product, defaults={'rating': rating_value, 'review': review_text})
    if not created:
        rating.rating = rating_value
        if review_text: rating.review = review_text
        rating.save()
    return JsonResponse({'success': True, 'average_rating': product.get_average_rating(), 'rating_count': product.get_rating_count()})

@csrf_protect
@login_required
@require_http_methods(["POST"])
def delete_rating(request, product_slug):
    product = get_object_or_404(Product, slug=product_slug)
    try:
        rating = ProductRating.objects.get(user=request.user, product=product)
        rating.delete()
        return JsonResponse({'success': True, 'average_rating': product.get_average_rating(), 'rating_count': product.get_rating_count()})
    except ProductRating.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Rating bulunamadı'}, status=404)

def pre_information_text(request):
    return render(request, 'pages/pre-information-text.html')

def distance_sales_contract_text(request):
    return render(request, 'pages/distance-sales-contract-text.html')

def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug)
    products = Product.objects.filter(category=category, is_active=True)
    favorites = []
    if request.user.is_authenticated:
        favorites = Favorite.objects.filter(user=request.user).values_list('product_id', flat=True)
    return render(request, 'categories/category-template.html', {'title': category.name, 'category': category, 'products': products, 'favorites': favorites})

@user_passes_test(lambda u: u.is_staff)
def admin_home_images(request):
    slides = HomeSlide.objects.all().order_by('order')
    return render(request, 'management/admin-home-images.html', {'slides': slides})

@user_passes_test(lambda u: u.is_staff)
def admin_slide_add(request):
    if request.method == 'POST':
        form = HomeSlideForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Slide başarıyla eklendi.")
            return redirect('admin-home-images')
    else:
        form = HomeSlideForm()
    return render(request, 'management/admin-slide-form.html', {'form': form, 'title': 'Yeni Slide Ekle'})

@user_passes_test(lambda u: u.is_staff)
def admin_slide_edit(request, pk):
    slide = get_object_or_404(HomeSlide, pk=pk)
    if request.method == 'POST':
        # 'instance=slide' parameter allows us to update the current data
        form = HomeSlideForm(request.POST, request.FILES, instance=slide)
        if form.is_valid():
            form.save()
            messages.success(request, "Slide başarıyla güncellendi.")
            return redirect('admin-home-images')
    else:
        form = HomeSlideForm(instance=slide)
    
    return render(request, 'management/admin-slide-form.html', {
        'form': form, 
        'title': 'Slide Düzenle',
        'slide': slide
    })

@user_passes_test(lambda u: u.is_staff)
def admin_slide_delete(request, pk):
    slide = get_object_or_404(HomeSlide, pk=pk)
    slide.delete()
    messages.success(request, "Slide silindi.")
    return redirect('admin-home-images')

# Campaign management views
@user_passes_test(lambda u: u.is_staff)
def admin_campaign_list(request):
    campaigns = BulkDiscount.objects.select_related('product').all().order_by('-id')
    return render(request, 'management/admin-campaign-list.html', {'campaigns': campaigns})

@user_passes_test(lambda u: u.is_staff)
def admin_campaign_add(request):
    if request.method == 'POST':
        form = BulkDiscountForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Kampanya başarıyla eklendi.")
            return redirect('admin-campaign-list')
    else:
        form = BulkDiscountForm()
    return render(request, 'management/admin-campaign-form.html', {
        'form': form,
        'title': 'Yeni Kampanya Ekle'
    })

@user_passes_test(lambda u: u.is_staff)
def admin_campaign_edit(request, pk):
    campaign = get_object_or_404(BulkDiscount, pk=pk)
    if request.method == 'POST':
        form = BulkDiscountForm(request.POST, instance=campaign)
        if form.is_valid():
            form.save()
            messages.success(request, "Kampanya başarıyla güncellendi.")
            return redirect('admin-campaign-list')
    else:
        form = BulkDiscountForm(instance=campaign)
    return render(request, 'management/admin-campaign-form.html', {
        'form': form,
        'title': 'Kampanya Düzenle',
        'campaign': campaign
    })

@user_passes_test(lambda u: u.is_staff)
def admin_campaign_delete(request, pk):
    campaign = get_object_or_404(BulkDiscount, pk=pk)
    campaign.delete()
    messages.success(request, "Kampanya silindi.")
    return redirect('admin-campaign-list')