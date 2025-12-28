from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand

from carwash.models import Booking, Washer


class Command(BaseCommand):
    help = 'Создает группу "Мойщики" с ограниченными правами доступа'  # noqa: E501

    def handle(self, *args, **options):
        # Создаем или получаем группу мойщиков
        group, created = Group.objects.get_or_create(name="Мойщики")

        if created:
            self.stdout.write(
                self.style.SUCCESS('Создана группа "Мойщики"')
            )
        else:
            self.stdout.write(
                self.style.WARNING('Группа "Мойщики" уже существует')
            )

        # Получаем права для модели Booking
        booking_ct = ContentType.objects.get_for_model(Booking)
        booking_permissions = Permission.objects.filter(
            content_type=booking_ct
        )

        # Добавляем права на просмотр (view) и изменение (change) записей
        try:
            view_permission = booking_permissions.get(
                codename="view_booking"
            )
            group.permissions.add(view_permission)
        except Permission.DoesNotExist:
            msg = (
                "Право view_booking не найдено. "
                "Запустите миграции: python manage.py migrate"
            )
            self.stdout.write(self.style.WARNING(msg))

        try:
            change_permission = booking_permissions.get(
                codename="change_booking"
            )
            group.permissions.add(change_permission)
        except Permission.DoesNotExist:
            self.stdout.write(
                self.style.WARNING("Право change_booking не найдено")
            )

        msg = (
            'Добавлены права на просмотр и изменение записей '
            'для группы "Мойщики"'
        )
        self.stdout.write(self.style.SUCCESS(msg))

        msg1 = "\nДля назначения мойщика в группу используйте админ-панель Django:"  # noqa: E501
        self.stdout.write(self.style.SUCCESS(msg1))
        msg2 = '1. Перейдите в раздел "Группы" в админ-панели'
        self.stdout.write(self.style.SUCCESS(msg2))
        msg3 = '2. Выберите группу "Мойщики"'
        self.stdout.write(self.style.SUCCESS(msg3))
        msg4 = "3. Добавьте пользователя-мойщика в эту группу"
        self.stdout.write(self.style.SUCCESS(msg4))
