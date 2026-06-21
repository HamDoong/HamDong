import threading
from django.core.management.base import BaseCommand

from ...infrastructure.rabbitmq_consumer import IdentityConsumer, GroupConsumer


class Command(BaseCommand):
    help = "Run combined event consumers for expense-service"

    def handle(self, *args, **options):
        # Start identity and group consumers in separate threads
        id_consumer = IdentityConsumer()
        grp_consumer = GroupConsumer()

        t1 = threading.Thread(target=id_consumer.start, daemon=True)
        t2 = threading.Thread(target=grp_consumer.start, daemon=True)

        t1.start()
        t2.start()

        self.stdout.write(self.style.SUCCESS("Started identity and group consumers (foreground). Press Ctrl+C to stop."))
        try:
            t1.join()
            t2.join()
        except KeyboardInterrupt:
            self.stdout.write("Shutting down consumers")
