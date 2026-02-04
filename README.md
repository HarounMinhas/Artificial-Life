# Artificial-Life

## V1 Python implementation

Deze repo bevat een eerste Python-implementatie van de V1-mechanics in `artificial_life/`.
De code volgt een tick-gebaseerde simulatie-flow en gebruikt strategieën (Strategy pattern)
voor perceptie, emotie, beslissing en actie, zodat onderdelen gemakkelijk te vervangen
of te testen zijn.

### Run (headless)
```bash
python -m artificial_life.runner
```

# Versie 1 — Core mechanics brainstorm

## 1. Tijd & simulatie-flow (superbelangrijk)

### Mechanic
- Discrete **ticks** (bijv. 30–60 per seconde)
- Alles gebeurt in vaste volgorde

### V1-regel
Elke tick:
1. Waarnemen
2. Emotie update
3. Beslissing
4. Actie
5. Interactie
6. Verval

➡️ **Geen parallelle chaos**, alles is deterministisch per tick.

---

## 2. Beweging (locomotion)

### Wat moet bewegen realistisch maken?
- Geen teleport
- Geen perfecte bochten
- Momentum + beperking

### V1-mechanics
- Positie (x,y)
- Richting (hoek)
- Snelheid
- Maximale draaisnelheid

### Regels
- Wezen draait eerst → beweegt daarna
- Richting verandert max X graden per tick
- Botsing = afketsen + stress

### Extra (cheap maar effectief)
- Kleine willekeurige ruis in richting → “levendig”

---

## 3. Zien (vision)

### Wat zien wezentjes?
Niet “alles”, maar:
- Alleen binnen bereik
- Met onnauwkeurigheid
- Beperkt aantal objecten

### V1-mechanics
- Cirkelvormig zicht (geen kegels in v1)
- Max zichtafstand
- Zicht-ruis (positie ± fout)

### Output
```
object_type
geschatte_positie
geschatte_afstand
```

➡️ Waarneming ≠ realiteit

---

## 4. Horen (gehoor)

### Wat is horen in v1?
Niet richtinggevoelig, alleen:
- Er is iets
- Hoe sterk

### V1-mechanics
- Geluidsbron heeft radius + intensiteit
- Afstand verlaagt intensiteit
- Meerdere geluiden stapelen

### Output
```
geluidstype
sterkte
bron_onbekend
```

➡️ Paniek zonder weten waar het vandaan komt

---

## 5. Ruiken (reuk)

### Cruciaal verschil met zicht
- Geur blijft hangen
- Verspreidt zich langzaam
- Vervaagt

### V1-mechanics
- Geur = puntbron met radius
- Radius groeit langzaam
- Intensiteit daalt per tick

### Wezen ruikt
- Sterkste geur
- Geen exacte richting, alleen “warmer/kouder”

➡️ Ruiken = zoeken, niet targetten

---

## 6. Tast / nabijheid

### V1-mechanics
- Check: is iets binnen kleine straal?
- Botsing = fysiek + emotioneel effect

### Triggers
- Aanraking ander wezen
- Aanraking obstakel
- Aanval

➡️ Tast is *event-based*, niet continu

---

## 7. Perceptie-samenvoeging

### Waarom belangrijk?
Zonder dit krijg je rare reacties.

### V1-mechanic
Per tick:
- Max **N percepties**
- Gesorteerd op:
  1. Bedreiging
  2. Nabijheid
  3. Intensiteit

➡️ Aandacht is beperkt

---

## 8. Stress (centrale driver)

### Stress = functie van:
- Angst
- Pijn
- Prikkels
- Energie

### V1-mechanics
```
stress = angst + pijn + prikkel_overload - energie
```

### Stress
- Stuurt fight/flight/freeze
- Verlaagt waarneming
- Verhoogt fouten

---

## 9. Fight / Flight / Freeze (mechanics)

### V1-beslissing
Als `stress > drempel`:
- Kies respons o.b.v. bias

### Fight
- Beweeg naar bedreiging
- Agressie ↑
- Pijn-drempel ↑

### Flight
- Draai weg
- Snelheid ↑
- Perceptie vernauwt

### Freeze
- Snelheid = 0
- Zicht ↓
- Detecteerbaarheid ↓

---

## 10. Beslissingsmechanic (simpel maar krachtig)

### Geen AI-boom, maar:
**Score-based intenties**

### V1-mechanics
Elke mogelijke intentie krijgt score:
- Eten
- Aanvallen
- Vluchten
- Patrouilleren
- Rusten

Score = emotie × behoefte × context

➡️ Hoogste score wint

---

## 11. Territorium-mechanics (v1)

### Representatie
- Cirkel (centrum + radius)
- Sterkte (0–1)

### Regels
- Wezen in eigen territorium → stress ↓
- Indringer → stress ↑ + agressie ↑
- Markeren = sterkte ↑

➡️ Geen ingewikkelde kaarten in v1

---

## 12. Sociale interactie (v1)

### Relaties
Per ander wezen:
- Vertrouwen
- Angst

### V1-regels
- Schade → vertrouwen ↓, angst ↑
- Hulp → vertrouwen ↑
- Nabijheid zonder conflict → lichte vertrouwensgroei

---

## 13. Communicatie (super simpel v1)

### Alleen broadcasts:
- Gevaar
- Voedsel

### Mechanics
- Signaal = geluid + emotie
- Ontvanger interpreteert verkeerd met kans

➡️ Miscommunicatie standaard

---

## 14. Schade & pijn

### V1-mechanics
```
schade = agressie × snelheid
pijn += schade
```

### Effect
- Pijn ↑ stress
- Pijn ↓ nauwkeurigheid
- Pijn vervaagt langzaam

---

## 15. Leren (minimaal v1)

