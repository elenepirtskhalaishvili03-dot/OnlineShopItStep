from django import forms
from django.contrib.auth.models import User

from .models import Product


class StyledFieldsMixin:
    def apply_shared_styles(self) -> None:
        for name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs['class'] = 'form-check-input'
                continue

            classes = widget.attrs.get('class', '')
            widget.attrs['class'] = f'{classes} form-control'.strip()
            widget.attrs.setdefault('placeholder', field.label or name.replace('_', ' ').title())

            if isinstance(widget, forms.Textarea):
                widget.attrs.setdefault('rows', 4)


class UserRegistrationForm(StyledFieldsMixin, forms.ModelForm):
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirm Password", widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ['username', 'email']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_shared_styles()

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords do not match.")
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        user.is_staff = False  # regular customer by default
        if commit:
            user.save()
        return user


class LoginForm(StyledFieldsMixin, forms.Form):
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_shared_styles()


class ProductForm(StyledFieldsMixin, forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'description', 'price', 'stock', 'image', 'image_url', 'is_active']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_shared_styles()

