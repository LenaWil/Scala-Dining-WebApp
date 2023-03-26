from datetime import datetime, timedelta
from typing import cast
from dal_select2.views import Select2QuerySetView
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Value
from django.db.models.functions import Concat
from django.urls import reverse_lazy
from django.views.generic import ListView, FormView

from dining.models import DiningList, DiningEntry
from scaladining import settings
from userdetails.forms import RegisterUserForm
from userdetails.models import User


class RegisterView(FormView):
    template_name = "account/signup.html"
    form_class = RegisterUserForm
    success_url = reverse_lazy("index")

    def form_valid(self, form):
        user = form.save()
        login(self.request, user, backend="django.contrib.auth.backends.ModelBackend")
        return super().form_valid(form)


class DiningJoinHistoryView(LoginRequiredMixin, ListView):
    context = {}
    template_name = "accounts/user_history_joined.html"
    paginate_by = 20

    def get_queryset(self):
        return DiningEntry.objects.internal().filter(user=self.request.user).order_by("-dining_list__date")


class DiningPayHistoryView(LoginRequiredMixin, ListView):
    context = {}
    template_name = "accounts/user_history_paid.html"
    paginate_by = 20

    def get_queryset(self):
        return self.request.user.get_debts()
        return (
            DiningEntry.objects.internal()
            .filter(user=self.request.user)
            .filter(has_paid=False)
            .filter(dining_list__payment_link__istartswith="http")
            .filter(dining_list__dining_cost__gt=0)
            # the correct query would be kinda complicated and I am lazy, so here is a bad version
            # .filter(dining_list__is_adjustable=True)
            .filter(dining_list__date__lte=datetime.now() + settings.TRANSACTION_PENDING_DURATION)
            .order_by("-dining_list__date")
        )


class DiningClaimHistoryView(LoginRequiredMixin, ListView):
    template_name = "accounts/user_history_claimed.html"
    paginate_by = 20

    def get_queryset(self):
        return DiningList.objects.filter(owners=self.request.user).order_by("-date")


class PeopleAutocompleteView(LoginRequiredMixin, Select2QuerySetView):
    # django-autocomplete-light does infinite scrolling by default, but doesn't seem to trigger when paginate_by has a
    # lower value (e.g. 5)
    # paginate_by = 10

    def get_queryset(self):
        qs = User.objects.filter(is_active=True)
        if self.q:
            qs = qs.annotate(full_name=Concat("first_name", Value(" "), "last_name")).filter(
                full_name__icontains=self.q
            )
        return qs

    def get_result_label(self, result):
        return result.get_full_name()
