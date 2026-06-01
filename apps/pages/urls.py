from django.urls import path

from .views import (
    ActusListView,
    AgendaListView,
    EventDetailView,
    HomeView,
    NewsDetailView,
)

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("agenda/", AgendaListView.as_view(), name="agenda"),
    path("agenda/<slug:slug>/", EventDetailView.as_view(), name="event-detail"),
    path("actus/", ActusListView.as_view(), name="actus"),
    path("actus/<slug:slug>/", NewsDetailView.as_view(), name="news-detail"),
]
