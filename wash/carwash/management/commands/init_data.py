from django.core.management.base import BaseCommand

from carwash.models import Box, Service


class Command(BaseCommand):
    help = (
        "Создает начальные данные: боксы (2 бокса по 2 места) "
        "и примерные услуги"
    )

    def handle(self, *args, **options):
        # Создаем боксы
        boxes_created = 0
        for box_num in [1, 2]:
            for place_num in [1, 2]:
                box, created = Box.objects.get_or_create(
                    box_number=box_num,
                    place_number=place_num,
                    defaults={"is_active": True},
                )
                if created:
                    boxes_created += 1
                    self.stdout.write(
                        self.style.SUCCESS(f"Создан {box}")
                    )

        if boxes_created == 0:
            self.stdout.write(self.style.WARNING("Боксы уже существуют"))
        else:
            self.stdout.write(
                self.style.SUCCESS(f"Создано боксов: {boxes_created}")
            )

        # Создаем примерные услуги
        services_data = [
            {
                "name": "Мойка кузова",
                "description": "Стандартная мойка кузова автомобиля",
                "price": 500.00,
            },
            {
                "name": "Мойка кузова + сушка",
                "description": "Мойка кузова с последующей сушкой",
                "price": 700.00,
            },
            {
                "name": "Чистка салона",
                "description": "Влажная уборка салона автомобиля",
                "price": 1000.00,
            },
            {
                "name": "Комплексная мойка",
                "description": "Мойка кузова + сушка + чистка салона",
                "price": 1500.00,
            },
            {
                "name": "Полировка кузова",
                "description": "Полировка кузова автомобиля",
                "price": 2000.00,
            },
        ]

        services_created = 0
        for service_data in services_data:
            service, created = Service.objects.get_or_create(
                name=service_data["name"], defaults=service_data
            )
            if created:
                services_created += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Создана услуга: {service.name} - {service.price} руб"
                    )
                )

        if services_created == 0:
            self.stdout.write(self.style.WARNING("Услуги уже существуют"))
        else:
            self.stdout.write(
                self.style.SUCCESS(f"Создано услуг: {services_created}")
            )

        self.stdout.write(
            self.style.SUCCESS("\nИнициализация данных завершена!")
        )
