from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import Http404, HttpResponseRedirect, HttpResponseForbidden
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.http import is_safe_url
from django.utils.translation import gettext as _
from django.views.generic import TemplateView, View
from django.views.generic.base import ContextMixin
from django.views.generic.edit import DeleteView
from django.conf import settings

from .forms import *
from .models import *


def index(request):
    upcoming = timezone.now().date()
    # If weekend, redirect to Monday after
    if upcoming.weekday() >= 5:
        upcoming = upcoming + timedelta(days=7 - upcoming.weekday())
    return redirect('day_view', year=upcoming.year, month=upcoming.month, day=upcoming.day)


class DayMixin(ContextMixin):
    """
    Adds useful thingies to context and self that have to do with the request date.
    """

    date = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['date'] = self.date
        context['next_date'] = self.date + timedelta(days=3 if self.date.weekday() == 4 else 1)
        context['previous_date'] = self.date - timedelta(days=3 if self.date.weekday() == 0 else 1)
        if context['next_date'] - timezone.now().date() > timedelta(days=7):
            context['next_date'] = None
        if (context['previous_date'] - timezone.now().date()).days < -2:
            context['previous_date'] = None
        context['is_today'] = (self.date - timezone.now().date()).days == 0
        return context

    def init_date(self):
        """
        Fetches the date from the request arguments.
        """
        if self.date:
            # Already initialized
            return
        self.date = date(self.kwargs['year'], self.kwargs['month'], self.kwargs['day'])
        if self.date.weekday() >= 5:
            raise Http404('Weekends are not available')

    def dispatch(self, request, *args, **kwargs):
        """
        Construct date before get/post is called.
        """
        self.init_date()
        return super().dispatch(request, *args, **kwargs)

    def reverse(self, *args, kwargs=None, **other_kwargs):
        """
        URL reverse which expands the date. See
        https://docs.djangoproject.com/en/2.1/ref/urlresolvers/#django.urls.reverse
        """
        kwargs = kwargs or {}
        kwargs['year'] = self.date.year
        kwargs['month'] = self.date.month
        kwargs['day'] = self.date.day
        return reverse(*args, kwargs=kwargs, **other_kwargs)


class DiningListMixin(DayMixin):
    """
    Extends the day mixin with dining list thingies.
    """
    dining_list = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['dining_list'] = self.dining_list
        return context

    def init_dining_list(self):
        """
        Fetches the dining list using the request arguments.
        """
        if self.dining_list:
            # Already initialized
            return
        # Needs initialized date
        self.init_date()
        self.dining_list = get_object_or_404(DiningList, date=self.date, association__slug=self.kwargs['identifier'])

    def dispatch(self, request, *args, **kwargs):
        self.init_dining_list()
        return super().dispatch(request, *args, **kwargs)

    def reverse(self, *args, kwargs=None, **other_kwargs):
        kwargs = kwargs or {}
        kwargs['identifier'] = self.dining_list.association.slug
        return super().reverse(*args, kwargs=kwargs, **other_kwargs)


class DayView(LoginRequiredMixin, DayMixin, TemplateView):
    """"
    This is the view responsible for the day index
    Task:
    -   display all occupied dining slots
    -   allow for additional dining slots to be made if place is available
    """

    template_name = "dining_lists/dining_day.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['dining_lists'] = DiningList.objects.filter(date=self.date)
        context['Announcements'] = DiningDayAnnouncements.objects.filter(date=self.date)

        # Check if create slot button must be shown
        # (but I prefer to only check when claiming to reduce code)
        in_future = self.date >= timezone.now().date()
        if in_future and self.date == timezone.now().date():
            # If date is today, check if the dining slot claim time has not passed
            if settings.DINING_SLOT_CLAIM_CLOSURE_TIME < timezone.now().time():
                in_future = False

        has_no_claimed_slots = len(context['dining_lists'].filter(claimed_by=self.request.user)) == 0
        context['can_create_slot'] = DiningList.objects.available_slots(self.date) >= 0 and\
                                     in_future and has_no_claimed_slots

        # Make the view clickable
        context['interactive'] = True

        return context


