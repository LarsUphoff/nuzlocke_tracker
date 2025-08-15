from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseNotAllowed, HttpResponse
from django.views.decorators.http import require_POST
from django.db.models import Q, Min, Max
import requests
from django.core.cache import cache
from django.db import transaction
import json
from django.db import IntegrityError


from .models import Player, Route, Encounter, PokemonSpecies, PlayerType
from .forms import EncounterForm


TYPE_NAMES_CACHE_KEY = "german_type_names_map"
TYPE_EFFECTIVENESS_CACHE_KEY = "pokemon_type_effectiveness_{}"

TYPE_COLORS_EN = {
    "normal": "#A8A77A",
    "fire": "#EE8130",
    "water": "#6390F0",
    "electric": "#F7D02C",
    "grass": "#7AC74C",
    "ice": "#96D9D6",
    "fighting": "#C22E28",
    "poison": "#A33EA1",
    "ground": "#E2BF65",
    "flying": "#A98FF3",
    "psychic": "#F95587",
    "bug": "#A6B91A",
    "rock": "#B6A136",
    "ghost": "#735797",
    "dragon": "#6F35FC",
    "dark": "#705746",
    "steel": "#B7B7CE",
    "fairy": "#D685AD",
    "unknown": "#68A090",
    "shadow": "#605A55",
    "stellar": "#44A0DA",
}

EXCLUDED_TYPES = ["unknown", "shadow", "stellar"]


def get_german_type_names():
    german_names_map = cache.get(TYPE_NAMES_CACHE_KEY)
    if german_names_map:
        return german_names_map

    german_names_map = {}
    all_types_results = []
    try:
        all_types_response = requests.get("https://pokeapi.co/api/v2/type?limit=100")
        all_types_response.raise_for_status()
        all_types_results = all_types_response.json()["results"]

        for type_info in all_types_results:
            english_name = type_info["name"]
            if english_name in EXCLUDED_TYPES:
                continue

            type_url = type_info["url"]
            type_detail_response = requests.get(type_url)
            type_detail_response.raise_for_status()
            type_details = type_detail_response.json()

            german_name = english_name.capitalize()
            for name_data in type_details.get("names", []):
                if name_data["language"]["name"] == "de":
                    german_name = name_data["name"]
                    break
            german_names_map[english_name] = german_name

        cache.set(TYPE_NAMES_CACHE_KEY, german_names_map, timeout=60 * 60 * 24)
        return german_names_map

    except requests.exceptions.RequestException as e:
        print(f"Error fetching German type names from PokéAPI: {e}")
        return {
            t["name"]: t["name"].capitalize()
            for t in all_types_results
            if t["name"] not in EXCLUDED_TYPES
        }
    except Exception as e:
        print(f"Unexpected error in get_german_type_names: {e}")
        return {}


def get_pokemon_types(pokemon_name_or_id):
    try:
        response = requests.get(
            f"https://pokeapi.co/api/v2/pokemon/{pokemon_name_or_id.lower()}"
        )
        response.raise_for_status()
        data = response.json()
        types = [t["type"]["name"] for t in data["types"]]
        return types
    except requests.exceptions.RequestException as e:
        print(f"Error fetching from PokéAPI: {e}")
        return None


