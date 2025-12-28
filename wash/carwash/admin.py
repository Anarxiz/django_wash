from django.contrib import admin

from .models import Service, Box, Washer, Client, Booking


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ["name", "price", "is_active", "created_at"]
    list_filter = ["is_active", "created_at"]
    search_fields = ["name", "description"]
    list_editable = ["is_active"]


@admin.register(Box)
class BoxAdmin(admin.ModelAdmin):
    list_display = ["box_number", "place_number", "is_active"]
    list_filter = ["box_number", "is_active"]
    list_editable = ["is_active"]


@admin.register(Washer)
class WasherAdmin(admin.ModelAdmin):
    list_display = ["get_full_name", "phone", "is_active", "created_at"]
    list_filter = ["is_active", "created_at"]
    search_fields = [
        "user__first_name",
        "user__last_name",
        "user__username",
        "phone",
    ]
    list_editable = ["is_active"]

    def get_full_name(self, obj):
        name = f"{obj.user.first_name} {obj.user.last_name}".strip()
        return name if name else obj.user.username

    get_full_name.short_description = "Имя"


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "phone",
        "is_regular",
        "discount_percent",
        "created_at",
    ]
    list_filter = ["is_regular", "created_at"]
    search_fields = ["name", "phone"]
    list_editable = ["is_regular", "discount_percent"]


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = [
        "client",
        "scheduled_time",
        "box",
        "washer",
        "status",
        "final_price",
        "created_at",
    ]
    list_filter = ["status", "box", "created_at", "scheduled_time"]
    search_fields = ["client__name", "client__phone"]
    date_hierarchy = "scheduled_time"
    filter_horizontal = ["services"]
    readonly_fields = [
        "base_price",
        "discount_amount",
        "final_price",
        "created_at",
        "created_by",
    ]

    fieldsets = (
        (
            "Основная информация",
            {
                "fields": (
                    "client",
                    "scheduled_time",
                    "duration_minutes",
                    "box",
                    "washer",
                    "status",
                )
            },
        ),
        ("Услуги", {"fields": ("services",)}),
        (
            "Цена",
            {"fields": ("base_price", "discount_amount", "final_price")},
        ),
        (
            "Дополнительно",
            {"fields": ("notes", "created_at", "created_by")},
        ),
    )

    def save_model(self, request, obj, form, change):
        if not change:  # Если создается новая запись
            obj.created_by = request.user
        # Валидация выполняется через clean() метод формы
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        """Пересчитываем цену после сохранения связанных объектов (услуг)"""
        super().save_related(request, form, formsets, change)
        obj = form.instance
        if obj.pk:  # Если объект сохранен
            # Пересчитываем цену (учитываются услуги и клиент со скидкой)
            obj.calculate_price()
            Booking.objects.filter(pk=obj.pk).update(
                base_price=obj.base_price,
                discount_amount=obj.discount_amount,
                final_price=obj.final_price,
            )
