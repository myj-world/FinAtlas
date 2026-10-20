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

import os
import xml.etree.ElementTree as ET
from typing import List, Dict, Set, Optional

# Assuming this exists based on your previous initialization error
SANCTIONS_FILES = ["EU", "UNSC", "OFAC"]

def normalize_name(name: Optional[str]) -> str:
    """Helper function to normalize strings for comparison."""
    if not name:
        return ""
    # Strip punctuation and convert to lowercase
    return " ".join(name.lower().replace("-", " ").replace(",", "").split())

class SanctionsEntity:
    def __init__(self, entity_id: str, list_name: str):
        self.entity_id = entity_id
        self.list_name = list_name
        self.names: Set[str] = set()

def _extract_entities(list_name: str, filename: str) -> List[SanctionsEntity]:
    entities: List[SanctionsEntity] = []
    if not os.path.exists(filename):
        return entities

    try:
        # FIX: Use iterparse to stream large XML files and prevent memory crashes
        context = ET.iterparse(filename, events=("end",))
    except ET.ParseError:
        return entities

    for event, entity_elem in context:
        # Strip namespaces dynamically
        tag_name = entity_elem.tag.split("}")[-1].lower() if "}" in entity_elem.tag else entity_elem.tag.lower()
        
        # FIX: Only process top-level targets to prevent duplicating nested entities
        if tag_name in ("sanctionentity", "entity", "sdnentry", "individual"):
            entity_id = (
                entity_elem.get("logicalId") 
                or entity_elem.get("euReferenceNumber") 
                or entity_elem.get("id") 
                or f"{list_name}-UNKNOWN"
            )
            entity = SanctionsEntity(entity_id=entity_id, list_name=list_name)

            # Process descendants for names and aliases
            for alias_block in entity_elem.iter():
                alias_tag = alias_block.tag.split("}")[-1].lower() if "}" in alias_block.tag else alias_block.tag.lower()
                
                # FIX: Extract from attributes (Crucial for EU XML)
                for attr_key, attr_val in alias_block.attrib.items():
                    if attr_key.lower() in ("wholename", "firstname", "lastname", "name", "entityname"):
                        normalized = normalize_name(attr_val)
                        if normalized:
                            entity.names.add(normalized)

                # FIX: Combine inner text correctly if names are broken into separate child tags
                if alias_tag in ("name", "alias", "wholename"):
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
            
            # Free memory for processed elements
            entity_elem.clear()

    return entities

class SanctionsRepository:
    def __init__(self):
        # FIX: Ensure dictionary handles dynamically added lists cleanly
        self._entities: Dict[str, List[SanctionsEntity]] = {key: [] for key in SANCTIONS_FILES}
        
    def load_data(self, list_name: str, filename: str):
        if list_name not in self._entities:
            self._entities[list_name] = []
        self._entities[list_name].extend(_extract_entities(list_name, filename))

    def match(self, target: str) -> List[SanctionsEntity]:
        hits = []
        normalized_target = normalize_name(target)
        target_tokens = set(normalized_target.split())
        
        if not target_tokens:
            return hits

        for list_name, entities in self._entities.items():
            for entity in entities:
                # FIX: Token-overlap matching instead of rigid exact match (target in entity.names)
                is_match = False
                for name in entity.names:
                    name_tokens = set(name.split())
                    
                    # If the query is completely found within the entity name, or vice versa
                    if target_tokens.issubset(name_tokens) or name_tokens.issubset(target_tokens):
                        is_match = True
                        break
                        
                if is_match:
                    hits.append(entity)
                    
        return hits