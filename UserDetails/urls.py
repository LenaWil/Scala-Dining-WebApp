from django.urls import path, include

from CreditManagement.views import TransactionAddView
from .views import RegisterView, DiningHistoryView, ProfileView
from .views_association import CreditsOverview, TransactionsCsvView, MembersOverview, MembersEditView, \
    AssociationOverview

urlpatterns = [
    path('association/<slug:association_name>/', include([
        path('', AssociationOverview.as_view(), name='association_overview'),
        path('transactions/', CreditsOverview.as_view(), name='association_credits'),
        path('transactions/csv/', TransactionsCsvView.as_view(), name='association_transactions_csv'),
        path('transactions/add/', TransactionAddView.as_view(), name='transaction_add'),
        path('members/', MembersOverview.as_view(), name='association_members'),
        path('members/edit/', MembersEditView.as_view(), name='association_members_edit'),
    ])),

    # Override allauth sign up page with our registration page
    path('signup/', RegisterView.as_view(), name='account_signup'),

    path('history/dining/', DiningHistoryView.as_view(), name='history_lists'),
    path('history/dining/<int:page>/', DiningHistoryView.as_view(), name='history_lists'),
    path('profile/', ProfileView.as_view(), name='account_profile'),
]