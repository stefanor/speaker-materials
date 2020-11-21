from django.urls import path

from materials.views import EventDetailView, EventListView


urlpatterns = [
    path('', EventListView.as_view()),
    path('<slug:slug>/', EventDetailView.as_view(),
         name='materials.event_detail'),
]
