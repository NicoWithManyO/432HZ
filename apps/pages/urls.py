from django.urls import path

from .views import (
    ActusListView,
    AdhererView,
    AgendaListView,
    AssoView,
    ContactView,
    EventDetailView,
    HomeView,
    MentionsView,
    NewsDetailView,
)

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("agenda/", AgendaListView.as_view(), name="agenda"),
    path("agenda/<slug:slug>/", EventDetailView.as_view(), name="event-detail"),
    path("actus/", ActusListView.as_view(), name="actus"),
    path("actus/<slug:slug>/", NewsDetailView.as_view(), name="news-detail"),
    path("asso/", AssoView.as_view(), name="asso"),
    path("adherer/", AdhererView.as_view(), name="adherer"),
    path("contact/", ContactView.as_view(), name="contact"),
    path("mentions-legales/", MentionsView.as_view(), name="mentions"),
]