def get_type_effectiveness(pokemon_id):
    cache_key = TYPE_EFFECTIVENESS_CACHE_KEY.format(pokemon_id)
    cached_data = cache.get(cache_key)
    if cached_data:
        return cached_data

    try:
        german_type_map = get_german_type_names()
        if not german_type_map:
            print("Error: German type map is empty.")
            return None

        poke_response = requests.get(f"https://pokeapi.co/api/v2/pokemon/{pokemon_id}")
        poke_response.raise_for_status()
        poke_data = poke_response.json()
        type_urls = [t["type"]["url"] for t in poke_data["types"]]
        pokemon_types_en = [t["type"]["name"] for t in poke_data["types"]]
        pokemon_types_de = [
            german_type_map.get(t, t.capitalize())
            for t in pokemon_types_en
            if t not in EXCLUDED_TYPES
        ]

        damage_relations_list = []
        for type_url in type_urls:
            type_response = requests.get(type_url)
            type_response.raise_for_status()
            damage_relations_list.append(type_response.json()["damage_relations"])

        all_attacking_types_en = list(german_type_map.keys())

        effectiveness_by_multiplier = {
            "4": [],
            "2": [],
            "1": [],
            "0.5": [],
            "0.25": [],
            "0": [],
        }

        for attack_type_en in all_attacking_types_en:
            multiplier = 1.0
            for relations in damage_relations_list:
                current_multiplier = 1.0
                if any(
                    t["name"] == attack_type_en for t in relations["double_damage_from"]
                ):
                    current_multiplier = 2.0
                elif any(
                    t["name"] == attack_type_en for t in relations["half_damage_from"]
                ):
                    current_multiplier = 0.5
                elif any(
                    t["name"] == attack_type_en for t in relations["no_damage_from"]
                ):
                    current_multiplier = 0.0
                multiplier *= current_multiplier

            attack_type_de = german_type_map.get(attack_type_en)
            if not attack_type_de:
                print(
                    f"Warning: English type '{attack_type_en}' not found in german_type_map during effectiveness calculation."
                )
                continue

            if multiplier == 4.0:
                effectiveness_by_multiplier["4"].append(attack_type_de)
            elif multiplier == 2.0:
                effectiveness_by_multiplier["2"].append(attack_type_de)
            elif multiplier == 1.0:
                effectiveness_by_multiplier["1"].append(attack_type_de)
            elif multiplier == 0.5:
                effectiveness_by_multiplier["0.5"].append(attack_type_de)
            elif multiplier == 0.25:
                effectiveness_by_multiplier["0.25"].append(attack_type_de)
            elif multiplier == 0.0:
                effectiveness_by_multiplier["0"].append(attack_type_de)

        for key in effectiveness_by_multiplier:
            effectiveness_by_multiplier[key].sort()

        result = {
            "pokemon_types": pokemon_types_de,
            "effectiveness": effectiveness_by_multiplier,
        }

        cache.set(cache_key, result, timeout=60 * 60 * 24 * 7)
        return result

    except requests.exceptions.RequestException as e:
        print(
            f"Error fetching type effectiveness from PokéAPI for ID {pokemon_id}: {e}"
        )
        return None
    except Exception as e:
        print(
            f"An unexpected error occurred in get_type_effectiveness for ID {pokemon_id}: {e}"
        )
        return None