class NewSlotView(LoginRequiredMixin, DayMixin, TemplateView):
    """
    Creation page for a new dining list.
    """
    template_name = "dining_lists/dining_add.html"

    def get(self, request, *args, **kwargs):
        context = self.get_context_data()
        context['slot_form'] = CreateSlotForm(self.request.user, context['date'])
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        context = self.get_context_data()

        form = CreateSlotForm(request.user, self.date, request.POST)

        if form.is_valid():
            dining_list = form.save()


            return redirect(dining_list)

        context['slot_form'] = form
        return self.render_to_response(context)

    def dispatch(self, request, *args, **kwargs):
        """
        Disable page when no slots are available.
        """
        # Check available slots
        # Todo: possibly also disable page when date is in the past or later than closure time!
        self.init_date()
        available_slots = DiningList.objects.available_slots(self.date)
        if available_slots <= 0:
            error = _("No free slots availlable")
            messages.add_message(request, messages.ERROR, error)
            return HttpResponseRedirect(self.reverse('day_view', kwargs={}))

        if len(DiningList.objects.filter(date=self.date).filter(claimed_by=self.request.user)) > 0:
            error = _("You have already a dining slot claimed today")
            messages.add_message(request, messages.ERROR, error)
            return HttpResponseRedirect(self.reverse('day_view', kwargs={}))
        return super().dispatch(request, *args, **kwargs)


class EntryAddView(LoginRequiredMixin, DiningListMixin, TemplateView):
    template_name = "dining_lists/dining_entry_add.html"
    add_external_button_name = "addExternalButton"

    def check_user_permission(self, request):
        # If user is dining list owner or purchaser
        if request.user == self.dining_list.claimed_by or request.user == self.dining_list.purchaser:
            return True

        if not self.dining_list.is_open():
            # Dining list is closed. Go back to the info screen
            error = _("Dining list is closed, people can no longer join")
            messages.add_message(request, messages.ERROR, error)
            return False

        if not self.dining_list.has_room():
            # dining list is full. Go back to the info screen
            error = _("Dining list is already full, ask the chef personally if you want to join")
            messages.add_message(request, messages.ERROR, error)
            return False

        # No problems, use can add people
        return True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Search processing
        search = self.request.GET.get('search')
        if search:
            users = None
            # split over all spaces
            for search_part in search.split(" "):
                # query the substring if it is part of either the first, last or username
                search_result = get_user_model().objects.filter(
                    Q(first_name__icontains=search_part) |
                    Q(last_name__icontains=search_part) |
                    Q(username__icontains=search_part)
                )
                if users is None:
                    users = search_result
                elif search_result.count()>0:
                    users = users.intersection(search_result)

            # Search all users corresponding with the typed in name
            context['users'] = users
            context['search'] = search

            if len(context['users']) == 0:
                context['error_input'] = "Error: no people with that name found"
            elif len(context['users']) > 10:
                context['error_input'] = "Error: search produced too many results"
                context['users'] = None
            else:
                context['error_input'] = None
        else:
            context['users'] = None
            context['search'] = ""
            context['error_input'] = None

        context['add_external_button_name'] = self.add_external_button_name

        return context

    def get(self, request, *args, **kwargs):
        # Check permissions, if user has no access to this page, reject it.
        if not self.check_user_permission(request):
            return HttpResponseRedirect(self.reverse('slot_details'))

        context = self.get_context_data()

        # Form rendering
        context['form'] = DiningEntryUserCreateForm(request.user, self.dining_list)

        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        context = self.get_context_data()

        # Check permissions, if user has no access to this page, reject it.
        if not self.check_user_permission(request):
            return HttpResponseRedirect(self.reverse('slot_details'))

        # Do form shenanigans
        if self.add_external_button_name in request.POST:
            form = DiningEntryExternalCreateForm(request.user, self.dining_list,
                                                 request.POST['external_name'], data=request.POST)
        else:
            form = DiningEntryUserCreateForm(request.user, self.dining_list, data=request.POST)

        if form.is_valid():
            form.save()

        # If next is provided, put possible error messages on the messages system and redirect
        next = request.GET.get('next', None)
        if next and is_safe_url(next, request.get_host()):
            for field, errors in form.errors.items():
                for error in errors:
                    messages.add_message(request, messages.ERROR, error)
            return HttpResponseRedirect(next)

        # If next not provided, but the form was valid, redirect to the slot list
        if form.is_valid():
            # Todo: Check if user is on multiple dining lists today, then show warning
            return HttpResponseRedirect(self.reverse('slot_list'))

        # Render form otherwise
        context['form'] = form
        return self.render_to_response(context)


