import os
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from app.config import SANCTIONS_FILES


def normalize_name(name: Optional[str]) -> str:
    """Strip punctuation and convert to lowercase for comparison."""
    if not name:
        return ""
    # Strip a wider array of punctuation that disrupts token generation
    for char in "-,.'\"()&":
        name = name.replace(char, " ")
    return " ".join(name.lower().split())


@dataclass
class SanctionsEntity:
    entity_id: str
    list_name: str
    names: Set[str] = field(default_factory=set)


class SanctionsRepository:
    """Loads local UNSC, EU and OFAC XML files and performs flexible token matching."""

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
                    
                    # Forward check: Are all target tokens satisfied by an entity token?
                    # Uses exact match OR prefix match for words >= 4 chars (handles "INTERNATI")
                    target_in_name = all(
                        any(
                            n_tok == t_tok or 
                            (len(t_tok) >= 4 and n_tok.startswith(t_tok)) or 
                            (len(n_tok) >= 4 and t_tok.startswith(n_tok))
                            for n_tok in name_tokens
                        )
                        for t_tok in target_tokens
                    )
                    
                    # Backward check: Are all entity tokens satisfied by a target token?
                    name_in_target = all(
                        any(
                            t_tok == n_tok or 
                            (len(n_tok) >= 4 and t_tok.startswith(n_tok)) or 
                            (len(t_tok) >= 4 and n_tok.startswith(t_tok))
                            for t_tok in target_tokens
                        )
                        for n_tok in name_tokens
                    )
                    
                    if target_in_name or name_in_target:
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
        context = ET.iterparse(filename, events=("end",))
    except ET.ParseError:
        return entities

    for event, entity_elem in context:
        tag_name = entity_elem.tag.split("}")[-1].lower() if "}" in entity_elem.tag else entity_elem.tag.lower()

        if tag_name in ("sanctionentity", "entity", "sdnentry", "individual", "profile"):
            entity_id = (
                entity_elem.get("logicalId")
                or entity_elem.get("euReferenceNumber")
                or entity_elem.get("id")
                or f"{list_name}-UNKNOWN"
            )
            entity = SanctionsEntity(entity_id=entity_id, list_name=list_name)

            # 1. Catch flat UN XML names (e.g., FIRST_NAME, SECOND_NAME directly under ENTITY)
            primary_name_parts = []
            for child in entity_elem:
                child_tag = child.tag.split("}")[-1].lower() if "}" in child.tag else child.tag.lower()
                if child_tag in ("first_name", "second_name", "third_name", "last_name", "firstname", "lastname", "entity_name"):
                    if child.text and child.text.strip():
                        primary_name_parts.append(child.text.strip())
            if primary_name_parts:
                normalized = normalize_name(" ".join(primary_name_parts))
                if normalized:
                    entity.names.add(normalized)

            # 2. Catch nested OFAC aliases & EU attributes
            for alias_block in entity_elem.iter():
                alias_tag = alias_block.tag.split("}")[-1].lower() if "}" in alias_block.tag else alias_block.tag.lower()

                # EU List stores names inside XML attributes
                for attr_key, attr_val in alias_block.attrib.items():
                    if attr_key.lower() in ("wholename", "firstname", "lastname", "name", "entityname"):
                        normalized = normalize_name(attr_val)
                        if normalized:
                            entity.names.add(normalized)

                # OFAC List stores names in tags that wrap individual name parts
                if alias_tag in ("name", "alias", "wholename", "entityname", "aka", "documentedname", "lastname"):
                    name_parts = []
                    if alias_block.text and alias_block.text.strip():
                        name_parts.append(alias_block.text.strip())
                    
                    for child in alias_block:
                        child_tag = child.tag.split("}")[-1].lower() if "}" in child.tag else child.tag.lower()
                        if "name" in child_tag or child_tag in ("value", "part", "first_name", "last_name", "firstname", "lastname"):
                            if child.text and child.text.strip():
                                name_parts.append(child.text.strip())
                                
                    if name_parts:
                        normalized = normalize_name(" ".join(name_parts))
                        if normalized:
                            entity.names.add(normalized)

            if entity.names:
                entities.append(entity)

            # Free RAM for processed elements
            entity_elem.clear()

    return entities


# Module instance required by app.services.scoring
sanctions_repo = SanctionsRepository()