def tracker_view(request):
    if request.method == "GET":
        players = Player.objects.all()
        routes = Route.objects.all().order_by("order", "name")
        encounters = Encounter.objects.select_related(
            "player", "route", "pokemon_species"
        ).all()
        encounter_map = {
            route: {player: None for player in players} for route in routes
        }
        for encounter in encounters:
            if (
                encounter.route in encounter_map
                and encounter.player in encounter_map[encounter.route]
            ):
                encounter_map[encounter.route][encounter.player] = encounter
        encounter_form = EncounterForm()
        context = {
            "players": players,
            "routes": routes,
            "encounter_map": encounter_map,
            "encounter_form": encounter_form,
            "active_tab": "tracker",
        }
        return render(request, "tracker/tracker.html", context)

    elif request.method == "POST":
        is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
        action = request.POST.get("action")
        player_id = request.POST.get("player")
        route_id = request.POST.get("route")

        if action == "add_route":
            if not is_ajax:
                return HttpResponseNotAllowed(["POST"])

            route_name = request.POST.get("route_name", "").strip()
            if not route_name:
                return JsonResponse(
                    {"status": "error", "message": "Routenname darf nicht leer sein."},
                    status=400,
                )

            try:
                min_order = Route.objects.aggregate(Min("order"))["order__min"]
                new_order = (min_order - 1) if min_order is not None else 0

                new_route = Route.objects.create(name=route_name, order=new_order)

                players = Player.objects.all()
                for player in players:
                    Encounter.objects.create(player=player, route=new_route, status="-")

                return JsonResponse(
                    {
                        "status": "success",
                        "message": f'Route "{route_name}" hinzugefügt.',
                        "route_id": new_route.id,
                        "route_name": new_route.name,
                        "route_order": new_route.order,
                    }
                )
            except IntegrityError:
                return JsonResponse(
                    {
                        "status": "error",
                        "message": f'Route "{route_name}" existiert bereits.',
                    },
                    status=400,
                )
            except Exception as e:
                print(f"Error adding route: {e}")
                return JsonResponse(
                    {
                        "status": "error",
                        "message": f"Fehler beim Hinzufügen der Route: {str(e)}",
                    },
                    status=500,
                )

        elif action == "reset_run":
            if not is_ajax:
                return HttpResponseNotAllowed(["POST"])

            try:
                with transaction.atomic():
                    deleted_encounters_count, _ = Encounter.objects.all().delete()
                    deleted_routes_count, _ = Route.objects.filter(
                        order__lt=-1
                    ).delete()

                    return JsonResponse(
                        {
                            "status": "success",
                            "message": f"{deleted_encounters_count} Encounter und {deleted_routes_count} benutzerdefinierte Routen wurden zurückgesetzt.",
                        }
                    )
            except Exception as e:
                print(f"Error resetting run: {e}")
                return JsonResponse(
                    {
                        "status": "error",
                        "message": f"Fehler beim Zurücksetzen des Runs: {str(e)}",
                    },
                    status=500,
                )

        elif action == "export_run":
            if not is_ajax:
                return HttpResponseNotAllowed(["POST"])

            try:
                encounters = Encounter.objects.select_related(
                    "player", "route", "pokemon_species"
                ).all()

                export_data = []
                for encounter in encounters:
                    encounter_data = {
                        "player_name": encounter.player.name,
                        "route_name": encounter.route.name,
                        "status": encounter.status,
                        "nickname": encounter.nickname,
                        "pokemon_name": encounter.pokemon_species.name
                        if encounter.pokemon_species
                        else None,
                    }
                    export_data.append(encounter_data)

                return JsonResponse({"status": "success", "data": export_data})
            except Exception as e:
                print(f"Error exporting run: {e}")
                return JsonResponse(
                    {
                        "status": "error",
                        "message": f"Fehler beim Exportieren des Runs: {str(e)}",
                    },
                    status=500,
                )

        elif action == "import_run":
            if not is_ajax:
                return HttpResponseNotAllowed(["POST"])

            try:
                import_data = json.loads(request.POST.get("import_data", "[]"))
                if not import_data:
                    return JsonResponse(
                        {"status": "error", "message": "Keine Daten zum Importieren."},
                        status=400,
                    )

                with transaction.atomic():
                    success_count = 0
                    error_count = 0

                    for item in import_data:
                        try:
                            player_name = item.get("player_name")
                            route_name = item.get("route_name")
                            pokemon_name = item.get("pokemon_name")

                            if not player_name or not route_name:
                                error_count += 1
                                continue

                            player, _ = Player.objects.get_or_create(name=player_name)

                            try:
                                route = Route.objects.get(name=route_name)
                            except Route.DoesNotExist:
                                error_count += 1
                                continue

                            pokemon_species = None
                            if pokemon_name:
                                try:
                                    pokemon_species = PokemonSpecies.objects.get(
                                        name__iexact=pokemon_name
                                    )
                                except PokemonSpecies.DoesNotExist:
                                    pass

                            import_status = item.get("status")
                            if import_status == "verpasst":
                                import_status = "-"
                            elif not import_status:
                                import_status = "-"

                            encounter, created = Encounter.objects.update_or_create(
                                player=player,
                                route=route,
                                defaults={
                                    "pokemon_species": pokemon_species,
                                    "nickname": item.get("nickname"),
                                    "status": import_status,
                                },
                            )

                            success_count += 1

                        except Exception as e:
                            print(f"Error importing item {item}: {e}")
                            error_count += 1

                    return JsonResponse(
                        {
                            "status": "success",
                            "message": f"{success_count} Encounters erfolgreich importiert. {error_count} Fehler.",
                        }
                    )

            except json.JSONDecodeError:
                return JsonResponse(
                    {"status": "error", "message": "Ungültiges JSON-Format."},
                    status=400,
                )

            except Exception as e:
                print(f"Error importing run: {e}")
                return JsonResponse(
                    {
                        "status": "error",
                        "message": f"Fehler beim Importieren des Runs: {str(e)}",
                    },
                    status=500,
                )

        elif action == "reset_route":
            if not is_ajax:
                return HttpResponseNotAllowed(["POST"])
            try:
                with transaction.atomic():
                    deleted_count, _ = Encounter.objects.filter(
                        route_id=route_id
                    ).delete()
                return JsonResponse(
                    {
                        "status": "success",
                        "message": f"{deleted_count} Einträge zurückgesetzt.",
                    }
                )
            except Exception as e:
                print(f"Error resetting route {route_id}: {e}")
                return JsonResponse(
                    {
                        "status": "error",
                        "message": "Fehler beim Zurücksetzen der Route.",
                    },
                    status=500,
                )

        elif action == "kill_route":
            if not is_ajax:
                return HttpResponseNotAllowed(["POST"])
            try:
                with transaction.atomic():
                    updated_count = Encounter.objects.filter(
                        route_id=route_id, pokemon_species__isnull=False
                    ).update(status="tot")
                return JsonResponse(
                    {
                        "status": "success",
                        "message": f"{updated_count} Pokémon auf Tot gesetzt.",
                    }
                )
            except Exception as e:
                print(f"Error killing route {route_id}: {e}")
                return JsonResponse(
                    {
                        "status": "error",
                        "message": "Fehler beim Aktualisieren des Status für die Route.",
                    },
                    status=500,
                )

        elif action == "fail_route":
            if not is_ajax:
                return HttpResponseNotAllowed(["POST"])
            try:
                with transaction.atomic():
                    updated_count = Encounter.objects.filter(route_id=route_id).update(
                        status="verkackt", pokemon_species=None, nickname=""
                    )
                return JsonResponse(
                    {
                        "status": "success",
                        "message": f"{updated_count} Einträge auf Verkackt gesetzt.",
                    }
                )
            except Exception as e:
                print(f"Error failing route {route_id}: {e}")
                return JsonResponse(
                    {
                        "status": "error",
                        "message": "Fehler beim Setzen auf Verkackt für die Route.",
                    },
                    status=500,
                )

        elif action == "delete_route":
            if not is_ajax:
                return HttpResponseNotAllowed(["POST"])
            if not route_id:
                return JsonResponse(
                    {"status": "error", "message": "Route ID fehlt."}, status=400
                )
            try:
                route_to_delete = get_object_or_404(Route, pk=route_id)
                route_name = route_to_delete.name
                with transaction.atomic():
                    route_to_delete.delete()
                return JsonResponse(
                    {
                        "status": "success",
                        "message": f'Route "{route_name}" erfolgreich gelöscht.',
                    }
                )
            except Route.DoesNotExist:
                return JsonResponse(
                    {"status": "error", "message": "Route nicht gefunden."}, status=404
                )
            except Exception as e:
                print(f"Error deleting route {route_id}: {e}")
                return JsonResponse(
                    {"status": "error", "message": "Fehler beim Löschen der Route."},
                    status=500,
                )

        elif action == "reset":
            if not player_id:
                message = "Player ID fehlt für Einzel-Reset."
                if is_ajax:
                    return JsonResponse(
                        {"status": "error", "message": message}, status=400
                    )
                else:
                    print(message)
                    return redirect("tracker_view")

            instance = None
            try:
                instance = Encounter.objects.get(player_id=player_id, route_id=route_id)
                instance.delete()
                if is_ajax:
                    return JsonResponse({"status": "reset_success", "new_status": "-"})
                else:
                    return redirect("tracker_view")
            except Encounter.DoesNotExist:
                if is_ajax:
                    return JsonResponse(
                        {
                            "status": "reset_success",
                            "message": "Bereits entfernt.",
                            "new_status": "-",
                        }
                    )
                else:
                    return redirect("tracker_view")
            except Exception as e:
                print(
                    f"Error resetting encounter (Player: {player_id}, Route: {route_id}): {e}"
                )
                if is_ajax:
                    return JsonResponse(
                        {"status": "error", "message": "Fehler beim Zurücksetzen."},
                        status=500,
                    )
                else:
                    return redirect("tracker_view")

        elif action == "save":
            if not player_id:
                message = "Player ID fehlt für Speichern."
                if is_ajax:
                    return JsonResponse(
                        {"status": "error", "message": message}, status=400
                    )
                else:
                    print(message)
                    return redirect("tracker_view")

            instance = None
            try:
                instance = Encounter.objects.get(player_id=player_id, route_id=route_id)
            except Encounter.DoesNotExist:
                instance = None

            form = EncounterForm(request.POST, instance=instance)
            if form.is_valid():
                try:
                    # Clear Pokemon data when status is verkackt or -
                    if form.cleaned_data["status"] in ["-", "verkackt"]:
                        form.instance.pokemon_species = None
                        form.instance.nickname = ""

                    saved_instance = form.save()
                    if is_ajax:
                        response_data = {
                            "status": "success",
                            "pokemon_species_id": saved_instance.pokemon_species_id
                            if saved_instance.pokemon_species
                            else "",
                            "status_value": saved_instance.status,
                        }
                        return JsonResponse(response_data)
                    else:
                        return redirect("tracker_view")
                except Exception as e:
                    print(
                        f"Error saving encounter (Player: {player_id}, Route: {route_id}): {e}"
                    )
                    if is_ajax:
                        return JsonResponse(
                            {"status": "error", "message": "Fehler beim Speichern."},
                            status=500,
                        )
                    else:
                        return redirect("tracker_view")
            else:
                if is_ajax:
                    error_dict = (
                        form.errors.get_json_data()
                        if hasattr(form.errors, "get_json_data")
                        else {"__all__": form.errors.as_text()}
                    )
                    if "pokemon_name" in error_dict and form.cleaned_data.get(
                        "status"
                    ) in ["-", "verkackt"]:
                        error_dict["pokemon_name"] = [
                            {
                                "message": "Pokémon nicht gefunden, aber Status ist OK.",
                                "code": "",
                            }
                        ]

                    return JsonResponse(
                        {"status": "error", "errors": error_dict}, status=400
                    )
                else:
                    print(
                        f"Form errors (non-AJAX) for Player {player_id}, Route {route_id}:",
                        form.errors,
                    )
                    return redirect("tracker_view")

        else:
            message = f"Unbekannte Aktion: {action}"
            if is_ajax:
                return JsonResponse({"status": "error", "message": message}, status=400)
            else:
                print(message)
                return redirect("tracker_view")

    return HttpResponseNotAllowed(["GET", "POST"])


