from django.shortcuts import render, redirect
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.shortcuts import resolve_url
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from . import forms


class LoginView(auth_views.LoginView):
    authentication_form = forms.AuthenticationForm
    template_name = 'accounts/registration/login.html'

    def get_success_url(self):
        if not self.request.POST.get('remberme', None):
            self.request.session.set_expiry(0)
        else:
            self.request.session.set_expiry(settings.SESSION_COOKIE_AGE)
        url = self.get_redirect_url()
        return url or resolve_url(settings.LOGIN_REDIRECT_URL)

class LogoutView(auth_views.LogoutView):
    template_name = 'accounts/registration/logout.html'

class PasswordChangeView(auth_views.PasswordChangeView):
    form_class = forms.PasswordChangeForm
    template_name = 'accounts/registration/password_change_form.html'
    success_url = reverse_lazy('accounts:password_change_done')

class PasswordChangeDoneView(auth_views.PasswordChangeDoneView):
    template_name = 'accounts/registration/password_change_done.html'

class PasswordResetView(auth_views.PasswordResetView):
    form_class = forms.PasswordResetForm
    template_name = 'accounts/registration/password_reset_form.html'
    email_template_name = 'accounts/registration/password_reset_email.html'
    subject_template_name = 'accounts/registration/password_reset_subject.txt'
    html_email_template_name = 'accounts/registration/password_reset_html_email.html'
    success_url = reverse_lazy('accounts:password_reset_done')

class PasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    form_class = forms.SetPasswordForm
    template_name = 'accounts/registration/password_reset_confirm.html'
    success_url = reverse_lazy('accounts:password_reset_complete')

@login_required
def personalInfo(request):
    if request.method == 'POST':
        form = forms.PersonalInfoForm(instance=request.user, data=request.POST, files=request.FILES)
        if form.is_valid():
            ins = form.save(commit=False)
            ins.username = request.user.username
            ins.save()
            messages.success(request, '个人信息修改成功')
        else:
            messages.error(request, '个人信息修改失败')
            return render(request, 'accounts/personal_info.html', {'form': form})
    form = forms.PersonalInfoForm(instance=request.user)
    return render(request, 'accounts/personal_info.html', {'form': form})

def register(request):
    if request.method == 'POST':
        form = forms.RegisterForm(data=request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, '注册成功，你现在可以登录了！')
            return redirect('accounts:login')
        else:
            return render(request, 'accounts/register.html', {'form': form})
    form = forms.RegisterForm()
    return render(request, 'accounts/register.html', {'form': form})