### Associaties
- Plek → emotie
- Wezen → emotie

### Regel
- Sterke emotie = sterke associatie
- Verval over tijd

---

## 16. Dood (ja, ook in v1)

### Dood veroorzaakt:
- Geur
- Angst-signaal
- Territorium-instabiliteit

➡️ Dood is een **event**, geen eindpunt

---

## 17. Fouten & ruis (heilig)

### Overal ruis:
- Zichtfout
- Besluitfout
- Reactietijd

➡️ Zonder ruis = dode simulatie

---

## Samenvatting: wat V1 absoluut heeft

Zonder dit werkt het niet:
- Beweging met beperking
- Onbetrouwbare perceptie
- Stress als kern
- Fight/flight/freeze
- Territorium
- Pijn + angst
- Ruis

Met alleen dit krijg je al:
- Jagen
- Vluchten
- Territoriumgedrag
- Conflicten
- Emergente chaos

---

# V1 — Visueel & interactie ontwerp (Python)

## Doel van de visualisatie (V1)
- Gedrag **observeren**, niet verfraaien
- Begrijpen *waarom* een wezen iets doet
- Debuggen van perceptie, stress en territorium

➡️ Functionaliteit > esthetiek

---

## 1. Het veld (de wereld)

### Afmetingen
- **Veldgrootte:** 800 × 600 pixels (startpunt)
- **Reden:**
  - Klein genoeg om interacties af te dwingen
  - Groot genoeg voor territoriumvorming

### Achtergrond
- Effen donkere kleur (bijv. donkergrijs / blauwzwart)
- Geen textuur in V1

---

## 2. Wezentjes (agents)

### Vorm
- **Cirkel**
- Radius: **6–8 pixels**

### Kleur (informatief)
Kleur geeft **interne staat** weer:
- Basis: blauwachtig
- Meer **stress / angst** → roder
- Lage energie → donkerder
- Eventueel: agressie → lichte oranje tint

➡️ Je *ziet* emoties zonder UI

### Richting
- Klein **lijnstuk of punt** vanuit het centrum
- Toont bewegingsrichting

---

## 3. Territorium (debug zichtbaar)

### Weergave
- **Cirkel rondom het wezen**
- Dunne lijn
- Lage alpha (transparant)

### Kleur
- Groen = eigen territorium
- Rood = indringer (optioneel debug)

### Regels
- Alleen zichtbaar in **debug-modus**
- Aan/uit via toets (bijv. `D`)

---

## 4. Zien / horen / ruiken (debug overlays)

### Zicht
- Cirkel met radius = zichtbereik
- Alleen zichtbaar in debug-modus

### Gehoor
- Geen cirkel nodig
- Eventueel: korte flits bij ontvangen geluid

### Reuk
- Geurbronnen zichtbaar als:
  - Vage cirkels
  - Intensiteit = alpha
- Verdwijnen langzaam

➡️ Dit maakt “zoeken” zichtbaar

---

## 5. Voedsel

### Vorm
- Kleine cirkel of vierkant
- Radius: **4–5 pixels**

### Kleur
- Groen
- Iets feller dan achtergrond

### Gedrag
- Wordt geconsumeerd bij nabijheid
- Verwijnt direct

---

## 6. Voedsel-spawning (interactie)

### V1: beide methodes (simpel)

#### 1️⃣ Random spawning
- Elke X seconden:
  - Als voedsel < minimum → spawn nieuw
- Spawn op random positie
- Niet te dicht bij rand

#### 2️⃣ Muis-interactie
- **Linkermuisklik** → plaats voedsel
- Direct zichtbaar
- Goed voor testen van gedrag

➡️ Handig om stress-reacties te observeren

---

## 7. Aantal entiteiten (V1 defaults)

### Wezentjes
- Start: **8–15**
- Verschillende fight/flight/freeze biases
- Willekeurige startposities

### Voedsel
- Start: **15–25**
- Minimum aanwezig: **5–8**

---

## 8. Camera & navigatie

### V1: vaste camera
- Geen zoom
- Geen panning

### Reden
- Simpel
- Observeer globale dynamiek

---

## 9. UI / HUD (minimaal)

### Linksboven tekst:
- Tick / tijd
- Aantal wezens
- Aantal voedsel
- Debug aan/uit

### Optioneel:
- Toon stress van geselecteerd wezen

---

## 10. Selectie & inspectie (optioneel maar sterk)

### Muis
- Klik op wezen → selecteer

### Toon (overlay of tekst):
- Energie
- Stress
- Angst
- Agressie
- Huidige intentie

➡️ Niet nodig voor gedrag, **wel cruciaal voor tuning**

---

## 11. Input-overzicht (V1)

| Input          | Actie                  |
| -------------- | ---------------------- |
| Linkermuisklik | Plaats voedsel         |
| D              | Debug overlays aan/uit |
| R              | Reset wereld           |
| Spatie         | Pauze                  |
| S (optioneel)  | Stap 1 tick vooruit    |

---

## 12. Wat expliciet niet in V1 visualisatie
- Animaties
- Sprites
- Geluiden
- Fancy UI
- Camera beweging
- Particles

➡️ Alles wat afleidt van gedrag

---

## 13. Hoe Codex dit moet begrijpen (belangrijk)

Formuleer dit als:
> “De visualisatie is een observatie-instrument voor gedragsmechanics, niet een game-UI.”

---

## Samenvattend beeld (mentaal)
- Donkere rechthoek
- Kleine bewegende cirkels
- Soms botsen ze
- Soms vluchten ze
- Soms vallen ze aan
- Groene puntjes verschijnen
- Rode/gele tinten verraden interne chaos
- Transparante cirkels tonen territorium in debug

➡️ **Als je hier 10 minuten naar kijkt en het blijft interessant, dan zit V1 goed.**
