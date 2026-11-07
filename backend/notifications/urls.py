from django.urls import path

from .views import (
    AuthorityMessageCreateView,
    AuthorityMessageRecipientsView,
    NotificationDetailView,
    NotificationListView,
)

urlpatterns = [
    path('', NotificationListView.as_view(), name='notification-list'),
    path(
        'messages/',
        AuthorityMessageCreateView.as_view(),
        name='authority-message-create',
    ),
    path(
        'messages/recipients/',
        AuthorityMessageRecipientsView.as_view(),
        name='authority-message-recipients',
    ),
    path('<uuid:pk>/', NotificationDetailView.as_view(), name='notification-detail'),
]
