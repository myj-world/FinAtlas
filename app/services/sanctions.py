# """Deterministic sanctions matching against local UNSC, EU and OFAC XML lists."""

# import os
# import xml.etree.ElementTree as ET
# from dataclasses import dataclass, field
# from typing import Dict, List, Optional, Set

# from app.config import SANCTIONS_FILES
# from app.utils import normalize_name


# @dataclass
# class SanctionsEntity:
#     entity_id: str
#     list_name: str
#     names: Set[str] = field(default_factory=set)


# class SanctionsRepository:
#     """Loads local UNSC, EU and OFAC XML files and performs exact/normalised name matching."""

#     def __init__(self):
#         self._entities: Dict[str, List[SanctionsEntity]] = {key: [] for key in SANCTIONS_FILES}
#         self._loaded = False

#     def load(self) -> None:
#         if self._loaded:
#             return
#         for list_name, filename in SANCTIONS_FILES.items():
#             if os.path.exists(filename):
#                 self._entities[list_name] = _extract_entities(list_name, filename)
#         self._loaded = True

#     def match(self, name: Optional[str]) -> List[Dict[str, str]]:
#         """Return every exact/normalised sanctions hit for the supplied name."""
#         self.load()
#         target = normalize_name(name)
#         if not target:
#             return []

#         hits = []
#         for list_name, entities in self._entities.items():
#             for entity in entities:
#                 if target in entity.names:
#                     hits.append(
#                         {
#                             "list": list_name,
#                             "entity_id": entity.entity_id,
#                             "matched_name": name,
#                         }
#                     )
#         return hits

#     def stats(self) -> Dict[str, int]:
#         self.load()
#         return {name: len(entities) for name, entities in self._entities.items()}


# def _extract_entities(list_name: str, filename: str) -> List[SanctionsEntity]:
#     entities: List[SanctionsEntity] = []
#     if not os.path.exists(filename):
#         return entities

#     try:
#         tree = ET.parse(filename)
#     except ET.ParseError:
#         return entities

#     root = tree.getroot()
#     for entity_elem in root.findall("entity"):
#         entity_id = entity_elem.get("id") or f"{list_name}-UNKNOWN"
#         entity = SanctionsEntity(entity_id=entity_id, list_name=list_name)

#         # Collect primary names, aliases and any free-text name fields.
#         for tag in ("name", "firstName", "lastName", "entityName"):
#             for elem in entity_elem.iter(tag):
#                 text = elem.text
#                 if text:
#                     normalized = normalize_name(text)
#                     if normalized:
#                         entity.names.add(normalized)

#         aliases_elem = entity_elem.find("aliases")
#         if aliases_elem is not None:
#             for alias_elem in aliases_elem.iter("alias"):
#                 text = alias_elem.text
#                 if text:
#                     normalized = normalize_name(text)
#                     if normalized:
#                         entity.names.add(normalized)

#         if entity.names:
#             entities.append(entity)

#     return entities


# sanctions_repo = SanctionsRepository()

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
    """Loads local UNSC, EU and OFAC XML files and performs flexible/normalized name matching."""

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
        """Return every flexible/normalized sanctions hit for the supplied name."""
        self.load()
        normalized_target = normalize_name(name)
        if not normalized_target:
            return []

        target_tokens = set(normalized_target.split())
        if not target_tokens:
            return []

        hits = []
        for list_name, entities in self._entities.items():
            for entity in entities:
                is_match = False
                for entity_name in entity.names:
                    name_tokens = set(entity_name.split())

                    # Flag if query tokens are a subset of entity tokens (or vice versa)
                    if target_tokens.issubset(name_tokens) or name_tokens.issubset(target_tokens):
                        is_match = True
                        break

                if is_match:
                    hits.append(
                        {
                            "list": list_name,
                            "entity_id": entity.entity_id,
                            "matched_name": name or "",
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
        # Stream large XML files with iterparse to prevent out-of-memory errors
        context = ET.iterparse(filename, events=("end",))
    except ET.ParseError:
        return entities

    for event, entity_elem in context:
        tag_name = entity_elem.tag.split("}")[-1].lower() if "}" in entity_elem.tag else entity_elem.tag.lower()

        if tag_name in ("sanctionentity", "entity", "sdnentry", "individual"):
            entity_id = (
                entity_elem.get("logicalId")
                or entity_elem.get("euReferenceNumber")
                or entity_elem.get("id")
                or f"{list_name}-UNKNOWN"
            )
            entity = SanctionsEntity(entity_id=entity_id, list_name=list_name)

            for alias_block in entity_elem.iter():
                alias_tag = alias_block.tag.split("}")[-1].lower() if "}" in alias_block.tag else alias_block.tag.lower()

                # Extract names stored in XML attributes (EU format)
                for attr_key, attr_val in alias_block.attrib.items():
                    if attr_key.lower() in ("wholename", "firstname", "lastname", "name", "entityname"):
                        normalized = normalize_name(attr_val)
                        if normalized:
                            entity.names.add(normalized)

                # Extract names from text nodes and nested elements
                if alias_tag in ("name", "alias", "wholename", "firstname", "lastname", "entityname"):
                    name_parts = []
                    if alias_block.text and alias_block.text.strip():
                        name_parts.append(alias_block.text.strip())

                    for child in alias_block:
                        child_tag = child.tag.split("}")[-1].lower() if "}" in child.tag else child.tag.lower()
                        if child_tag in ("firstname", "lastname", "first_name", "last_name", "name") and child.text:
                            name_parts.append(child.text.strip())

                    if name_parts:
                        full_name = " ".join(name_parts)
                        normalized = normalize_name(full_name)
                        if normalized:
                            entity.names.add(normalized)

            if entity.names:
                entities.append(entity)

            # Free RAM for processed elements
            entity_elem.clear()

    return entities


# Module instance required by app.services.scoring
sanctions_repo = SanctionsRepository()
