# Great Firewall Scanner

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.18172145.svg)](https://doi.org/10.5281/zenodo.18172145) 

## Streszczenie

Projekt bada pojęcie [Wielkiej Zapory Sieciowej](https://pl.wikipedia.org/wiki/Wielka_Zapora_Sieciowa) 
(ang. [The Great Firewall](https://en.wikipedia.org/wiki/Great_Firewall))
, która polega na blokowaniu dostępu do wybranych zagranicznych witryn internetowych i spowalnianiu transgranicznego ruchu internetowego.  
Aplikacja ta to asynchroniczny skaner adresów URL przeznaczony do testowania dostępności i analizy zasięgu chińskich stron rządowych w sieci. Narzędzie wczytuje dane z pliku CSV, równolegle testuje połączenia HTTP, rejestruje czasy odpowiedzi, śledzi kody statusu i diagnozuje problemy sieciowe.

## Inspiracja projektu

Projekt i zastosowana w nim metodyka pomiarowa opierają się na publikacji naukowej z czasopisma Journal of Cybersecurity.

- **Tytuł:** *"Conceptualizing the reverse great firewall: cybersecurity and the logics of government geo-blocking in China"*
- **Autor:** Vincent Brussee
- **Czasopismo:** Journal of Cybersecurity, Volume 12, Issue 1
- **Rok publikacji:** 2026
- **Link do publikacji (DOI):** [https://doi.org/10.1093/cybsec/tyag005](https://doi.org/10.1093/cybsec/tyag005)

Plik z bazą danych stron chińskich została zapewniona przez autora na otwartej licencji  
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.18172145.svg)](https://doi.org/10.5281/zenodo.18172145)

### Cytowanie

Vincent Brussee, Conceptualizing the reverse great firewall: cybersecurity and the logics of government geo-blocking in China, Journal of Cybersecurity, Volume 12, Issue 1, 2026, tyag005, https://doi.org/10.1093/cybsec/tyag005

## Ograniczenia względem artykułu naukowego

Artykuł Vincent'a Brussee wykorzystywał 14 różnych serwerów proxy każdy dla osobnych krajów (w tym Chiny, Hong Kong i Tajwan). 
Ze względu na dodatkowe koszty związane z utworzeniem i konfigurowaniem serwerów proxy ten projekt skupi się na testowaniu stron tylko z lokalizacji użytkownika.

## Główne funkcjonalności

- **Asynchroniczne skanowanie:** Wykorzystuje `asyncio` i `aiohttp` z użyciem semaforów do równoległego i szybkiego skanowania setek adresów bez przeciążania sieci.
- **Diagnostyka sieciowa i DNS:** Automatycznie przeprowadza dogłębną diagnozę (DNS traceroute, network traceroute) w przypadku braku połączenia do testowanego zasobu.
- **Odporność na blokady:** Rotacja nagłówków `User-Agent`, ignorowanie weryfikacji SSL i obsługiwanie limitów czasu w celu ominięcia prostych mechanizmów przeciwko botom.
- **Raportowanie i logowanie:** Śledzenie łańcuchów przekierowań (HTTP trace). Zapisuje wyniki i obszerne podsumowania sesji do folderu `results/` pod postacią plików CSV i tekstowych logów (osobnych dla każdej sesji/dnia).
- **Elastyczna konfiguracja:** Główne ustawienia projektu, takie jak limit jednoczesnych połączeń, czas oczekiwania, zakres uderzeń czy uruchamianie tras (trace), można zmieniać w `config.py`.

## Struktura projektu

- `main.py` - Główny plik uruchomieniowy aplikacji.
- `config.py` - Plik z konfiguracją skanera (limity, ścieżki, timeouty).
- `requirements.txt` - Lista wymaganych zależności i pakietów.
- `analysis.py` / `report.py` - Skrypty służące do analizy wyników skanowań.
- `scanner/` - Moduły odpowiedzialne za nawiązywanie połączenia HTTP (`http.py`), diagnostykę błędów sieci (`diagnostics.py`) oraz kod rdzenny skanera (`core.py`).
- `utils/` - Funkcje pomocnicze, m.in. obróbka dat (`time_utils.py`) i wyświetlanie tabel (`table_printer.py`).
- `results/` - Tu zapisywane są wyniki w formacie CSV oraz historia konsoli (logi).
- `Chinese government websites.csv` - Plik ze zbiorem danych (URL) używanych przy testach. Udostępniona na otwartej licencji przez autora artykułu naukowego. W przypadku zmiany tej nazwy należy ją zaktualizować w pliku `config.py`.

## Wymagania i instalacja

Projekt wymaga języka **Python** w wersji **3.11+**.
Dodatkowe zależności są zawarte w pliku `requirements.txt`, który może posłużyć do utworzenia środowiska wirtualnego.

### Tworzenie i uruchamianie środowiska wirtualnego

1. Sklonuj repozytorium (pobierz pliki projektu).
2. Stwórz wirtualne środowisko:
   ```bash
   python -m venv .venv
   ```
3. Uruchom wirtualne środowisko:
   ```bash
   # na systemie Linux/macOS
   source .venv/bin/activate
   # na systemie Windows, w wierszu poleceń 
   .venv\Scripts\activate.bat
   # na systemie Windows, w PowerShell
   venv\Scripts\Activate.ps1
   ```
4. Zainstaluj pakiety z `requirements.txt`:
   ```bash
   pip install -r requirements.txt
   ```
5. Projekt jest gotowy do uruchomienia i utworzy folder `results` w środku projektu:
   ```bash
   python main.py
   ```
6. Środowisko można wyłączyć poleceniem:
   ```bash
   deactivate
   ```


## Uruchamianie

Przed uruchomieniem można dostosować ustawienia logiki skanowania w pliku `config.py` (np. ilość testowanych url, ilość czasu poświęcona na zapytanie).

Skrypt uruchamia się poprzez plik `main.py`:

```bash
python main.py
```

Wszystkie zebrane logi oraz podsumowanie dostępności (pliki tekstowe z terminala, pliki CSV po skanowaniu) można znaleźć w katalogu `results/`.
