"""
Movie catalog loader for the MovieLens 100k dataset.

Reads u.item (pipe-delimited, latin-1) and exposes a fast dict lookup:
    item_id  →  { title, year, genres, imdb_url }

where item_id is the string used throughout the system, e.g. "item_30".

Genre columns in u.item (positions 5–23):
    unknown | Action | Adventure | Animation | Children's | Comedy |
    Crime   | Documentary | Drama | Fantasy | Film-Noir | Horror |
    Musical | Mystery | Romance | Sci-Fi | Thriller | War | Western
"""

import codecs
import os
import re
from pathlib import Path
from typing import Dict, List, Optional

import structlog

logger = structlog.get_logger(__name__)

# Ordered genre names matching the binary columns in u.item (index 5 onwards)
GENRE_NAMES: List[str] = [
    "Unknown", "Action", "Adventure", "Animation", "Children's",
    "Comedy", "Crime", "Documentary", "Drama", "Fantasy",
    "Film-Noir", "Horror", "Musical", "Mystery", "Romance",
    "Sci-Fi", "Thriller", "War", "Western",
]

# Default search paths (inside the Docker container the data is at /app/data)
_SEARCH_PATHS = [
    "/app/data/raw/ml-100k/u.item",
    "data/raw/ml-100k/u.item",
    "../data/raw/ml-100k/u.item",
]

_catalog: Dict[str, Dict] = {}


def _load(path: str) -> Dict[str, Dict]:
    catalog: Dict[str, Dict] = {}
    try:
        with codecs.open(path, encoding="latin-1") as fh:
            for line in fh:
                parts = line.rstrip("\n").split("|")
                if len(parts) < 5:
                    continue
                movie_id = parts[0].strip()
                raw_title = parts[1].strip()
                imdb_url = parts[3].strip() if len(parts) > 3 else ""

                # Extract year from title, e.g. "Toy Story (1995)" → 1995
                year_match = re.search(r"\((\d{4})\)\s*$", raw_title)
                year = int(year_match.group(1)) if year_match else None
                # Clean title: remove the trailing (year)
                title = re.sub(r"\s*\(\d{4}\)\s*$", "", raw_title).strip()

                # Decode genre flags
                genres: List[str] = []
                for i, name in enumerate(GENRE_NAMES):
                    col = 5 + i
                    if col < len(parts) and parts[col].strip() == "1":
                        genres.append(name)

                item_key = f"item_{movie_id}"
                catalog[item_key] = {
                    "title": title,
                    "full_title": raw_title,
                    "year": year,
                    "genres": genres,
                    "imdb_url": imdb_url,
                }
    except Exception as e:
        logger.warning("catalog_load_error", path=path, error=str(e))
    return catalog


def init_movie_catalog() -> int:
    """Load the catalog from the first available u.item path. Returns item count."""
    global _catalog
    for path in _SEARCH_PATHS:
        if os.path.exists(path):
            _catalog = _load(path)
            logger.info("movie_catalog_loaded", path=path, items=len(_catalog))
            return len(_catalog)
    logger.warning("movie_catalog_not_found", searched=_SEARCH_PATHS)
    return 0


def get_item_metadata(item_id: str) -> Dict:
    """
    Return metadata dict for an item_id.
    Falls back to minimal dict if the catalog has no entry.
    """
    entry = _catalog.get(item_id)
    if entry:
        return {
            "title": entry["title"],
            "full_title": entry["full_title"],
            "year": entry["year"],
            "genres": entry["genres"],
            "imdb_url": entry["imdb_url"],
            "available": True,
        }
    return {"title": item_id, "genres": [], "available": True}


def get_title(item_id: str) -> str:
    """Quick title lookup, returns item_id if not found."""
    entry = _catalog.get(item_id)
    return entry["title"] if entry else item_id


def catalog_size() -> int:
    return len(_catalog)
