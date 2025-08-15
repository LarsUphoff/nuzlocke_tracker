from django.contrib import admin
from .models import Player, Route, PokemonSpecies, Encounter, PlayerType

admin.site.register(Player)
admin.site.register(Route)
admin.site.register(PokemonSpecies)
admin.site.register(Encounter)
admin.site.register(PlayerType)
