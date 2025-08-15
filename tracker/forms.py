from django import forms
from .models import Encounter, Player, Route, PokemonSpecies


class EncounterForm(forms.ModelForm):
    player = forms.ModelChoiceField(
        queryset=Player.objects.all(), widget=forms.HiddenInput()
    )
    route = forms.ModelChoiceField(
        queryset=Route.objects.all(), widget=forms.HiddenInput()
    )
    pokemon_name = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={"class": "pokemon-autocomplete"}),
    )
    pokemon_species = forms.ModelChoiceField(
        queryset=PokemonSpecies.objects.all(),
        required=False,
        widget=forms.HiddenInput(),
    )

    class Meta:
        model = Encounter
        fields = [
            "player",
            "route",
            "pokemon_species",
            "nickname",
            "status",
            "pokemon_name",
        ]
        widgets = {
            "nickname": forms.TextInput(attrs={"placeholder": "Spitzname"}),
            "status": forms.Select(),
        }

    def clean(self):
        cleaned_data = super().clean()
        pokemon_name = cleaned_data.get("pokemon_name")
        status = cleaned_data.get("status")

        if pokemon_name:
            try:
                species = PokemonSpecies.objects.get(name__iexact=pokemon_name)
                cleaned_data["pokemon_species"] = species
            except PokemonSpecies.DoesNotExist:
                if status not in ["-", "verkackt"]:
                    self.add_error(
                        "pokemon_name",
                        f"Pokémon '{pokemon_name}' nicht in der Datenbank gefunden.",
                    )
                else:
                    cleaned_data["pokemon_species"] = None
        else:
            cleaned_data["pokemon_species"] = None

        return cleaned_data
