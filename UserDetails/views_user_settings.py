from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect
from django.views.generic import TemplateView
from django.utils.translation import gettext as _

from .forms import UserForm, DiningProfileForm


class SettingsView(TemplateView):
    template_name = "account/settings/settings_base.html"


class Settings_Profile_View(LoginRequiredMixin, TemplateView):
    template_name = "account/settings/settings_account.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'user_form': UserForm(instance=self.request.user),
            'dining_form': DiningProfileForm(instance=self.request.user.userdiningsettings),
        })
        return context

    def post(self, request, *args, **kwargs):
        context = self.get_context_data()

        context.update({
            'user_form': UserForm(request.POST, instance=self.request.user),
            'dining_form': DiningProfileForm(request.POST, instance=self.request.user.userdiningsettings),
        })

        if context['user_form'].is_valid() and context['dining_form'].is_valid():
            context['user_form'].save()
            context['dining_form'].save()
            messages.success(request, _("Profile saved."))

            return redirect('settings_account')

        return self.render_to_response(context)