def boss_view(request):
    boss_list = [
        {
            "num": 1,
            "region": "Johto",
            "name": "Falk",
            "location": "Viola City",
            "number_of_pokemon": 2,
            "level_cap": 13,
        },
        {
            "num": 2,
            "region": "Johto",
            "name": "Kai",
            "location": "Azalea City",
            "number_of_pokemon": 3,
            "level_cap": 17,
        },
        {
            "num": 3,
            "region": "Johto",
            "name": "Bianka",
            "location": "Dukatia City",
            "number_of_pokemon": 2,
            "level_cap": 19,
        },
        {
            "num": 4,
            "region": "Johto",
            "name": "Jens",
            "location": "Teak City",
            "number_of_pokemon": 4,
            "level_cap": 25,
        },
        {
            "num": 5,
            "region": "Johto",
            "name": "Hartwig",
            "location": "Anemonia City",
            "number_of_pokemon": 2,
            "level_cap": 31,
        },
        {
            "num": 6,
            "region": "Johto",
            "name": "Jasmin",
            "location": "Oliviana City",
            "number_of_pokemon": 3,
            "level_cap": 35,
        },
        {
            "num": 7,
            "region": "Johto",
            "name": "Norbert",
            "location": "Mahagonia City",
            "number_of_pokemon": 3,
            "level_cap": 34,
        },
        {
            "num": 8,
            "region": "Johto",
            "name": "Sandra",
            "location": "Ebenholz City",
            "number_of_pokemon": 4,
            "level_cap": 41,
        },
        {
            "num": 1,
            "region": "Top 4",
            "name": "Willi",
            "location": "Indigo Plateau",
            "number_of_pokemon": 5,
            "level_cap": 42,
        },
        {
            "num": 2,
            "region": "Top 4",
            "name": "Koga",
            "location": "Indigo Plateau",
            "number_of_pokemon": 5,
            "level_cap": 44,
        },
        {
            "num": 3,
            "region": "Top 4",
            "name": "Bruno",
            "location": "Indigo Plateau",
            "number_of_pokemon": 5,
            "level_cap": 46,
        },
        {
            "num": 4,
            "region": "Top 4",
            "name": "Melanie",
            "location": "Indigo Plateau",
            "number_of_pokemon": 5,
            "level_cap": 47,
        },
        {
            "num": 5,
            "region": "Top 4",
            "name": "Siegfried",
            "location": "Indigo Plateau",
            "number_of_pokemon": 6,
            "level_cap": 50,
        },
        {
            "num": 1,
            "region": "Kanto",
            "name": "Major Bob",
            "location": "Orania City",
            "number_of_pokemon": 5,
            "level_cap": 53,
        },
        {
            "num": 2,
            "region": "Kanto",
            "name": "Sabrina",
            "location": "Saffronia City",
            "number_of_pokemon": 3,
            "level_cap": 55,
        },
        {
            "num": 3,
            "region": "Kanto",
            "name": "Erika",
            "location": "Prismania City",
            "number_of_pokemon": 4,
            "level_cap": 56,
        },
        {
            "num": 4,
            "region": "Kanto",
            "name": "Janina",
            "location": "Fuchsania City",
            "number_of_pokemon": 5,
            "level_cap": 50,
        },
        {
            "num": 5,
            "region": "Kanto",
            "name": "Misty",
            "location": "Azuria City",
            "number_of_pokemon": 4,
            "level_cap": 54,
        },
        {
            "num": 6,
            "region": "Kanto",
            "name": "Rocko",
            "location": "Marmoria City",
            "number_of_pokemon": 5,
            "level_cap": 54,
        },
        {
            "num": 7,
            "region": "Kanto",
            "name": "Pyro",
            "location": "Seeschauminseln",
            "number_of_pokemon": 3,
            "level_cap": 59,
        },
        {
            "num": 8,
            "region": "Kanto",
            "name": "Blau",
            "location": "Vertania City",
            "number_of_pokemon": 6,
            "level_cap": 60,
        },
        {
            "num": 9,
            "region": "Kanto",
            "name": "Rot",
            "location": "Silberberg",
            "number_of_pokemon": 6,
            "level_cap": 88,
        },
    ]
    context = {
        "bosses": boss_list,
        "active_tab": "bosse",
    }
    return render(request, "tracker/bosses.html", context)


