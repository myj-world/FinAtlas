import os
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Set

from app.config import SANCTIONS_FILES
from app.utils import normalize_name


class SanctionsRepository:
    """Loads local UNSC, EU and OFAC XML files and performs exact/normalised name matching."""

    def __init__(self):
        self._lists: Dict[str, Set[str]] = {key: set() for key in SANCTIONS_FILES}
        self._loaded = False

    def load(self) -> None:
        if self._loaded:
            return
        for list_name, filename in SANCTIONS_FILES.items():
            if os.path.exists(filename):
                self._lists[list_name] = _extract_names(filename)
        self._loaded = True

    def match(self, name: Optional[str]) -> List[Dict[str, str]]:
        self.load()
        target = normalize_name(name)
        if not target:
            return []
        hits = []
        for list_name, names in self._lists.items():
            if target in names:
                hits.append({"list": list_name, "matched_name": name})
        return hits

    def stats(self) -> Dict[str, int]:
        self.load()
        return {name: len(entries) for name, entries in self._lists.items()}


def _extract_names(filename: str) -> Set[str]:
    names: Set[str] = set()
    try:
        tree = ET.parse(filename)
    except ET.ParseError:
        return names

    root = tree.getroot()
    # Common tags used by real and stub lists.
    for tag in ("name", "firstName", "lastName", "entityName", "alias", "aliases"):
        for elem in root.iter(tag):
            text = elem.text
            if text:
                normalized = normalize_name(text)
                if normalized:
                    names.add(normalized)
    return names


sanctions_repo = SanctionsRepository()
