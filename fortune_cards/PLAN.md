# Plan — Nouvelles Cartes Fortune + Web App

## Contexte

Extension fan-made du jeu *Mille Sabords* (Haim Shafir). Création de ~20-25 nouvelles cartes Fortune originales, illustrées par IA, affichées dans une web app mobile.

---

## Étape 1 — Génération des cartes (fait en conversation avec Claude)

### Contraintes de design

**Mécaniques :**
- Jouable avec les 8 dés physiques originaux (6 symboles : crâne 💀, épée ⚔️, pièce d'or 🪙, diamant 💎, singe 🐒, perroquet 🦜)
- Règle unique, explicable en 2-3 phrases max
- Équilibrée : ni trop avantageuse, ni trop punitive
- Stratégie optimale distincte des cartes existantes et des autres nouvelles cartes

**Archétypes visés :**
- Contrainte de relance (min/max de dés imposé)
- Inversion de valeur (symbole qui change de sens ce tour)
- Condition bonus/malus en fin de tour (objectif à atteindre)
- Règle one-shot (exception ponctuelle dans le tour)
- Pression sur les adversaires

### Format de chaque carte (fichier MD séparé)

Chaque carte est sauvegardée dans `fortune_cards/cards/<nom_carte>.md` avec le format :

```markdown
# Nom de la carte

## Règle
[2-3 phrases max]

## Stratégie induite
[1 phrase résumant la stratégie optimale]

## Description visuelle (prompt IA)
[Prompt prêt à l'emploi pour OpenAI Images]
```

### Style visuel unifié

**Base commune pour tous les prompts :**
> *Detailed digital fantasy illustration in the style of premium board game card art, painterly and vivid, rich saturated colors (deep navy blues, crimson reds, shimmering golds), dramatic chiaroscuro lighting with a single strong focal point, atmospheric background (stormy sea, night sky, candlelit cabin, or rich velvet fabric), 17th century pirate adventure theme, high detail, clean and polished finish, no text, no letters, no numbers, portrait orientation 2:3*

**Format image :** 1024×1536 px (portrait, ratio 2:3 — correspond aux cartes physiques)

---

## Étape 2 — Génération des illustrations (OpenAI Images API)

- Un appel API par carte, en utilisant la description visuelle du fichier MD
- Format cible : **paysage 3:2** (~1290×860 px), correspondant aux cartes réelles (8.6cm × 5.6cm)
- Modèle : `gpt-image-1` ou `dall-e-3`
- Script Python à créer : `fortune_cards/generate_images.py`
  - Lit chaque fichier `cards/*.md`
  - Extrait le prompt de la section "Description visuelle"
  - Appelle l'API avec `size="1792x1024"` (ratio ~3:2 disponible chez OpenAI)
  - Sauvegarde les images dans `fortune_cards/images/<nom_carte>.png`

---

## Étape 3 — Web App statique (HTML/CSS/JS, zéro dépendance)

### Fonctionnalités

**Core :**
- Affichage d'une carte tirée aléatoirement
- Face recto : illustration de la carte (plein écran, format paysage)
- Clic/tap → flip animé → verso : nom de la carte + règle
- Bouton "Nouvelle carte" : pioche aléatoire dans le deck

**Favoris & notes :**
- Bouton ⭐ sur le verso pour marquer une carte en favori
- Possibilité d'ajouter une note courte par carte (textarea)
- Persistance via `localStorage` (pas de serveur nécessaire)
- Vue "Mes favoris" : liste filtrée des cartes marquées

**UI :**
- Optimisée mobile (touch-friendly, plein écran)
- Orientation paysage recommandée (correspond au format des cartes)
- Animations de flip CSS (transform 3D)
- Hébergeable statiquement (GitHub Pages, Netlify, etc.)

### Structure des fichiers

```
fortune_cards/
├── PLAN.md                  ← ce fichier
├── cards/                   ← fichiers MD des cartes
│   ├── la_traversee.md
│   ├── le_grand_vent.md
│   └── ...
├── images/                  ← illustrations générées par IA
│   ├── la_traversee.png
│   └── ...
├── generate_images.py       ← script OpenAI API
└── web/
    ├── index.html
    ├── style.css
    ├── app.js
    └── cards.json           ← données des cartes (généré depuis les MD)
```

---

## Notes de design sur quelques cartes

**La Traversée** : pour cette carte uniquement, les crânes sont **relanables** (exception à la règle normale). Cela permet de gérer librement les 6 dés pour obtenir les 6 symboles différents. Les crânes causent toujours l'élimination si 3 apparaissent *simultanément* en fin de relance.

**Le Grand Vent** : minimum 4 dés par relance (au lieu de 2), les diamants valent 200 pts chacun individuellement.

---

## Statut

- [x] Règles du jeu lues et intégrées
- [x] Plan finalisé
- [x] Cartes générées (22 cartes dans `cards/`)
- [ ] Script `generate_images.py` créé
- [ ] Images générées
- [ ] Web app créée
