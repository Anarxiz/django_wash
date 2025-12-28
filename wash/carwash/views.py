from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import BookingForm
from .models import Booking, Service, Box, Washer


def price_list(request):
    """Публичная страница с прайс-листом услуг"""
    services = Service.objects.filter(is_active=True).order_by("name")
    context = {
        "services": services,
    }
    return render(request, "carwash/price_list.html", context)


@login_required
def booking_list(request):
    """Список всех записей для администратора"""
    bookings = (
        Booking.objects.select_related("client", "box", "washer")
        .prefetch_related("services")
        .all()
    )

    # Фильтрация
    status_filter = request.GET.get("status")
    if status_filter:
        bookings = bookings.filter(status=status_filter)

    # Поиск
    search = request.GET.get("search")
    if search:
        bookings = bookings.filter(
            Q(client__name__icontains=search) | Q(client__phone__icontains=search)
        )

    context = {
        "bookings": bookings.order_by("-created_at", "-scheduled_time"),
        "status_choices": Booking.STATUS_CHOICES,
    }
    return render(request, "carwash/booking_list.html", context)


@login_required
def booking_create(request):
    """Создание новой записи"""
    if request.method == "POST":
        form = BookingForm(request.POST)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.created_by = request.user
            booking.save()
            form.save_m2m()  # Сохраняем ManyToMany связи (услуги)

            # Пересчитываем цену
            booking.calculate_price()
            booking.save()

            messages.success(
                request, f"Запись для {booking.client.name} успешно создана!"
            )
            return redirect("booking_list")
    else:
        form = BookingForm()

    context = {
        "form": form,
        "services": Service.objects.filter(is_active=True),
    }
    return render(request, "carwash/booking_form.html", context)


@login_required
def booking_edit(request, pk):
    """Редактирование записи (назначение мойщика и изменение статуса)"""
    booking = get_object_or_404(
        Booking.objects.prefetch_related("services"), pk=pk
    )

    if request.method == "POST":
        form = BookingForm(request.POST, instance=booking)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.save()
            form.save_m2m()  # Сохраняем ManyToMany связи (услуги)
            # Пересчитываем цену при изменении услуг
            booking.calculate_price()
            booking.save()
            messages.success(request, "Запись успешно обновлена!")
            return redirect("booking_list")
    else:
        form = BookingForm(instance=booking)

    context = {
        "form": form,
        "booking": booking,
        "services": Service.objects.filter(is_active=True),
    }
    return render(request, "carwash/booking_form.html", context)


@login_required
def booking_update_status(request, pk):
    """Быстрое изменение статуса заявки"""
    booking = get_object_or_404(Booking, pk=pk)

    if request.method == "POST":
        new_status = request.POST.get("status")
        if new_status in dict(Booking.STATUS_CHOICES):
            booking.status = new_status
            booking.save()
            messages.success(
                request, f'Статус заявки изменен на "{booking.get_status_display()}"'
            )
        else:
            messages.error(request, "Неверный статус")

    return redirect("booking_list")


@login_required
def booking_detail(request, pk):
    """Детальная информация о записи"""
    booking = get_object_or_404(
        Booking.objects.select_related(
            "client", "box", "washer", "created_by"
        ).prefetch_related("services"),
        pk=pk,
    )
    context = {
        "booking": booking,
    }
    return render(request, "carwash/booking_detail.html", context)


@login_required
def calculate_price(request):
    """API endpoint для расчета цены по услугам и скидке"""
    if request.method == "GET":
        service_ids = request.GET.getlist("services[]")
        is_regular = request.GET.get("is_regular", "false") == "true"

        services = Service.objects.filter(pk__in=service_ids, is_active=True)
        base_price = sum(service.price for service in services)

        discount_percent = 10 if is_regular else 0
        if is_regular:
            discount_amount = base_price * discount_percent / 100
        else:
            discount_amount = 0
        final_price = base_price - discount_amount

        return JsonResponse(
            {
                "base_price": float(base_price),
                "discount_percent": discount_percent,
                "discount_amount": float(discount_amount),
                "final_price": float(final_price),
            }
        )

    return JsonResponse({"error": "Invalid request"}, status=400)


@login_required
def dashboard(request):
    """Панель управления администратора"""
    today = timezone.now().date()

    today_bookings = Booking.objects.filter(
        scheduled_time__date=today
    ).select_related("client", "box", "washer")

    pending_bookings = (
        Booking.objects.filter(
            status="pending", scheduled_time__gte=timezone.now()
        )
        .select_related("client", "box")
        .order_by("scheduled_time")[:10]
    )

    active_washers = Washer.objects.filter(is_active=True)
    active_boxes = Box.objects.filter(is_active=True)

    context = {
        "today_bookings": today_bookings,
        "pending_bookings": pending_bookings,
        "active_washers": active_washers,
        "active_boxes": active_boxes,
    }
    return render(request, "carwash/dashboard.html", context)