def strength_weakness_view(request):
    error = None
    pokemon_name_input = request.GET.get("pokemon_name", "").strip()
    pokemon_info = None
    display_name = pokemon_name_input
    type_colors_de = {}
    sprite_url = None

    german_type_map = get_german_type_names()

    if german_type_map:
        for en_name, de_name in german_type_map.items():
            color = TYPE_COLORS_EN.get(en_name, "#68A090")
            type_colors_de[de_name] = color
    else:
        error = "Fehler beim Laden der deutschen Typennamen von der API."

    if pokemon_name_input and not error:
        try:
            species = PokemonSpecies.objects.get(name__iexact=pokemon_name_input)
            display_name = species.name.capitalize()
            pokedex_id = species.pokedex_id
            sprite_url = species.sprite_url

            pokemon_info = get_type_effectiveness(pokedex_id)

            if pokemon_info is None and not error:
                error = f"Konnte Effektivitäten für {display_name} (ID: {pokedex_id}) nicht von PokéAPI abrufen."

        except PokemonSpecies.DoesNotExist:
            error = f"Pokémon '{pokemon_name_input}' nicht in der lokalen Datenbank gefunden. Stelle sicher, dass die Datenbank aktuell ist und der Name korrekt geschrieben wurde."
        except Exception as e:
            error = f"Ein unerwarteter Fehler ist aufgetreten: {e}"
            print(f"Error in strength_weakness_view for '{pokemon_name_input}': {e}")

    context = {
        "pokemon_name": pokemon_name_input,
        "display_name": display_name
        if pokemon_info or sprite_url
        else pokemon_name_input,
        "pokemon_info": pokemon_info,
        "error": error,
        "active_tab": "schwaechen",
        "multiplier_order": ["0", "0.25", "0.5", "1", "2", "4"],
        "type_colors_de": type_colors_de,
        "sprite_url": sprite_url,
    }
    return render(request, "tracker/strength_weakness.html", context)


