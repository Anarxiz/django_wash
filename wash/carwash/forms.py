from datetime import timedelta

from django import forms

from .models import Booking, Client, Service, Box, Washer


class BookingForm(forms.ModelForm):
    """Форма для создания и редактирования записи"""

    client_name = forms.CharField(
        max_length=200,
        required=True,
        label="Имя клиента",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    client_phone = forms.CharField(
        max_length=20,
        required=True,
        label="Телефон",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    is_regular_client = forms.BooleanField(
        required=False,
        label="Постоянный клиент (скидка 10%)",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

    class Meta:
        model = Booking
        fields = [
            "services",
            "box",
            "washer",
            "scheduled_time",
            "duration_minutes",
            "status",
            "notes",
        ]
        widgets = {
            "services": forms.CheckboxSelectMultiple(),
            "box": forms.Select(attrs={"class": "form-control"}),
            "washer": forms.Select(attrs={"class": "form-control"}),
            "scheduled_time": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "duration_minutes": forms.NumberInput(
                attrs={"class": "form-control", "min": 1, "max": 480}
            ),
            "status": forms.Select(
                attrs={"class": "form-control"}),
            "notes": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["box"].queryset = Box.objects.filter(is_active=True)
        self.fields["washer"].queryset = Washer.objects.filter(is_active=True)
        self.fields["services"].queryset = Service.objects.filter(
            is_active=True)

        # Устанавливаем формат для datetime-local поля
        if (
            self.instance
            and self.instance.pk
            and self.instance.scheduled_time
        ):
            # Конвертируем в формат для datetime-local (YYYY-MM-DDTHH:MM)
            dt = self.instance.scheduled_time
            self.fields["scheduled_time"].widget.attrs["value"] = (
                dt.strftime("%Y-%m-%dT%H:%M")
            )

        # Если редактируем существующую запись, заполняем поля клиента
        if (
            self.instance
            and self.instance.pk
            and self.instance.client
        ):
            self.fields["client_name"].initial = self.instance.client.name
            self.fields["client_phone"].initial = self.instance.client.phone
            self.fields["is_regular_client"].initial = (
                self.instance.client.is_regular
            )

    def clean_client_phone(self):
        phone = self.cleaned_data.get("client_phone")
        # Можно добавить валидацию формата телефона
        return phone

    def clean(self):
        cleaned_data = super().clean()
        box = cleaned_data.get("box")
        washer = cleaned_data.get("washer")
        scheduled_time = cleaned_data.get("scheduled_time")
        duration_minutes = cleaned_data.get("duration_minutes", 60)

        if not scheduled_time:
            return cleaned_data

        # Проверка конфликта бокса
        if box:
            active_statuses = ["pending", "in_progress"]
            end_time = scheduled_time + timedelta(minutes=duration_minutes)

            conflicting_bookings = Booking.objects.filter(
                box=box, status__in=active_statuses
            ).exclude(pk=self.instance.pk if self.instance.pk else None)

            for booking in conflicting_bookings:
                booking_end = booking.get_end_time()
                if booking_end and (
                    scheduled_time < booking_end and
                    end_time > booking.scheduled_time
                ):
                    start_str = booking.scheduled_time.strftime(
                        "%d.%m.%Y %H:%M"
                    )
                    end_str = booking_end.strftime("%H:%M")
                    msg = (
                        f"Бокс {box} уже занят в это время "
                        f"(запись #{booking.pk}, {start_str} - {end_str})"
                    )
                    raise forms.ValidationError({"box": msg})

        # Проверка конфликта мойщика
        if washer:
            active_statuses = ["pending", "in_progress"]
            end_time = scheduled_time + timedelta(minutes=duration_minutes)

            conflicting_bookings = Booking.objects.filter(
                washer=washer, status__in=active_statuses
            ).exclude(pk=self.instance.pk if self.instance.pk else None)

            for booking in conflicting_bookings:
                booking_end = booking.get_end_time()
                if booking_end and (
                    scheduled_time < booking_end and
                    end_time > booking.scheduled_time
                ):
                    start_str = booking.scheduled_time.strftime(
                        "%d.%m.%Y %H:%M"
                    )
                    end_str = booking_end.strftime("%H:%M")
                    msg = (
                        f"Мойщик {washer} уже занят в это время "
                        f"(запись #{booking.pk}, {start_str} - {end_str})"
                    )
                    raise forms.ValidationError({"washer": msg})

        return cleaned_data

    def save(self, commit=True):
        """Переопределяем save для создания/обновления клиента"""
        booking = super().save(commit=False)

        client_name = self.cleaned_data["client_name"]
        client_phone = self.cleaned_data["client_phone"]
        is_regular = self.cleaned_data.get("is_regular_client", False)

        # Ищем существующего клиента по телефону или создаем нового
        client, created = Client.objects.get_or_create(
            phone=client_phone,
            defaults={
                "name": client_name,
                "is_regular": is_regular,
                "discount_percent": 10 if is_regular else 0,
            },
        )

        # Обновляем данные клиента, если он уже существовал
        if not created:
            client.name = client_name
            client.is_regular = is_regular
            client.discount_percent = 10 if is_regular else 0
            client.save()

        booking.client = client

        if commit:
            booking.save()
            self.save_m2m()

        return booking
