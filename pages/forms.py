from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from django.utils import timezone
from orders.models import Order
from products.models import Product, ProductImage, BulkDiscount
from users.models import CustomUser, Address
from django.forms.models import inlineformset_factory
from .models import HomeSlide
import re

class SignUpForm(UserCreationForm):
    email = forms.EmailField(max_length=254, required=True, label="E-posta Adresi")
    first_name = forms.CharField(max_length=30, required=True, label="Ad")
    last_name = forms.CharField(max_length=30, required=True, label="Soyad")
    tc_kimlik_no = forms.CharField(
        max_length=11,
        required=True,
        label="T.C. Kimlik Numarası"
    )
    birth_date = forms.DateField(required=True, widget=forms.DateInput(attrs={'type': 'date'}), label="Doğum Tarihi")
    phone_number = forms.CharField(
        max_length=16,  # visual input length (for phone number)
        widget=forms.TextInput(attrs={'maxlength': 16}),
        required=True, label="Telefon Numarası"
    )
    password1 = forms.CharField(
        max_length=128,
        widget=forms.PasswordInput(),
        required=True,
        label="Şifre"
    )
    password2 = forms.CharField(
        max_length=128,
        widget=forms.PasswordInput(),
        required=True,
        label="Şifre Doğrulama"
    )

    class Meta:
        model = CustomUser
        fields = ('email', 'first_name', 'last_name', 'tc_kimlik_no','birth_date', 'phone_number', 'password1', 'password2')


    def clean_tc_kimlik_no(self):
        tc = self.cleaned_data.get('tc_kimlik_no')

        if not tc.isdigit() or len(tc) != 11:
            raise ValidationError("T.C. Kimlik Numarası 11 haneli ve sadece rakamlardan oluşmalıdır.")

        if CustomUser.objects.filter(tc_kimlik_no=tc).exists():
            raise ValidationError("Bu T.C. Kimlik Numarası zaten kayıtlı.")

        return tc

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exists():
            raise ValidationError("Bu e-posta adresi zaten kullanılıyor.")
        return email

    def clean_birth_date(self):
        birth_date = self.cleaned_data.get('birth_date')
        if birth_date:
            age = (timezone.now().date() - birth_date).days // 365
            if age < 18:
                raise ValidationError("18 yaşından büyük olmalısınız.")
        return birth_date

    def clean_phone_number(self):
        phone = self.cleaned_data['phone_number']
        cleaned_phone = re.sub(r'\D', '', phone)  # correctly remove non-digits (for phone number)
        if len(cleaned_phone) != 11:
            raise forms.ValidationError("Telefon numarası 11 haneli olmalıdır.")
        return cleaned_phone

    def clean_password1(self):
        password = self.cleaned_data.get('password1')
        if len(password) < 8:
            raise ValidationError("Şifre en az 8 karakter olmalıdır.")
        if not re.search(r'[A-Za-z]', password) or not re.search(r'\d', password):
            raise forms.ValidationError('Şifre en az bir harf ve bir rakam içermelidir.')
        return password

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['email']
        user.tc_kimlik_no = self.cleaned_data['tc_kimlik_no']
        
        if commit:
            user.save()
        return user

CITY_CHOICES = [('', 'İl Seçiniz')] + [(city, city) for city in [
    "Adana", "Adıyaman", "Afyonkarahisar", "Ağrı", "Aksaray", "Amasya", "Ankara",
    "Antalya", "Ardahan", "Artvin", "Aydın", "Balıkesir", "Bartın", "Batman",
    "Bayburt", "Bilecik", "Bingöl", "Bitlis", "Bolu", "Burdur", "Bursa",
    "Çanakkale", "Çankırı", "Çorum", "Denizli", "Diyarbakır", "Düzce", "Edirne",
    "Elazığ", "Erzincan", "Erzurum", "Eskişehir", "Gaziantep", "Giresun",
    "Gümüşhane", "Hakkari", "Hatay", "Iğdır", "Isparta", "İstanbul", "İzmir",
    "Kahramanmaraş", "Karabük", "Karaman", "Kars", "Kastamonu", "Kayseri",
    "Kilis", "Kırıkkale", "Kırklareli", "Kırşehir", "Kocaeli", "Konya",
    "Kütahya", "Malatya", "Manisa", "Mardin", "Mersin", "Muğla", "Muş",
    "Nevşehir", "Niğde", "Ordu", "Osmaniye", "Rize", "Sakarya", "Samsun",
    "Siirt", "Sinop", "Sivas", "Şanlıurfa", "Şırnak", "Tekirdağ", "Tokat",
    "Trabzon", "Tunceli", "Uşak", "Van", "Yalova", "Yozgat", "Zonguldak"
]]

