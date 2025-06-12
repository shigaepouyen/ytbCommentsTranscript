# Rapport Commentaires & Transcriptions YouTube

Ce projet est un **script Python** permettant de télécharger les commentaires d’une vidéo YouTube et sa transcription (priorité à la piste **FR**, fallback **EN**), puis de les organiser proprement dans des fichiers CSV/TXT.

## Table des Matières
1. [Présentation du Projet](#présentation-du-projet)
2. [Fonctionnalités](#fonctionnalités)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [Utilisation](#utilisation)
6. [Structure des Fichiers Générés](#structure-des-fichiers-générés)
7. [Nettoyage et Post‑Traitement](#nettoyage-et-post-traitement)
8. [Dépannage](#dépannage)
9. [Contribution](#contribution)
10. [Licence](#licence)

## Présentation du Projet
`ytbComentsTranscript.py` automatise :
- la **récupération** des commentaires YouTube,  
- la **détection** des réponses officielles de l’auteur·ice de la chaîne,  
- le **téléchargement** et le **nettoyage** de la transcription (sans timecodes ni balises `<c>`),  
- la **structuration** des exports dans un dossier dédié à chaque vidéo.

## Fonctionnalités
- Télécharge tous les commentaires avec :
  - nombre de likes,
  - date de publication,
  - colonne `is_owner` pour distinguer l’auteur·ice.
- Prend la transcription **française** si disponible, sinon **anglaise**.
- Fallback `yt‑dlp` : récupère le .vtt auto si l’API échoue.
- Nettoie les timecodes `<00:00:00.000>` et balises `<c>`.
- Génère deux formats :  
  - `.csv` détaillé (start, duration, text)  
  - `.txt` concaténé (texte brut)
- Crée la hiérarchie :

```
fichier/
└─ <titre_video_sécurisé>/
   ├─ comments_<id>_<titre>.csv
   ├─ transcript_<id>_<titre>_fr.csv
   └─ transcript_<id>_<titre>_fr.txt
```

*(le suffixe `_en` est utilisé uniquement si la piste FR est absente)*

## Installation
1. **Cloner le dépôt**  
   ```bash
   git clone https://github.com/your‑org/ytbComentsTranscript.git
   cd ytbComentsTranscript
   ```
2. **Créer un environnement virtuel** (recommandé)  
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. **Installer les dépendances**  
   ```bash
   pip install --upgrade requests rich youtube_transcript_api yt-dlp
   ```

## Configuration
Avant la première exécution, renseignez votre clé API YouTube Data v3 dans **`config.ini`** :

```ini
[youtube]
api_key = VOTRE_CLÉ_API
```

> À défaut, la variable d’environnement `YOUTUBE_API_KEY` sera utilisée.

## Utilisation
```bash
python ytbComentsTranscript.py
🔗 URL/ID : https://youtu.be/dQw4w9WgXcQ
```
Le script se charge du reste :

1. Création du dossier `fichier/<titre_ vidéo>/`
2. Export CSV des commentaires
3. Export transcription FR (ou EN)

## Structure des Fichiers Générés
| Fichier | Contenu |
|---------|---------|
| `comments_<id>_<titre>.csv` | type, author, text, likes, published_at, parent_id, is_owner |
| `transcript_<id>_<titre>_<lang>.csv` | start_sec, duration, text |
| `transcript_<id>_<titre>_<lang>.txt` | texte brut concaténé |

## Nettoyage et Post‑Traitement
- Les balises de style (`<c>`), timecodes VTT et lignes vides sont supprimés.  
- Les segments consécutifs sont fusionnés lorsque nécessaire pour éviter les doublons.  
- Les caractères spéciaux du titre sont remplacés afin de créer des chemins sûrs.

## Dépannage
| Problème | Solution |
|----------|----------|
| `NoTranscriptFound`, fichier .vtt vide | Vérifiez que la vidéo possède des sous‑titres auto/manuels. |
| `yt-dlp KO` | Mettez à jour yt‑dlp (`pip install -U yt-dlp`). |
| `API 403` | Activez YouTube Data API v3 sur votre projet Google Cloud et vérifiez vos quotas. |
| `KeyError config.ini` | Assurez‑vous que `[youtube] api_key = …` est bien présent. |

## Contribution
Les PR sont les bienvenues ! Merci de décrire clairement vos changements.

## Licence
Ce projet est sous licence **MIT**. Consultez le fichier LICENSE pour plus de détails.