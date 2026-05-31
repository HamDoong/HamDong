from django.core.management.base import BaseCommand, CommandError

from apps.settlements.application.recalculation_service import RecalculationService


class Command(BaseCommand):
    help = "Rebuild group balance snapshots"

    def add_arguments(self, parser):
        parser.add_argument("group_id", type=str)

    def handle(self, *args, **options):
        group_id = options.get("group_id")
        if not group_id:
            raise CommandError("group_id is required")
        RecalculationService().rebuild_group_balances(group_id)
        self.stdout.write(self.style.SUCCESS("Group balances rebuilt."))