class EntryRemoveView(LoginRequiredMixin, DiningListMixin, View):
    #http_method_names = ['post']

    def get(self, request, *args, entry_id=None, **kwargs):
        # TODO: This is a quick fix, some places still refer to a get page, but are already in a form
        # (e.g. diners display) and thus this is needed.
        return self.post(request, *args, entry_id=entry_id, **kwargs)

    def post(self, request, *args, entry_id=None, **kwargs):
        # Get entry
        if entry_id:
            entry = get_object_or_404(DiningEntry, id=entry_id)
        else:
            entry = get_object_or_404(DiningEntryUser, dining_list=self.dining_list, user=request.user)

        # Process deletion
        form = DiningEntryDeleteForm(request.user, entry)
        if form.is_valid():
            form.execute()
            if entry_id:
                message = _('The user is removed from the dining list.')
            else:
                message = _('You are removed from the dining list.')
            messages.add_message(request, messages.SUCCESS, message)
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.add_message(request, messages.ERROR, error)

        # Go to next
        next = request.GET.get('next')
        if not is_safe_url(next, request.get_host()):
            next = self.reverse('slot_list')

        return HttpResponseRedirect(next)


class SlotMixin(DiningListMixin):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['is_open'] = self.dining_list.is_open()
        context['user_is_on_list'] = self.dining_list.internal_dining_entries().filter(user=self.request.user).exists()
        context['user_can_add_self'] = self.dining_list.can_join(self.request.user)
        context['user_can_add_others'] = self.dining_list.can_join(self.request.user, check_for_self=False)

        # Get the amount of messages
        context['comments_total'] = self.dining_list.diningcomment_set.count()
        # Get the amount of unread messages
        view_time = DiningCommentVisitTracker.get_latest_visit(user=self.request.user, dining_list=self.dining_list)
        if view_time is None:
            context['comments_unread'] = context['comments_total']
        else:
            context['comments_unread'] = self.dining_list.diningcomment_set.filter(timestamp__gte=view_time).count()

        return context


class SlotListView(LoginRequiredMixin, SlotMixin, TemplateView):
    template_name = "dining_lists/dining_slot_diners.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tab'] = "list"

        context['entries'] = self.dining_list.dining_entries.all()

        # determine whether the user has external entries added that he/she can remove until closing time
        context['can_delete_some'] = \
            self.dining_list.external_dining_entries().filter(user=self.request.user).count() > 0
        context['can_delete_some'] = context['can_delete_some'] * context['is_open']

        context['can_edit_stats'] = (self.request.user == self.dining_list.claimed_by)
        context['can_delete_all'] = (self.request.user == self.dining_list.claimed_by)
        purchaser = self.dining_list.purchaser
        context['can_edit_pay'] = (self.request.user == purchaser or
                                   (purchaser is None and self.request.user == self.dining_list.claimed_by))
        return context

    def post(self, request, *args, **kwargs):
        can_adjust_stats = request.user == self.dining_list.claimed_by
        can_adjust_paid = request.user == self.dining_list.get_purchaser()

        if not (can_adjust_stats or can_adjust_paid):
            messages.add_message(request, messages.ERROR, "You did not have the rights to adjust anything")
            return HttpResponseRedirect(self.reverse('slot_list'))

        # Get all the keys in the post and put all relevant ones in a list
        post_requests = []
        for key in request.POST:
            key = key.split(":")
            if len(key) == 2:
                post_requests.append(key)

        if can_adjust_paid:
            # Process payment for all entries
            entries = {}

            # For all entries in the dining list, set the paid value to false
            for entry in self.dining_list.dining_entries.all():
                entry.has_paid = False
                entries[str(entry.id)] = entry

            # Go over all keys in the request containing has_paid, adjust the state on that object
            for key in post_requests:
                if key[1] == "has_paid":
                    entries[key[0]].has_paid = True

            # save all has_paid values
            for entry in entries.values():
                entry.save()

        if can_adjust_stats:
            # Adjust the help stats
            entries = {}

            # For all entries in the dining list, set the values to false
            for entry in self.dining_list.internal_dining_entries():
                entry.has_shopped = False
                entry.has_cooked = False
                entry.has_cleaned = False
                entries[str(entry.id)] = entry

            # Go over all keys in the request containing has_paid, adjust the state on that object
            for key in post_requests:
                if key[1] == "has_shopped":
                    entries[key[0]].has_shopped = True
                elif key[1] == "has_cooked":
                    entries[key[0]].has_cooked = True
                elif key[1] == "has_cleaned":
                    entries[key[0]].has_cleaned = True

            # save all has_paid values
            for entry in entries.values():
                entry.save()

        return HttpResponseRedirect(self.reverse('slot_list'))


