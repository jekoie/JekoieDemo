from django import forms
from django.contrib.auth import get_user_model, password_validation
from django.contrib.auth import views as auth_views
from django.utils.translation import ugettext_lazy as _
from easy_thumbnails.fields import ThumbnailerImageField
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.contrib.auth.models import Group

class AuthenticationForm(auth_views.AuthenticationForm):
    username = forms.CharField(label='用户名', widget=forms.TextInput(
        attrs={'class': 'form-control', 'autofocus': True, 'placeholder': '用户名或Email'}), max_length=254 )
    password = forms.CharField(label='密码', widget=forms.PasswordInput(attrs={'class': 'form-control'}), strip=False)
    remberme = forms.BooleanField(label='记住密码', widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}), required=False)

class PasswordResetForm(auth_views.PasswordResetForm):
    email = forms.EmailField(label='Email', max_length=254, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    def clean_email(self):
        email = self.cleaned_data.get('email', '')
        user = get_user_model().objects.filter(email=email)
        if not user:
            raise forms.ValidationError('邮箱未注册', code='invalid')

        return email

class SetPasswordForm(auth_views.SetPasswordForm):
    new_password1 = forms.CharField( label=_("New password"),
                                     widget=forms.PasswordInput(attrs={'class': 'form-control'}), strip=False,
                                     help_text=password_validation.password_validators_help_text_html() )

    new_password2 = forms.CharField( label=_("New password confirmation"), strip=False,
                                     widget=forms.PasswordInput(attrs={'class': 'form-control'}))


class PasswordChangeForm(auth_views.PasswordChangeForm):
    new_password1 = forms.CharField( label=_("New password"), widget= forms.PasswordInput(attrs={'class': 'form-control'}),
                                     strip=False, help_text=password_validation.password_validators_help_text_html())
    new_password2 = forms.CharField( label=_("New password confirmation"), strip=False,
                                     widget=forms.PasswordInput(attrs={'class': 'form-control'}) )
    old_password = forms.CharField( label=_("Old password"), strip=False,
                                    widget=forms.PasswordInput(attrs={'autofocus': True, 'class':'form-control'}) )

class PersonalInfoForm(forms.ModelForm):
    class Meta:
        model = get_user_model()
        fields = ('username', 'chinese_name', 'deparment', 'email', 'phone', 'photo', 'addr')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'readonly':''}),
            'chinese_name': forms.TextInput(attrs={'class': 'form-control', 'required': ''}),
            'deparment': forms.Select(attrs={'class': 'form-control', 'required': ''}),
            'email': forms.TextInput(attrs={'class': 'form-control', 'required': ''}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'required': ''}),
            'photo': forms.FileInput(attrs={'class': 'custom-file-input'}),
            'addr': forms.TextInput(attrs={'class': 'form-control'}),
        }



class RegisterForm(forms.ModelForm):
    password1 = forms.CharField(label='密码确认', widget=forms.PasswordInput( attrs={'class': 'form-control'}), strip=False)

    class Meta:
        model = get_user_model()
        fields = ('username', 'chinese_name', 'deparment' , 'password' , 'password1' , 'email', 'phone', 'photo', 'addr')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'password': forms.PasswordInput(attrs={'class': 'form-control'}),
            'chinese_name': forms.TextInput(attrs={'class': 'form-control', 'required': ''}),
            'deparment': forms.Select(attrs={'class': 'form-control', 'required': ''}),
            'email': forms.TextInput(attrs={'class': 'form-control', 'required': ''}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'required': ''}),
            'photo': forms.FileInput(attrs={'class': 'custom-file-input'}),
            'addr': forms.TextInput(attrs={'class': 'form-control'}),
        }

        help_texts = {
            'password': password_validation.password_validators_help_text_html(),
        }

    def clean_password1(self):
        password, password1 = self.cleaned_data['password'] ,self.cleaned_data['password1']
        if password and password1:
            if password != password1:
                raise forms.ValidationError('密码不一致', code='password_mismatch')

        return password

    def clean_email(self):
        email = self.cleaned_data['email']
        print(email)
        user = get_user_model().objects.filter(email=email)
        if user:
            raise forms.ValidationError('邮箱已注册', code='email_registered')
        return email

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.set_password(self.cleaned_data['password'])
        if commit:
            instance.save()

        return instance

#组模型表单
class GroupAdminForm(forms.ModelForm):
    users = forms.ModelMultipleChoiceField(label='用户', queryset=get_user_model().objects.all(), required=False ,widget=FilteredSelectMultiple('用户', False))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['users'].label_from_instance = lambda obj:'{} | {} | {}'.format(obj.username, obj.chinese_name, obj.email)
        if self.instance.pk:
            self.fields['users'].initial = self.instance.user_set.all()

    def save(self, commit=True):
        ins = super().save()
        self.save_m2m()
        return ins

    def save_m2m(self):
        self.instance.user_set.set(self.cleaned_data['users'])

    class Meta:
        model = Group
        exclude = []