def status_summary_view(request):
    players = Player.objects.all()
    summary = {}
    for player in players:
        summary[player] = {
            "lebendig": Encounter.objects.filter(
                player=player,
                status="gefangen",
            ).select_related("pokemon_species", "route"),
            "tot": Encounter.objects.filter(player=player, status="tot").select_related(
                "pokemon_species", "route"
            ),
        }

    context = {
        "summary": summary,
        "active_tab": "tot_lebendig",
    }
    return render(request, "tracker/status_summary.html", context)


def player_types_view(request):
    if request.method == "POST":
        if not request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return HttpResponseNotAllowed(["POST"])

        action = request.POST.get("action")
        player_id = request.POST.get("player_id")
        type_name = request.POST.get("type_name")
        assignment_id = request.POST.get("assignment_id")

        if action == "assign_type":
            if not all([player_id, type_name]):
                return JsonResponse(
                    {
                        "status": "error",
                        "message": "Spieler-ID und Typenname sind erforderlich.",
                    },
                    status=400,
                )
            try:
                player = get_object_or_404(Player, pk=player_id)
                german_type_map = get_german_type_names()
                if not german_type_map:
                    return JsonResponse(
                        {
                            "status": "error",
                            "message": "Fehler beim Laden der Typen-Informationen von der API.",
                        },
                        status=500,
                    )

                if type_name not in german_type_map.values():
                    return JsonResponse(
                        {
                            "status": "error",
                            "message": f"Ungültiger Typenname: {type_name}. Gültige Typen: {list(german_type_map.values())}",
                        },
                        status=400,
                    )

                existing_assignment = PlayerType.objects.filter(
                    type_name=type_name
                ).first()
                if existing_assignment:
                    if existing_assignment.player_id == int(player_id):
                        return JsonResponse(
                            {
                                "status": "success",
                                "assignment_id": existing_assignment.id,
                                "message": "Typ war bereits zugewiesen.",
                            }
                        )
                    else:
                        old_player_id = existing_assignment.player_id
                        existing_assignment.delete()

                        max_order_dict = PlayerType.objects.filter(
                            player=player
                        ).aggregate(Max("order"))
                        new_order = (
                            (max_order_dict["order__max"] + 1)
                            if max_order_dict["order__max"] is not None
                            else 0
                        )

                        assignment = PlayerType.objects.create(
                            player=player, type_name=type_name, order=new_order
                        )
                        return JsonResponse(
                            {
                                "status": "success",
                                "assignment_id": assignment.id,
                                "message": "Typ zugewiesen.",
                                "removed_from_player_id": old_player_id,
                            }
                        )
                else:
                    max_order_dict = PlayerType.objects.filter(player=player).aggregate(
                        Max("order")
                    )
                    new_order = (
                        (max_order_dict["order__max"] + 1)
                        if max_order_dict["order__max"] is not None
                        else 0
                    )

                    assignment = PlayerType.objects.create(
                        player=player, type_name=type_name, order=new_order
                    )
                    return JsonResponse(
                        {
                            "status": "success",
                            "assignment_id": assignment.id,
                            "message": "Typ zugewiesen.",
                        }
                    )

            except Exception as e:
                return JsonResponse({"status": "error", "message": str(e)}, status=500)

        elif action == "remove_type":
            if not assignment_id:
                return JsonResponse(
                    {"status": "error", "message": "Zuweisungs-ID ist erforderlich."},
                    status=400,
                )
            try:
                assignment = get_object_or_404(PlayerType, pk=assignment_id)
                assignment.delete()
                return JsonResponse({"status": "success", "message": "Typ entfernt."})
            except Exception as e:
                return JsonResponse({"status": "error", "message": str(e)}, status=500)

        elif action == "reset_all_types":
            try:
                deleted_count, _ = PlayerType.objects.all().delete()
                return JsonResponse(
                    {
                        "status": "success",
                        "message": f"{deleted_count} Typenzuweisungen wurden entfernt.",
                    }
                )
            except Exception as e:
                return JsonResponse({"status": "error", "message": str(e)}, status=500)

        else:
            return JsonResponse(
                {"status": "error", "message": "Unbekannte Aktion."}, status=400
            )

    players = Player.objects.all()
    player_types = PlayerType.objects.select_related("player").order_by(
        "player__name", "order"
    )
    german_type_map = get_german_type_names()

    all_type_colors_de = {}
    if german_type_map:
        for en_name, de_name in german_type_map.items():
            color = TYPE_COLORS_EN.get(en_name, "#68A090")
            all_type_colors_de[de_name] = color

    assigned_types = set(PlayerType.objects.values_list("type_name", flat=True))
    available_type_colors_de = {
        type_name: color
        for type_name, color in all_type_colors_de.items()
        if type_name not in assigned_types
    }

    sorted_available_type_colors_de = dict(sorted(available_type_colors_de.items()))

    context = {
        "players": players,
        "player_types": player_types,
        "type_colors_de": sorted_available_type_colors_de,
        "all_type_colors_de": all_type_colors_de,
        "active_tab": "typen",
    }
    return render(request, "tracker/player_types.html", context)


