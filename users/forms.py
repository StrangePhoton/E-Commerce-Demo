from django import forms
from .models import CustomUser


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'phone_number', 'birth_date']
        labels = {
            'first_name': 'İsim',
            'last_name': 'Soyisim',
            'email': 'Email',
            'phone_number': 'Telefon Numarası',
            'birth_date': 'Doğum Tarihi',
        }

    def __init__(self, *args, **kwargs):
        super(UserProfileForm, self).__init__(*args, **kwargs)
        
        if 'email' in self.fields:
            self.fields['email'].disabled = True
        
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})