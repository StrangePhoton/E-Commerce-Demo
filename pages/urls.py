from django.urls import path
from . import views
from django.contrib.auth.views import LogoutView
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy

urlpatterns = [
    path('', views.home, name='home'),
    path('arama/', views.search_results, name='search-results'),
    path('kategori/<int:category_id>/', views.category_products, name='category_products'),
    path('hasta-bakim-malzemeleri/', views.hasta_bakim_malzemeleri, name='hasta-bakim-malzemeleri'),
    path('medikal-sarf-malzemeleri/', views.medikal_sarf_malzemeleri, name='medikal-sarf-malzemeleri'),
    path('medikal-malzemeler/', views.medikal_malzemeler, name='medikal-malzemeler'),
    path('kisisel-yasam-malzemeleri/', views.kisisel_yasam_malzemeleri, name='kisisel-yasam-malzemeleri'),
    path('vitamin-ve-takviyeler/', views.vitamin_ve_takviyeler, name='vitamin-ve-takviyeler'),
    path('ev-ve-yasam/', views.ev_ve_yasam, name='ev-ve-yasam'),
    path('elektronik-cihazlar/', views.elektronik_cihazlar, name='elektronik-cihazlar'),
    path('cok-satanlar/', views.best_sellers, name='cok-satanlar'),
    path('yeni-urunler/', views.new_arrivals, name='yeni-urunler'),
    path('kampanyalar/',views.campaigns, name='kampanyalar'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path("activate/<uidb64>/<token>/", views.activate_account, name="activate-account"),
    path("resend-activation/", views.resend_activation_mail, name="resend-activation"),
    path('profile/', views.profile_view, name='profile'),
    path('logout/', LogoutView.as_view(next_page='home'), name='logout'),
    path('password_reset/', 
    auth_views.PasswordResetView.as_view(
        template_name='accounts/password_reset.html',
        email_template_name='accounts/password_reset_email.html',
        subject_template_name='accounts/password_reset_subject.txt',
        success_url=reverse_lazy('password_reset_done') # Redirect with name
    ),
    name='password_reset'
    ),
    path('password_reset/done/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='accounts/password_reset_done.html'
        ),
        name='password_reset_done'
    ),
    path('reset/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='accounts/password_reset_confirm.html'
        ),
        name='password_reset_confirm'
    ),
    path('reset/done/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='accounts/password_reset_complete.html'
        ),
        name='password_reset_complete'
    ),
    path('yonetim/', views.admin_dashboard, name='admin-dashboard'),
    path('yonetim/urunler/', views.admin_product_list, name='admin-product-list'),
    path('yonetim/urun-ekle/', views.admin_product_add, name='admin-product-add'),
    path('yonetim/urun-duzenle/<int:pk>/', views.admin_product_edit, name='admin-product-edit'),
    path('yonetim/urun-sil/<int:pk>/', views.admin_product_delete, name='admin-product-delete'),
    path('yonetim/kampanyalar/', views.admin_campaign_list, name='admin-campaign-list'),
    path('yonetim/kampanya-ekle/', views.admin_campaign_add, name='admin-campaign-add'),
    path('yonetim/kampanya-duzenle/<int:pk>/', views.admin_campaign_edit, name='admin-campaign-edit'),
    path('yonetim/kampanya-sil/<int:pk>/', views.admin_campaign_delete, name='admin-campaign-delete'),
    path('yonetim/siparisler/', views.admin_order_list, name='admin-order-list'),
    path('yonetim/siparis-ayarlari/', views.admin_order_settings, name='admin-order-settings'),
    path('yonetim/mail/', views.admin_send_mail, name='admin-send-mail'),
    path('yonetim/sablon/', views.get_mail_template, name='get-mail-template'),
    path('yonetim/mesajlar/',views.admin_contact_requests, name='admin-contact-requests'),
    path('yonetim/mesaj-oku/<int:pk>/',views.admin_contact_detail,name='admin-contact-detail'),
    path('urun/<slug:slug>/', views.product_detail, name='product_detail'),
    path('api/product-stock/<int:product_id>/', views.product_stock_api, name='product-stock-api'),
    path('yonetim/siparis/<int:pk>/guncelle/ajax/', views.admin_order_update_ajax, name='admin-order-update-ajax'),
    
    # Footer Pages
    path('siparis-takibi/', views.order_tracking, name='order-tracking'),
    path('iade-talepleri/', views.return_requests, name='return-requests'),
    path('odeme-secenekleri/', views.payment_options, name='payment-options'),
    path('kampanyalar/', views.campaigns, name='campaigns'),
    path('iletisim/', views.contact, name='contact'),
    path('garanti-ve-iade/', views.warranty_and_returns, name='warranty-and-returns'),
    path('kisisel-verilerin-korunmasi/', views.privacy_policy, name='privacy-policy'),
    path('bilgi-guvenligi-politikasi/', views.security_policy, name='security-policy'),
    path('hakkimizda/', views.about_us, name='about-us'),
    path('vizyon-ve-misyon/', views.vision_mission, name='vision-mission'),
    path('gizlilik-politikası/', views.new_privacy_policy, name='new-privacy-policy'),
    
    # Rating URLs
    path('urun/<slug:product_slug>/rating/', views.submit_rating, name='submit-rating'),
    path('urun/<slug:product_slug>/rating/sil/', views.delete_rating, name='delete-rating'),
    
    # Pages
    path('pre-information-text/', views.pre_information_text, name='pre-information-text'),
    path('distance-sales-contract-text/', views.distance_sales_contract_text, name='distance-sales-contract-text'),
    path('kategori/<slug:slug>/', views.category_detail, name='category-detail'),

    # Admin URLs
    path('yonetim/ana-sayfa-gorselleri/', views.admin_home_images, name='admin-home-images'),
    path('yonetim/ana-sayfa-gorselleri/yeni/', views.admin_slide_add, name='admin-slide-add'),
    path('yonetim/ana-sayfa-gorselleri/duzenle/<int:pk>/', views.admin_slide_edit, name='admin-slide-edit'),
    path('yonetim/ana-sayfa-gorselleri/sil/<int:pk>/', views.admin_slide_delete, name='admin-slide-delete'),
]