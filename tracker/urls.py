from django.urls import path
from . import views

urlpatterns = [
    path("", views.tracker_view, name="tracker_view"),
    path("bosse/", views.boss_view, name="boss_view"),
    path(
        "schwaechen/",
        views.strength_weakness_view,
        name="strength_weakness_view",
    ),
    path("status/", views.status_summary_view, name="status_summary_view"),
    path("regeln/", views.rules_view, name="rules_view"),
    path("typen/", views.player_types_view, name="player_types_view"),
    path("type-wheel/", views.type_wheel_view, name="type_wheel_view"),
    path(
        "api/pokemon-autocomplete/",
        views.pokemon_autocomplete,
        name="pokemon_autocomplete",
    ),
]