def rules_view(request):
    context = {
        "active_tab": "regeln",
    }
    return render(request, "tracker/rules.html", context)


def pokemon_autocomplete(request):
    term = request.GET.get("term", "").strip()
    if len(term) < 2:
        return JsonResponse([], safe=False)

    pokemons = PokemonSpecies.objects.filter(name__icontains=term).values_list(
        "name", flat=True
    )[:10]

    return JsonResponse(list(pokemons), safe=False)


def type_wheel_view(request):
    players = Player.objects.all()
    german_type_map = get_german_type_names()

    all_type_colors_de = {}
    if german_type_map:
        for en_name, de_name in german_type_map.items():
            color = TYPE_COLORS_EN.get(en_name, "#68A090")
            all_type_colors_de[de_name] = color

    assigned_types = set(PlayerType.objects.values_list("type_name", flat=True))
    available_types = [
        type_name
        for type_name in all_type_colors_de.keys()
        if type_name not in assigned_types
    ]
    available_type_colors = {
        type_name: all_type_colors_de[type_name] for type_name in available_types
    }

    available_types.sort()

    for player in players:
        player.type_count = PlayerType.objects.filter(player=player).count()

    player_types = PlayerType.objects.select_related("player").order_by(
        "player__name", "order"
    )

    import json

    context = {
        "players": players,
        "player_types": player_types,
        "available_types": json.dumps(available_types),
        "type_colors": json.dumps(available_type_colors),
        "all_type_colors_de": all_type_colors_de,
        "active_tab": "rad",
    }
    return render(request, "tracker/type_wheel.html", context)
    return render(request, "tracker/type_wheel.html", context)
