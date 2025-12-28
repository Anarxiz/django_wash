from django.urls import path
from . import views

urlpatterns = [
    path("", views.price_list, name="price_list"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("bookings/", views.booking_list, name="booking_list"),
    path("bookings/create/", views.booking_create, name="booking_create"),
    path("bookings/<int:pk>/", views.booking_detail, name="booking_detail"),
    path("bookings/<int:pk>/edit/", views.booking_edit, name="booking_edit"),
    path(
        "bookings/<int:pk>/update-status/",
        views.booking_update_status,
        name="booking_update_status",
    ),
    path("api/calculate-price/", views.calculate_price, name="calculate_price"),
]
