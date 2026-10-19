"""Deterministic sanctions matching against local UNSC, EU and OFAC XML lists."""

import os
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from app.config import SANCTIONS_FILES
from app.utils import normalize_name


@dataclass
class SanctionsEntity:
    entity_id: str
    list_name: str
    names: Set[str] = field(default_factory=set)


class SanctionsRepository:
    """Loads local UNSC, EU and OFAC XML files and performs exact/normalised name matching."""

    def __init__(self):
        self._entities: Dict[str, List[SanctionsEntity]] = {key: [] for key in SANCTIONS_FILES}
        self._loaded = False

    def load(self) -> None:
        if self._loaded:
            return
        for list_name, filename in SANCTIONS_FILES.items():
            if os.path.exists(filename):
                self._entities[list_name] = _extract_entities(list_name, filename)
        self._loaded = True

    def match(self, name: Optional[str]) -> List[Dict[str, str]]:
        """Return every exact/normalised sanctions hit for the supplied name."""
        self.load()
        target = normalize_name(name)
        if not target:
            return []

        hits = []
        for list_name, entities in self._entities.items():
            for entity in entities:
                if target in entity.names:
                    hits.append(
                        {
                            "list": list_name,
                            "entity_id": entity.entity_id,
                            "matched_name": name,
                        }
                    )
        return hits

    def stats(self) -> Dict[str, int]:
        self.load()
        return {name: len(entities) for name, entities in self._entities.items()}


def _extract_entities(list_name: str, filename: str) -> List[SanctionsEntity]:
    entities: List[SanctionsEntity] = []
    if not os.path.exists(filename):
        return entities

    try:
        tree = ET.parse(filename)
    except ET.ParseError:
        return entities

    root = tree.getroot()
    for entity_elem in root.findall("entity"):
        entity_id = entity_elem.get("id") or f"{list_name}-UNKNOWN"
        entity = SanctionsEntity(entity_id=entity_id, list_name=list_name)

        # Collect primary names, aliases and any free-text name fields.
        for tag in ("name", "firstName", "lastName", "entityName"):
            for elem in entity_elem.iter(tag):
                text = elem.text
                if text:
                    normalized = normalize_name(text)
                    if normalized:
                        entity.names.add(normalized)

        aliases_elem = entity_elem.find("aliases")
        if aliases_elem is not None:
            for alias_elem in aliases_elem.iter("alias"):
                text = alias_elem.text
                if text:
                    normalized = normalize_name(text)
                    if normalized:
                        entity.names.add(normalized)

        if entity.names:
            entities.append(entity)

    return entities


sanctions_repo = SanctionsRepository()
