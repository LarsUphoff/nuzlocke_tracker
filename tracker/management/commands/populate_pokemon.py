import requests
from django.core.management.base import BaseCommand
from tracker.models import PokemonSpecies


class Command(BaseCommand):
    help = "Populates the PokemonSpecies model with German names from PokéAPI"

    def handle(self, *args, **options):
        self.stdout.write("Fetching Pokémon data from PokéAPI for German names...")
        limit = 1025
        base_species_url = f"https://pokeapi.co/api/v2/pokemon-species?limit={limit}"
        base_pokemon_url = "https://pokeapi.co/api/v2/pokemon/"

        try:
            response = requests.get(base_species_url)
            response.raise_for_status()
            species_list = response.json()["results"]

            count = 0
            created_count = 0
            skipped_count = 0

            for species_data in species_list:
                species_url = species_data["url"]
                try:
                    species_detail_response = requests.get(species_url)
                    species_detail_response.raise_for_status()
                    species_details = species_detail_response.json()

                    german_name = None
                    for name_info in species_details.get("names", []):
                        if name_info["language"]["name"] == "de":
                            german_name = name_info["name"]
                            break

                    if not german_name:
                        self.stdout.write(
                            self.style.WARNING(
                                f"No German name found for {species_data['name']}. Skipping."
                            )
                        )
                        skipped_count += 1
                        continue

                    pokedex_id = species_details["id"]

                    pokemon_detail_url = f"{base_pokemon_url}{pokedex_id}/"
                    pokemon_detail_response = requests.get(pokemon_detail_url)

                    type1 = None
                    type2 = None
                    sprite_url = None

                    if pokemon_detail_response.status_code == 200:
                        pokemon_details = pokemon_detail_response.json()
                        types = pokemon_details.get("types", [])
                        type1 = types[0]["type"]["name"] if len(types) > 0 else None
                        type2 = types[1]["type"]["name"] if len(types) > 1 else None
                        sprite_url = pokemon_details.get("sprites", {}).get(
                            "front_default"
                        )
                    else:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Could not fetch type/sprite details for ID {pokedex_id} ({german_name}). Status: {pokemon_detail_response.status_code}"
                            )
                        )

                    obj, created = PokemonSpecies.objects.update_or_create(
                        pokedex_id=pokedex_id,
                        defaults={
                            "name": german_name,
                            "type1": type1 if type1 else "unknown",
                            "type2": type2,
                            "sprite_url": sprite_url,
                        },
                    )

                    if created:
                        created_count += 1
                    count += 1
                    if count % 10 == 0:
                        self.stdout.write(f".", ending="")
                        self.stdout.flush()

                except requests.exceptions.RequestException as detail_e:
                    self.stderr.write(
                        self.style.ERROR(
                            f"\nError fetching details for {species_data['name']} from {species_url}: {detail_e}"
                        )
                    )
                except Exception as e:
                    self.stderr.write(
                        self.style.ERROR(
                            f"\nError processing {species_data['name']}: {e}"
                        )
                    )

            self.stdout.write(
                self.style.SUCCESS(
                    f"\nSuccessfully processed {count} Pokémon. Created {created_count} new entries. Skipped {skipped_count}. "
                )
            )

        except requests.exceptions.RequestException as e:
            self.stderr.write(
                self.style.ERROR(f"Error fetching Pokémon species list: {e}")
            )
