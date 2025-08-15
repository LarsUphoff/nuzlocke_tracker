# Nuzlocke Tracker

Dies ist eine Django-Webanwendung zum Tracking einer HeartGold/SoulSilver Nuzlocke-Challenge mit deutschen Pokémon-Namen und vordefinierten Routen. Ich habe diese App als persönliches Projekt erstellt, um meine Django-Fähigkeiten zu verbessern und mehr über Webentwicklung zu lernen. Außerdem wollte ich die App erstellen, um ein spezielles Tool für das Tracking von Nuzlocke-Runs für mich und meine Freunde bei unseren LAN-Partys bereitzustellen.

Ich plane, in Zukunft weitere Pokémon-Spiele und Funktionen hinzuzufügen.

## Funktionen

- Tracking gefangener Pokémon mit deutschen Namen
- Vordefinierte Routen aus Pokémon HeartGold/SoulSilver
- PostgreSQL-Datenbankunterstützung
- Übersicht aller Bosse, gegen die man im Verlauf des Spiels kämpfen kann/muss
- Übersicht aller Schwächen eines Pokémon nach Eingabe des Namens
    - ACHTUNG: Das initiale Laden der Schwächen kann beim ersten Aufruf einige Zeit in Anspruch nehmen, da die Informationen von der PokéAPI abgerufen werden. Anschließend werden die Daten gecached. Zukünftig sollen diese Informationen in der Datenbank gespeichert werden, um die Ladezeiten zu verkürzen.
- Übersicht der Regeln einer Nuzlocke-Challenge.
- Als Hausregel haben wir uns überlegt, dass jedem Spieler bestimmte Typen zugewiesen werden sollen. Die Spieler dürfen dann nur Pokémon mit dem jeweiligen Typen fangen. Dafür gibt es einen eigenen Tab. Zudem gibt es ein Glücksrad, welches den Spielern zufällig Pokémon-Typen zuweist.

## Voraussetzungen

- Python 3.8+
- PostgreSQL 12+
- pip (Python-Paketmanager)

## Installation & Einrichtung

### 1. Repository klonen

```bash
git clone <your-repository-url>
cd nuzlocke_tracker
```

### 2. Virtuelle Umgebung erstellen

```bash
python -m venv venv
source venv/bin/activate  # Unter Windows: venv\Scripts\activate
```

### 3. Dependencies installieren

```bash
pip install -r requirements.txt
```

### 4. PostgreSQL-Datenbank einrichten

PostgreSQL installieren und die Datenbank erstellen:

```sql
-- Zu PostgreSQL verbinden
CREATE DATABASE nuzlocke_tracker;
CREATE USER nuzlocke_user WITH PASSWORD 'your_secure_password';

-- Berechtigungen erteilen
GRANT CREATE ON SCHEMA public TO nuzlocke_user;
GRANT USAGE ON SCHEMA public TO nuzlocke_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO nuzlocke_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO nuzlocke_user;
```

### 5. Umgebungskonfiguration

Eine `.env`-Datei im Projektverzeichnis erstellen:

```env
# PostgreSQL-Datenbank-Konfiguration
DB_NAME=nuzlocke_tracker
DB_USER=nuzlocke_user
DB_PASSWORD=your_secure_password
DB_HOST=localhost
DB_PORT=5432

# Django-Einstellungen
SECRET_KEY=your-secret-key-here
DEBUG=True
```

**Wichtig:** Einen neuen SECRET_KEY für production generieren:
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 6. Datenbank-Migration

```bash
python manage.py makemigrations
python manage.py migrate
```

### 7. Superuser erstellen

```bash
python manage.py createsuperuser
```

### 8. Ausgangsdaten einfügen

Pokémon-Arten mit deutschen Namen laden:
```bash
python manage.py populate_pokemon
```

Vordefinierte Routen laden:
```bash
python manage.py populate_routes
```

### 9. Entwicklungsserver starten

```bash
python manage.py runserver
```

Die Anwendung ist unter `http://127.0.0.1:8000/` erreichbar.

### 10. Spieler hinzufügen

Um einen neuen Spieler hinzuzufügen, auf `http://127.0.0.1:8000/admin/` gehen und sich mit den Superuser-Anmeldedaten anmelden. Dann zu "Players" navigieren und Spieler hinzufügen.

## Netzwerkzugriff

Um anderen Geräten im Netzwerk den Zugriff auf die Anwendung zu ermöglichen:

**Option 1: Konfiguration über .env-Datei (empfohlen)**
1. Lokale IP-Adresse ermitteln
2. Diese zu `ALLOWED_HOSTS` in der `.env`-Datei hinzufügen (komma-getrennt):
   ```env
   ALLOWED_HOSTS=127.0.0.1,localhost,YOUR_IP
   ```
3. Diese Umgebungsvariable in `settings.py` verwenden:
   ```python
   ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='127.0.0.1,localhost').split(',')
   ```
4. Den Server mit folgender Anweisung starten:
   ```bash
   python manage.py runserver 0.0.0.0:8000
   ```

**Option 2: Direkte Konfiguration in settings.py**
1. Lokale IP-Adresse ermitteln
2. Diese zu `ALLOWED_HOSTS` in `settings.py` hinzufügen
3. Den Server mit folgender Anweisung starten:
   ```bash
   python manage.py runserver 0.0.0.0:8000
   ```

Von anderen Geräten zugreifen über: `http://YOUR_IP:8000`

## Projektstruktur

```
nuzlocke_tracker/
├── nuzlocke_tracker/           # Hauptprojektverzeichnis
│   ├── settings.py             # Django-Einstellungen
│   ├── urls.py                 # URL-Konfiguration
│   └── wsgi.py                 # WSGI-Konfiguration
├── tracker/                    # Hauptanwendung
│   ├── management/
│   │   └── commands/           # Benutzerdefinierte Management-Befehle
│   │       ├── populate_pokemon.py
│   │       └── populate_routes.py
│   ├── models.py               # Datenbankmodelle
│   └── ...
├── .env                        # Umgebungsvariablen
├── manage.py                   # Django-Management-Skript
└── requirements.txt            # Python-Dependencies
```

## Management-Befehle

- `python manage.py populate_pokemon` - Holt Pokémon-Daten von der PokéAPI mit deutschen Namen
- `python manage.py populate_routes` - Erstellt vordefinierte Routen für HeartGold/SoulSilver

## Admin-Interface

Zugriff auf das Admin-Interface unter `http://127.0.0.1:8000/admin/` mit Superuser-Anmeldedaten zur Verwaltung von:
- Pokémon-Arten
- Routen
- Benutzerkonten

## API-Datenquelle

Diese Anwendung verwendet die [PokéAPI](https://pokeapi.co/), um Pokémon-Daten einschließlich deutscher Namen und Sprites abzurufen.
