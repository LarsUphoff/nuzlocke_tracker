from django.db import models


class Player(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class Route(models.Model):
    name = models.CharField(max_length=100, unique=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


class PokemonSpecies(models.Model):
    name = models.CharField(max_length=100, unique=True)
    pokedex_id = models.IntegerField(unique=True)
    type1 = models.CharField(max_length=50)
    type2 = models.CharField(max_length=50, blank=True, null=True)
    sprite_url = models.URLField(blank=True, null=True)

    def __str__(self):
        return self.name.capitalize()


class Encounter(models.Model):
    STATUS_CHOICES = [
        ("-", "-"),
        ("gefangen", "Gefangen"),
        ("tot", "Tot"),
        ("verkackt", "Verkackt"),
    ]

    player = models.ForeignKey(
        Player, on_delete=models.CASCADE, related_name="encounters"
    )
    route = models.ForeignKey(
        Route, on_delete=models.CASCADE, related_name="encounters"
    )
    pokemon_species = models.ForeignKey(
        PokemonSpecies, on_delete=models.SET_NULL, null=True, blank=True
    )
    nickname = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="-")

    class Meta:
        unique_together = ("player", "route")
        ordering = ["route__order", "route__name", "player__name"]

    def __str__(self):
        poke_name = (
            self.pokemon_species.name.capitalize()
            if self.pokemon_species
            else "Kein Pokémon"
        )
        return f"{self.player.name} @ {self.route.name}: {self.nickname or poke_name} ({self.get_status_display()})"


class PlayerType(models.Model):
    player = models.ForeignKey(
        Player, on_delete=models.CASCADE, related_name="assigned_types"
    )
    type_name = models.CharField(max_length=50)
    order = models.IntegerField(default=0)

    class Meta:
        unique_together = ("player", "type_name")
        ordering = ["player", "order", "type_name"]

    def __str__(self):
        return f"{self.player.name} - {self.type_name} (Order: {self.order})"
