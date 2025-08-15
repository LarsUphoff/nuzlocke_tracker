from django.core.management.base import BaseCommand
from tracker.models import Route


class Command(BaseCommand):
    help = "Populates the Route model with predefined locations in order"

    def handle(self, *args, **options):
        self.stdout.write("Creating routes in database...")

        routes = [
            "Starter",
            "Neuborkia",
            "Route 29",
            "Route 46",
            "Rosalia City",
            "Route 30",
            "Route 31",
            "Dunkelhöhle",
            "Viola City",
            "Knofensa-Turm",
            "Route 32",
            "Alph-Ruinen",
            "Einheitstunnel",
            "Route 33",
            "Azalea City",
            "Flegmon-Brunnen",
            "Ilex-Wald",
            "Route 34",
            "Dukatia City",
            "Route 35",
            "Nationalpark",
            "Route 36",
            "Route 37",
            "Teak City",
            "Turmruine",
            "Turm des Glockenspiels",
            "Route 38",
            "Route 39",
            "Oliviana City",
            "Route 40",
            "Route 41",
            "Strudelinseln",
            "Anemonia City",
            "Felsklippentor",
            "Route 47",
            "Felsklippenhöhle",
            "Route 48",
            "Safari-Zonen-Tor",
            "Safarizone",
            "Route 42",
            "Quarzberg",
            "Unterschlupf von Team Rocket",
            "See des Zorns",
            "Route 43",
            "Route 44",
            "Eispfad",
            "Ebenholz City",
            "Drachengrotte",
            "Route 45",
            "Route 27",
            "Tohjo-Fälle",
            "Route 26",
            "Siegstraße",
            "Indigo-Plateau",
            "Orania City",
            "Route 6",
            "Saffronia City",
            "Route 7",
            "Prismania City",
            "Route 16",
            "Route 17",
            "Route 18",
            "Fuchsania City",
            "Route 15",
            "Route 14",
            "Route 13",
            "Route 12",
            "Route 8",
            "Route 5",
            "Route 9",
            "Route 10",
            "Kraftwerk",
            "Route 24",
            "Route 25",
            "Azuria City",
            "Felsentunnel",
            "Route 4",
            "Route 11",
            "Digda-Höhle",
            "Marmoria City",
            "Route 3",
            "Mondberg",
            "Vertania-Wald",
            "Route 2",
            "Vertania City",
            "Route 1",
            "Alabastia",
            "Route 21",
            "Zinnoberinsel",
            "Route 20",
            "Route 19",
            "Route 22",
            "Route 28",
            "Berg Silber",
        ]

        created_count = 0
        skipped_count = 0

        for order, name in enumerate(routes):
            try:
                route, created = Route.objects.update_or_create(
                    name=name, defaults={"order": order}
                )

                if created:
                    created_count += 1
                    self.stdout.write(f"Created route: {name} (order: {order})")
                else:
                    self.stdout.write(f"Updated route: {name} (order: {order})")
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Error creating route {name}: {e}"))
                skipped_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"\nSuccessfully processed {len(routes)} routes. "
                f"Created {created_count} new routes, skipped {skipped_count}."
            )
        )