class SlotInfoView(LoginRequiredMixin, SlotMixin, TemplateView):
    template_name = "dining_lists/dining_slot_info.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tab'] = "info"

        context['comments'] = self.dining_list.diningcomment_set.order_by('-pinned_to_top', 'timestamp').all()

        # Last visit
        context['last_visited'] = DiningCommentVisitTracker.get_latest_visit(
            user=self.request.user,
            dining_list=self.dining_list,
            update=True)

        from django.db.models import CharField
        from django.db.models.functions import Length
        CharField.register_lookup(Length)
        context['number_of_allergies'] = self.dining_list.internal_dining_entries().filter(
            user__userdiningsettings__allergies__length__gt=1).count()

        if self.dining_list.claimed_by == self.request.user or self.dining_list.purchaser == self.request.user:
            context['can_change_settings'] = True
        if self.dining_list.claimed_by == self.request.user and self.dining_list.diners.count() < self.dining_list.min_diners:
            context['can_remove_list'] = True
        else:
            context['can_remove_list'] = False
        return context

    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)

        # Add the comment
        comment_form = DiningCommentForm(request.user, self.dining_list, data=request.POST)

        if comment_form.is_valid():
            comment_form.save()
            return HttpResponseRedirect(self.reverse('slot_details'))
        else:
            context['form'] = comment_form
            return self.render_to_response(context)




# Could possibly use the Django built-in FormView or ModelFormView in combination with FormSet
class SlotInfoChangeView(LoginRequiredMixin, SlotMixin, TemplateView):
    template_name = "dining_lists/dining_slot_info_alter.html"

    def get(self, request, *args, **kwargs):
        context = self.get_context_data()

        if self.dining_list.claimed_by == request.user:
            context['info_form'] = DiningInfoForm(instance=self.dining_list)

        if self.dining_list.get_purchaser() == request.user:
            context['payment_form'] = DiningPaymentForm(instance=self.dining_list)

        if context.get('info_form') is None and context.get('payment_form') is None:
            # User is not allowed on this page
            return HttpResponseForbidden()

        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        context = self.get_context_data()

        is_valid = True
        can_change = False

        context['payment_form'] = None

        # Check if the active user is the current user, if checked after the general info, the local object could have
        # it's information changed causing usage errors
        is_purchaser = self.dining_list.get_purchaser() == request.user

        # Check general info
        if self.dining_list.claimed_by == request.user:
            can_change = True
            context['info_form'] = DiningInfoForm(request.POST, instance=self.dining_list)
            if context['info_form'].is_valid():
                context['info_form'].save()
            else:
                is_valid = False

        if is_purchaser:
            can_change = True
            context['payment_form'] = DiningPaymentForm(request.POST, instance=self.dining_list)
            if context['payment_form'].is_valid():
                context['payment_form'].save()
            else:
                is_valid = False

        # Redirect if forms were all valid, stay otherwise
        if not can_change:
            return HttpResponseForbidden()
        elif is_valid:
            messages.add_message(request, messages.SUCCESS, "Changes successfully saved")
            return HttpResponseRedirect(self.reverse('slot_details'))

        return self.render_to_response(context)


class SlotAllergyView(LoginRequiredMixin, SlotMixin, TemplateView):
    template_name = "dining_lists/dining_slot_allergy.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tab'] = "allergy"

        from django.db.models import CharField
        from django.db.models.functions import Length
        CharField.register_lookup(Length)
        context['allergy_entries'] = self.dining_list.internal_dining_entries().filter(
            user__userdiningsettings__allergies__length__gte=1)

        return context


class SlotDeleteView(LoginRequiredMixin, SlotMixin, DeleteView):
    """
    Page for slot deletion. Page is only available for slot owners.
    """
    template_name = "dining_lists/dining_slot_delete.html"
    context_object_name = "dining_list"

    def get_object(self, queryset=None):
        if self.request.user != self.dining_list.claimed_by:
            # Block page for non slot owners
            raise Http404("Deletion not available.")
        return self.dining_list

    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        form = DiningListDeleteForm(request.user, instance)
        if form.is_valid():
            form.execute()
            messages.add_message(request, messages.SUCCESS, _("Dining list is deleted."))
            # Need to use reverse from the DiningListMixin superclass
            return HttpResponseRedirect(super(DiningListMixin, self).reverse("day_view"))

        # Could not delete
        for error in form.non_field_errors():
            messages.add_message(request, messages.ERROR, error)

        return HttpResponseRedirect(self.reverse("slot_delete"))
