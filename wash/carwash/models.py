from datetime import timedelta

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models


class Service(models.Model):
    """Услуга автомойки"""

    name = models.CharField(max_length=200, verbose_name="Название услуги")
    description = models.TextField(blank=True, verbose_name="Описание")
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Цена",
        validators=[MinValueValidator(0)],
    )
    is_active = models.BooleanField(
        default=True, verbose_name="Активна"
    )
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name="Дата создания"
    )

    class Meta:
        verbose_name = "Услуга"
        verbose_name_plural = "Услуги"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Box(models.Model):
    """Бокс автомойки (2 бокса по 2 места)"""

    BOX_NUMBERS = [
        (1, "Бокс 1"),
        (2, "Бокс 2"),
    ]

    PLACE_NUMBERS = [
        (1, "Место 1"),
        (2, "Место 2"),
    ]

    box_number = models.IntegerField(
        choices=BOX_NUMBERS, verbose_name="Номер бокса"
    )
    place_number = models.IntegerField(
        choices=PLACE_NUMBERS, verbose_name="Номер места"
    )
    is_active = models.BooleanField(default=True, verbose_name="Активно")

    class Meta:
        verbose_name = "Бокс"
        verbose_name_plural = "Боксы"
        unique_together = [["box_number", "place_number"]]
        ordering = ["box_number", "place_number"]

    def __str__(self):
        return f"Бокс {self.box_number}, место {self.place_number}"


class Washer(models.Model):
    """Мойщик"""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        verbose_name="Пользователь",
        related_name="washer_profile",
    )
    phone = models.CharField(max_length=20, verbose_name="Телефон")
    is_active = models.BooleanField(
        default=True, verbose_name="Активен"
    )
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name="Дата добавления"
    )

    class Meta:
        verbose_name = "Мойщик"
        verbose_name_plural = "Мойщики"
        ordering = ["user__first_name", "user__last_name"]

    def __str__(self):
        name = f"{self.user.first_name} {self.user.last_name}".strip()
        return name if name else self.user.username


class Client(models.Model):
    """Клиент автомойки"""

    name = models.CharField(max_length=200, verbose_name="Имя клиента")
    phone = models.CharField(max_length=20, unique=True,
                             verbose_name="Телефон")
    is_regular = models.BooleanField(
        default=False, verbose_name="Постоянный клиент"
    )
    discount_percent = models.IntegerField(
        default=0,
        verbose_name="Процент скидки",
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name="Дата регистрации"
    )
    notes = models.TextField(blank=True, verbose_name="Заметки")

    class Meta:
        verbose_name = "Клиент"
        verbose_name_plural = "Клиенты"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.phone})"


class Booking(models.Model):
    """Запись клиента на мойку"""

    STATUS_CHOICES = [
        ("pending", "Ожидает"),
        ("in_progress", "В работе"),
        ("completed", "Завершена"),
        ("cancelled", "Отменена"),
    ]

    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        verbose_name="Клиент",
        related_name="bookings",
    )
    services = models.ManyToManyField(
        Service, verbose_name="Услуги", related_name="bookings"
    )
    box = models.ForeignKey(
        Box,
        on_delete=models.PROTECT,
        verbose_name="Бокс",
        related_name="bookings",
    )
    washer = models.ForeignKey(
        Washer,
        on_delete=models.PROTECT,
        verbose_name="Мойщик",
        related_name="bookings",
        null=True,
        blank=True,
    )
    scheduled_time = models.DateTimeField(verbose_name="Запланированное время")
    duration_minutes = models.IntegerField(
        default=60,
        verbose_name="Длительность (минут)",
        validators=[MinValueValidator(1), MaxValueValidator(480)],
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
        verbose_name="Статус",
    )
    base_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="Базовая цена",
    )
    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="Сумма скидки",
    )
    final_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="Итоговая цена",
    )
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name="Дата создания"
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Создано администратором",
        related_name="created_bookings",
    )
    notes = models.TextField(blank=True, verbose_name="Заметки")

    class Meta:
        verbose_name = "Запись"
        verbose_name_plural = "Записи"
        ordering = ["-scheduled_time", "-created_at"]

    def __str__(self):
        date_str = self.scheduled_time.strftime("%d.%m.%Y %H:%M")
        return f"{self.client.name} - {date_str}"

    def get_end_time(self):
        """Получить время окончания записи"""
        if self.scheduled_time:
            return self.scheduled_time + timedelta(minutes=self.duration_minutes)
        return None

    @property
    def end_time(self):
        """Свойство для времени окончания (для использования в шаблонах)"""
        return self.get_end_time()

    def calculate_price(self):
        """Вычисление итоговой цены с учетом скидки"""
        self.base_price = sum(
            service.price for service in self.services.all()
        )
        if self.client.is_regular and self.client.discount_percent > 0:
            self.discount_amount = (
                self.base_price * self.client.discount_percent / 100
            )
        else:
            self.discount_amount = 0
        self.final_price = self.base_price - self.discount_amount
        return self.final_price

    def check_box_conflict(self):
        """Проверка конфликта времени для бокса"""
        if not self.scheduled_time or not self.box:
            return

        # Исключаем завершенные и отмененные записи
        active_statuses = ["pending", "in_progress"]
        end_time = self.get_end_time()

        conflicting_bookings = Booking.objects.filter(
            box=self.box, status__in=active_statuses
        ).exclude(pk=self.pk if self.pk else None)

        # Проверяем пересечение интервалов времени
        for booking in conflicting_bookings:
            booking_end = booking.get_end_time()
            # Проверяем пересечение интервалов
            if (
                self.scheduled_time < booking_end
                and end_time > booking.scheduled_time
            ):
                start_str = booking.scheduled_time.strftime("%d.%m.%Y %H:%M")
                end_str = booking_end.strftime("%H:%M")
                msg = (
                    f"Бокс {self.box} уже занят в это время "
                    f"(запись #{booking.pk}, {start_str} - {end_str})"
                )
                raise ValidationError({"box": msg})

    def check_washer_conflict(self):
        """Проверка конфликта времени для мойщика"""
        if not self.scheduled_time or not self.washer:
            return

        # Исключаем завершенные и отмененные записи
        active_statuses = ["pending", "in_progress"]
        end_time = self.get_end_time()

        conflicting_bookings = Booking.objects.filter(
            washer=self.washer, status__in=active_statuses
        ).exclude(pk=self.pk if self.pk else None)

        # Проверяем пересечение интервалов времени
        for booking in conflicting_bookings:
            booking_end = booking.get_end_time()
            # Проверяем пересечение интервалов
            if (
                self.scheduled_time < booking_end
                and end_time > booking.scheduled_time
            ):
                start_str = booking.scheduled_time.strftime("%d.%m.%Y %H:%M")
                end_str = booking_end.strftime("%H:%M")
                msg = (
                    f"Мойщик {self.washer} уже занят в это время "
                    f"(запись #{booking.pk}, {start_str} - {end_str})"
                )
                raise ValidationError({"washer": msg})

    def clean(self):
        """Валидация модели"""
        super().clean()
        # Проверки конфликтов выполняются только если объект
        # имеет все необходимые поля
        if self.pk and self.box and self.scheduled_time:
            self.check_box_conflict()
        if self.pk and self.washer and self.scheduled_time:
            self.check_washer_conflict()

    def save(self, *args, **kwargs):
        """Переопределяем save для валидации"""
        # Не вызываем full_clean здесь, чтобы избежать проблем
        # при создании через форму
        super().save(*args, **kwargs)