class AddressForm(forms.ModelForm):
    city = forms.ChoiceField(
        choices=CITY_CHOICES,
        label="Şehir",
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_city'})
    )

    district = forms.CharField(
        label="İlçe",
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_district'})
    )

    class Meta:
        model = Address
        fields = (
            'title',
            'address_type',
            'full_name',
            'phone',
            'city',
            'district',
            'address_line',
            'country',
        )
        labels = {
            'title': 'Adres Başlığı',
            'address_type': 'Adres Türü',
            'full_name': 'Ad Soyad',
            'phone': 'Telefon',
            'city': 'Şehir',
            'district': 'İlçe',
            'address_line': 'Adres',
            'country': 'Ülke',
        }
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Örn: Ev, İşyeri, Yazlık'}),
            'address_type': forms.Select(attrs={'class': 'form-control'}),
            'full_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Adınızı ve soyadınızı giriniz'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '05XX XXX XX XX'}),
            'address_line': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'Mahalle, sokak, bina ve kapı numarası...'}),
            'country': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Türkiye'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['district'].widget.choices = [('', 'İlçe Seçiniz')]

        self.fields['country'].initial = 'Türkiye'
        self.fields['country'].widget = forms.HiddenInput()

        # Placeholders for dynamic fields (for address form)
        self.fields['title'].widget.attrs.update({'placeholder': 'Örn: Ev, İşyeri, Yazlık'})
        self.fields['full_name'].widget.attrs.update({'placeholder': 'Adınızı ve soyadınızı giriniz'})
        self.fields['phone'].widget.attrs.update({'placeholder': '05XX XXX XX XX'})
        self.fields['address_line'].widget.attrs.update({'placeholder': 'Mahalle, sokak, bina ve kapı numarası...'})

        for field in self.fields.values():
            field.error_messages.update({
                'required': f'{field.label} alanı boş bırakılamaz.',
            })

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ('first_name', 'last_name', 'email', 'phone_number', 'birth_date')
        labels = {
            'first_name': 'İsim',
            'last_name': 'Soyisim',
            'email': 'Email',
            'phone_number': 'Telefon Numarası',
            'birth_date': 'Doğum Tarihi',
        }

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product

        fields = ['name', 'category', 'description', 'price', 'stock', 'is_active', 'has_sizes', 'has_colors']
        labels = {
            'name': 'Ürün Adı',
            'category': 'Kategori',
            'description': 'Açıklama',
            'price': 'Fiyat',
            'stock': 'Stok',
            'is_active': 'Durum',
            'has_sizes': 'Beden Seçeneği Var mı?',
            'has_colors': 'Renk Seçeneği Var mı?',
        }
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'price': forms.NumberInput(attrs={'class': 'form-control'}),
            'stock': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'toggle-input'}),
            'has_sizes': forms.CheckboxInput(attrs={'class': 'toggle-input'}),
            'has_colors': forms.CheckboxInput(attrs={'class': 'toggle-input'}),
        }

class ProductImageForm(forms.ModelForm):
    class Meta:
        model = ProductImage
        fields = ['image']
        widgets = {
            # 'FileInput' use removes the "Currently" text
            'image': forms.FileInput(attrs={'class': 'form-control'}),
        }

class BaseProductImageFormSet(forms.BaseInlineFormSet):
    def clean(self):
        """Enforce upload of 1 to 5 images"""
        super().clean()
        
        if any(self.errors):
            # If there are already data type errors in the forms, do not clean
            return

        count = 0
        for form in self.forms:
            # Only count valid and not deleted forms
            if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                # If the image field is empty (new empty row), count
                if form.cleaned_data.get('image'):
                    count += 1
        
        if count < 1:
            raise forms.ValidationError("En az 1 adet ürün görseli yüklemek zorunludur.")
        if count > 5:
            raise forms.ValidationError("En fazla 5 adet ürün görseli yükleyebilirsiniz.")

ProductImageFormSet = inlineformset_factory(
    Product, 
    ProductImage, 
    form=ProductImageForm,
    formset=BaseProductImageFormSet,
    fields=('image',), 
    max_num = 5,
    extra=1, # For new addition, only 1 empty slot remains, to avoid complexity
    can_delete=True
)
class OrderStatusForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['status']
        labels = {'status': 'Sipariş Durumu'}

class EmailForm(forms.Form):
    subject = forms.CharField(label="Konu", max_length=100)
    message = forms.CharField(label="Mesaj", widget=forms.Textarea)

class HomeSlideForm(forms.ModelForm):
    class Meta:
        model = HomeSlide
        fields = ['title', 'image', 'order']
        labels = {
            'title': 'Başlık',
            'image': 'Görsel',
            'order': 'Sıra',
        }
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class BulkDiscountForm(forms.ModelForm):
    class Meta:
        model = BulkDiscount
        fields = ['product', 'quantity_threshold', 'discount_percent']
        labels = {
            'product': 'Ürün',
            'quantity_threshold': 'Minimum Adet',
            'discount_percent': 'İndirim Yüzdesi',
        }
        widgets = {
            'product': forms.Select(attrs={'class': 'form-control'}),
            'quantity_threshold': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'discount_percent': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 100}),
        }
    
    def clean_discount_percent(self):
        discount = self.cleaned_data.get('discount_percent')
        if discount < 1 or discount > 100:
            raise ValidationError("İndirim yüzdesi 1 ile 100 arasında olmalıdır.")
        return discount
    
    def clean_quantity_threshold(self):
        quantity = self.cleaned_data.get('quantity_threshold')
        if quantity < 1:
            raise ValidationError("Minimum adet 1 veya daha fazla olmalıdır.")
        return quantity