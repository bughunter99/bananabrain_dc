"""Python counterpart of C++ BaseState.cpp / BaseState.h (BWAPI 4.4.0 BananaBrain)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar, Dict, List, Optional, Set, Tuple


@dataclass
class Border:
    """Border - areas on the boundary between controlled/uncontrolled."""
    inside_areas_: Set[str] = field(default_factory=set)
    outside_areas_: Set[str] = field(default_factory=set)
    chokepoints_: Set[str] = field(default_factory=set)

    def __init__(self, areas: Optional[Set[str]] = None):
        """Initialize from set of controlled areas."""
        self.inside_areas_ = set()
        self.outside_areas_ = set()
        self.chokepoints_ = set()
    
    def chokepoints_with_area(self, area: Optional[str]) -> List[str]:
        """Get chokepoints associated with given area."""
        if area is None:
            return []
        result = []
        for chokepoint in self.chokepoints_:
            # In Python representation, check if chokepoint connects to area
            if str(chokepoint).startswith(f"{area}_") or f"_{area}" in str(chokepoint):
                result.append(chokepoint)
        return result
    
    def largest_chokepoint_with_area(self, area: Optional[str]) -> Optional[str]:
        """Get largest chokepoint associated with given area."""
        chokepoints = self.chokepoints_with_area(area)
        if not chokepoints:
            return None
        # Return first chokepoint (in Python, would need width data for true "largest")
        return chokepoints[0] if chokepoints else None


@dataclass
class BaseState:
    """Python mirror of C++ BaseState (Singleton pattern)."""
    
    _instance: ClassVar[Optional["BaseState"]] = None
    kLargeAreaAltitude: ClassVar[int] = 640
    
    bases_: List[Dict[str, Any]] = field(default_factory=list)
    base_map_: Dict[Tuple[int, int], Dict[str, Any]] = field(default_factory=dict)
    area_graph_: Dict[str, Set[str]] = field(default_factory=dict)
    base_area_map_: Dict[Tuple[int, int], str] = field(default_factory=dict)
    start_to_natural_map_: Dict[Tuple[int, int], Tuple[int, int]] = field(default_factory=dict)
    start_extension_map_: Dict[Tuple[int, int], str] = field(default_factory=dict)
    controlled_bases_: Set[Tuple[int, int]] = field(default_factory=set)
    controlled_and_planned_bases_: Set[Tuple[int, int]] = field(default_factory=set)
    controlled_areas_: Set[str] = field(default_factory=set)
    controlled_and_planned_areas_: Set[str] = field(default_factory=set)
    opponent_bases_: Set[Tuple[int, int]] = field(default_factory=set)
    border_: Border = field(default_factory=Border)
    next_available_bases_: List[Dict[str, Any]] = field(default_factory=list)
    unexplored_start_bases_: List[Dict[str, Any]] = field(default_factory=list)
    base_last_seen_: Dict[Tuple[int, int], int] = field(default_factory=dict)
    start_base_: Optional[Tuple[int, int]] = None
    natural_base_: Optional[Tuple[int, int]] = None
    backdoor_natural_: bool = False
    island_map_: bool = False
    skip_mineral_only_: bool = False
    frame_: int = 0

    @classmethod
    def Instance(cls) -> "BaseState":
        """Singleton accessor (C++ style)."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def init_bases(self, snapshot: Optional[Dict[str, Any]] = None) -> None:
        """Initialize bases from BWEM (C++ BananaBrain::init_bases parity)."""
        state = snapshot or {}
        
        # Load all bases from snapshot
        self._load_base_catalog(state)
        
        # Map each base by tile position
        for base in self.bases_:
            tile = self._tile_of_base(base)
            if tile is None:
                continue
            
            self.base_map_[tile] = base
            
            # Store area name for tile
            area_name = self._area_name_of_base(base)
            if area_name is not None:
                self.base_area_map_[tile] = area_name
            
            # For starting bases, compute natural and extension
            if base.get("starting"):
                natural_base_tile = self.determine_natural(base, state)
                if natural_base_tile is not None:
                    self.start_to_natural_map_[tile] = natural_base_tile
                    natural_base = self.base_map_.get(natural_base_tile)
                    if natural_base:
                        ext_area = self.determine_start_extension(base, natural_base, state)
                        if ext_area:
                            self.start_extension_map_[tile] = ext_area
        
        # Update controlled bases and areas
        self.update_base_information(state)
        
        # Resolve start base
        self.start_base_ = self._resolve_start_base(state)
        if self.start_base_ is not None:
            self.natural_base_ = self.start_to_natural_map_.get(self.start_base_)
            start_area = self._area_for_tile(self.start_base_)
            natural_area = self._area_for_tile(self.natural_base_) if self.natural_base_ else None
            
            # Check backdoor natural
            if start_area and natural_area:
                self.backdoor_natural_ = natural_area in self.enclosed_areas({start_area})
            
            # Check island map
            self.island_map_ = self._compute_island_map(start_area)
        else:
            self.natural_base_ = None
            self.backdoor_natural_ = False
            self.island_map_ = False

    def update_base_information(self, snapshot: Optional[Dict[str, Any]] = None) -> None:
        """Update base information from snapshot (C++ BananaBrain::update_base_information parity)."""
        state = snapshot or {}
        self.frame_ = int(state.get("frame") or 0)
        
        # Reload bases if provided
        if state.get("bases") is not None:
            self._load_base_catalog(state)
        
        # Parse tile pairs for bases
        self.start_base_ = self._parse_tile_pair(state.get("self_start")) or self.start_base_
        self.natural_base_ = self._parse_tile_pair(state.get("natural_start")) or self.natural_base_
        
        # Rebuild base_map from current bases
        self.base_map_ = {
            tile: base
            for base in self.bases_
            if (tile := self._tile_of_base(base)) is not None
        }
        
        # Parse controlled bases
        self.controlled_bases_ = self._parse_tile_set(state.get("controlled_bases", set()))
        self.controlled_and_planned_bases_ = (
            self._parse_tile_set(state.get("controlled_and_planned_bases", set()))
            or set(self.controlled_bases_)
        )
        
        # Parse controlled areas
        self.controlled_areas_ = self._parse_text_set(state.get("controlled_areas", set()))
        self.controlled_and_planned_areas_ = (
            self._parse_text_set(state.get("controlled_and_planned_areas", set()))
            or set(self.controlled_areas_)
        )
        
        # Parse opponent bases
        self.opponent_bases_ = self._parse_tile_set(state.get("opponent_bases", set()))
        
        # Compute derived lists
        self.next_available_bases_ = [
            base for base in self.bases_
            if self._tile_of_base(base) not in self.controlled_and_planned_bases_
        ]
        
        self.unexplored_start_bases_ = [
            base for base in self.bases_
            if base.get("starting") and not base.get("explored")
        ]
        
        self.base_last_seen_ = self._parse_base_seen(state.get("base_last_seen", {}))
        
        # Update border
        self.border_ = Border(self.controlled_and_planned_areas_)


    # Public accessor methods (matching C++)
    
    def bases(self) -> List[Dict[str, Any]]:
        """Return list of all bases."""
        return list(self.bases_)

    def base_for_tile_position(self, tile_position: Tuple[int, int]) -> Optional[Dict[str, Any]]:
        """Get base at given tile position."""
        return self.base_map_.get(tuple(tile_position))

    def natural_base_for_start_base(self, start_base: Tuple[int, int]) -> Optional[Tuple[int, int]]:
        """Get natural base for a given starting base."""
        return self.start_to_natural_map_.get(tuple(start_base))

    def extension_area_for_start_base(self, start_base: Tuple[int, int]) -> Optional[str]:
        """Get extension area for a given starting base."""
        return self.start_extension_map_.get(tuple(start_base))

    def controlled_bases(self) -> Set[Tuple[int, int]]:
        """Return controlled bases."""
        return set(self.controlled_bases_)

    def controlled_and_planned_bases(self) -> Set[Tuple[int, int]]:
        """Return controlled and planned bases."""
        return set(self.controlled_and_planned_bases_)

    def controlled_areas(self) -> Set[str]:
        """Return controlled areas."""
        return set(self.controlled_areas_)

    def controlled_and_planned_areas(self) -> Set[str]:
        """Return controlled and planned areas."""
        return set(self.controlled_and_planned_areas_)

    def border(self) -> Border:
        """Return border information."""
        return self.border_

    def opponent_bases(self) -> Set[Tuple[int, int]]:
        """Return opponent bases."""
        return set(self.opponent_bases_)

    def unexplored_start_bases(self) -> List[Dict[str, Any]]:
        """Return unexplored starting bases."""
        return list(self.unexplored_start_bases_)

    def base_last_seen(self, base: Tuple[int, int]) -> int:
        """Get frame when base was last seen (-1 if never)."""
        return int(self.base_last_seen_.get(tuple(base), -1))

    def next_available_bases(self) -> List[Dict[str, Any]]:
        """Return next available bases for expansion."""
        return list(self.next_available_bases_)

    def start_base(self) -> Optional[Tuple[int, int]]:
        """Get our starting base."""
        return self.start_base_

    def natural_base(self) -> Optional[Tuple[int, int]]:
        """Get our natural base."""
        return self.natural_base_

    def is_backdoor_natural(self) -> bool:
        """Check if natural base is backdoor."""
        return self.backdoor_natural_

    def is_island_map(self) -> bool:
        """Check if map is island-style."""
        return self.island_map_

    def main_base(self) -> Optional[Tuple[int, int]]:
        """Get current main base (expansion)."""
        if len(self.controlled_bases_) == 1:
            return next(iter(self.controlled_bases_))
        if self.start_base_ in self.controlled_bases_:
            return self.start_base_
        return None

    def start_base_count(self) -> int:
        """Get number of starting bases on map."""
        return len(self.start_to_natural_map_)

    def controlled_geyser_count(self) -> int:
        """Count total geysers in controlled bases."""
        count = 0
        for base in self.bases_:
            if self._tile_of_base(base) in self.controlled_bases_:
                count += len(base.get("geysers", []))
        return count

    def mining_base_count(self) -> int:
        """Count controlled bases with minerals."""
        count = 0
        for base in self.bases_:
            if self._tile_of_base(base) in self.controlled_bases_:
                if base.get("minerals", []):
                    count += 1
        return count

    def mineable_mineral_count(self) -> int:
        """Get total mineable minerals in controlled and planned bases."""
        total = 0
        for base in self.bases_:
            if self._tile_of_base(base) in self.controlled_and_planned_bases_:
                total += base.get("mineable_minerals", 0)
        return total

    def skip_mineral_only(self) -> bool:
        """Get skip_mineral_only flag."""
        return self.skip_mineral_only_

    def set_skip_mineral_only(self, skip_mineral_only: bool) -> None:
        """Set skip_mineral_only flag."""
        self.skip_mineral_only_ = bool(skip_mineral_only)

    def undiscovered_starting_bases(self, overlord: bool = False) -> List[Dict[str, Any]]:
        """Get unexplored starting bases (C++ undiscovered_starting_bases parity)."""
        result = []
        for base in self.bases_:
            if base.get("starting") and not base.get("explored"):
                result.append(base)
        return result

    # Area connectivity methods (matching C++ implementations)

    def enclosed_areas(self, areas: Set[str]) -> Set[str]:
        """Get areas enclosed by given controlled areas (C++ BananaBrain::enclosed_areas parity)."""
        if not areas:
            return set()

        # Find uncontrolled base areas
        uncontrolled_base_areas = set()
        for base in self.bases_:
            base_area = self._area_name_of_base(base)
            if base_area and base_area not in areas:
                # Check if this is an opponent or uncontrolled base
                if not self.opponent_bases_:
                    # No opponent bases known, so all non-controlled starting bases are enemies
                    if base.get("starting"):
                        uncontrolled_base_areas.add(base_area)
                elif self._tile_of_base(base) in self.opponent_bases_:
                    uncontrolled_base_areas.add(base_area)

        result = set(areas)
        
        # Check all areas to see if enclosed
        for area in self.area_graph_.keys():
            reachable = self._reachable_areas(area)
            reachable_blocked = self._reachable_areas(area, areas)
            
            # Area is enclosed if reachable from ours and blocked from uncontrolled
            if reachable.intersection(areas) and not reachable_blocked.intersection(uncontrolled_base_areas):
                result.add(area)

        return result

    @staticmethod
    def reachable_areas(area: str, blocked_areas: Optional[Set[str]] = None) -> Set[str]:
        """Static method for reachable areas (C++ signature match)."""
        blocked = set(blocked_areas or set())
        return {area} if area not in blocked else set()

    @staticmethod
    def connected_areas(area: str, allowed_areas: Set[str]) -> Set[str]:
        """Static method for connected areas within allowed set."""
        return {area} if area in allowed_areas else set()

    def is_base_enclosed(self, start_base: Tuple[int, int], natural_base: Tuple[int, int], other_base: Tuple[int, int]) -> bool:
        """Check if other_base is enclosed given start and natural control."""
        start_area = self._area_for_tile(start_base)
        other_area = self._area_for_tile(other_base)
        if not start_area or not other_area:
            return False
        enclosed = self.enclosed_areas({start_area})
        return other_area in enclosed

    # Base determination methods

    def determine_natural(self, start_base: Dict[str, Any], snapshot: Optional[Dict[str, Any]] = None) -> Optional[Tuple[int, int]]:
        """Determine natural base for starting base (C++ BananaBrain::determine_natural parity)."""
        state = snapshot or {}
        start_tile = self._tile_of_base(start_base)
        if start_tile is None:
            return None

        # Check for override
        override = self._parse_tile_pair(state.get("natural_start"))
        if override is not None:
            return override

        # Find non-starting candidates
        candidates = [b for b in self.bases_ if not b.get("starting") and self._tile_of_base(b) is not None]
        if not candidates:
            return None

        # Sort by distance, mineral+gas, position
        def sort_key(base: Dict[str, Any]) -> tuple:
            base_tile = self._tile_of_base(base)
            dist = self._manhattan_distance(start_tile, base_tile) if base_tile else 10**9
            has_both = 0 if self._has_minerals_and_gas(base) else 1
            return (dist, has_both, base_tile or (10**9, 10**9))

        ordered = sorted(candidates, key=sort_key)
        result = self._tile_of_base(ordered[0])

        # Special case: if first is mineral-only and second has both, pick second if enclosed
        if len(ordered) >= 2:
            first = ordered[0]
            second = ordered[1]
            if (not self._has_minerals_and_gas(first)) and self._has_minerals_and_gas(second):
                first_tile = self._tile_of_base(first)
                second_tile = self._tile_of_base(second)
                if first_tile and second_tile and self.is_base_enclosed(start_tile, second_tile, first_tile):
                    result = second_tile

        return result

    def determine_start_extension(self, start_base: Dict[str, Any], natural_base: Dict[str, Any], snapshot: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """Determine extension area for starting base (C++ determine_start_extension parity)."""
        state = snapshot or {}
        start_tile = self._tile_of_base(start_base)
        if start_tile is None:
            return None

        # Check for override from snapshot
        override = self._area_name_of_base_by_tile(state.get("start_extension_map"), start_tile)
        if override is not None:
            return override

        start_area = self._area_name_of_base(start_base)
        natural_area = self._area_name_of_base(natural_base)
        if not start_area or not natural_area:
            return None

        # Find area connected to both start and natural
        start_and_natural_areas = {start_area, natural_area}
        candidates = []
        
        for area in self.area_graph_.get(start_area, set()):
            area_neighbours = self.area_graph_.get(area, set())
            if area_neighbours == start_and_natural_areas:
                candidates.append(area)

        return candidates[0] if len(candidates) == 1 else None

    def determine_pylon_and_bunker_areas(self, completed: bool = False, snapshot: Optional[Dict[str, Any]] = None) -> Set[str]:
        """Determine areas containing Pylons and Bunkers (C++ determine_pylon_and_bunker_areas parity)."""
        state = snapshot or {}
        result: Set[str] = set()

        # Check completed units (buildings)
        units = state.get("units", []) or []
        for unit in units:
            unit_type = unit.get("type")
            tile_pos = self._parse_tile_pair(unit.get("tile_position") or unit.get("tile"))
            
            if not tile_pos:
                continue
            
            # Check Protoss Pylon
            if unit_type == "Protoss_Pylon" and (not completed or unit.get("completed")):
                # Skip proxy pylon (would need building_placement_manager reference)
                area = self._area_for_tile(tile_pos)
                if area:
                    # Check if FFE pylon (would need is_ffe_pylon check)
                    # For now, use natural base area if available
                    if self.natural_base_:
                        natural_area = self._area_for_tile(self.natural_base_)
                        if natural_area:
                            result.add(natural_area)
                    else:
                        result.add(area)
            
            # Check Terran Bunker
            elif unit_type == "Terran_Bunker" and (not completed or unit.get("completed")):
                area = self._area_for_tile(tile_pos)
                if area:
                    result.add(area)

        # Check incomplete units (workers building)
        if not completed:
            workers = state.get("workers", {}) or {}
            for worker_id, worker_info in workers.items() if isinstance(workers, dict) else enumerate(workers):
                building_type = worker_info.get("building_type")
                building_pos = self._parse_tile_pair(worker_info.get("building_position") or worker_info.get("building_tile"))
                
                if not building_pos:
                    continue
                
                # Check Protoss Pylon
                if building_type == "Protoss_Pylon":
                    area = self._area_for_tile(building_pos)
                    if area:
                        if self.natural_base_:
                            natural_area = self._area_for_tile(self.natural_base_)
                            if natural_area:
                                result.add(natural_area)
                        else:
                            result.add(area)
                
                # Check Terran Bunker
                elif building_type == "Terran_Bunker":
                    area = self._area_for_tile(building_pos)
                    if area:
                        result.add(area)

        return result


    # Private helper methods

    # Update methods (C++ private update methods)

    def _update_controlled_bases(self) -> None:
        """Update controlled bases from current game state."""
        # Called from update_base_information()
        pass
    
    def _update_opponent_bases(self) -> None:
        """Update opponent bases from current game state."""
        # Called from update_base_information()
        pass
    
    def _update_border(self) -> None:
        """Update border information from controlled areas."""
        self.border_ = Border(self.controlled_and_planned_areas_)
    
    def _update_next_available_bases(self) -> None:
        """Update list of next available bases for expansion."""
        self.next_available_bases_ = [
            base for base in self.bases_
            if self._tile_of_base(base) not in self.controlled_and_planned_bases_
        ]
    
    def _update_unexplored_start_bases(self) -> None:
        """Update list of unexplored starting bases."""
        self.unexplored_start_bases_ = [
            base for base in self.bases_
            if base.get("starting") and not base.get("explored")
        ]
    
    def _update_base_last_seen(self) -> None:
        """Update base_last_seen mapping."""
        # Update would come from game state updates
        pass

    # Helper methods

    def _load_base_catalog(self, state: Dict[str, Any]) -> None:
        """Load base catalog from snapshot."""
        self.bases_ = self._parse_bases(state)
        self.area_graph_ = self._parse_area_graph(state)

    def _reset_base_catalog(self) -> None:
        """Reset all base tracking data."""
        self.bases_.clear()
        self.base_map_.clear()
        self.area_graph_.clear()
        self.base_area_map_.clear()
        self.start_to_natural_map_.clear()
        self.start_extension_map_.clear()
        self.start_base_ = None
        self.natural_base_ = None
        self.backdoor_natural_ = False
        self.island_map_ = False

    def _resolve_start_base(self, state: Dict[str, Any]) -> Optional[Tuple[int, int]]:
        """Resolve starting base from snapshot or bases list."""
        start_base = self._parse_tile_pair(state.get("self_start"))
        if start_base is not None:
            return start_base
        
        # Find first starting base
        for base in self.bases_:
            if base.get("starting"):
                tile = self._tile_of_base(base)
                if tile is not None:
                    return tile
        return None

    def _parse_bases(self, state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse bases from snapshot."""
        bases = []
        raw_bases = state.get("bases", [])
        if isinstance(raw_bases, list):
            for entry in raw_bases:
                if isinstance(entry, dict):
                    bases.append(entry)
        return bases

    def _parse_area_graph(self, state: Dict[str, Any]) -> Dict[str, Set[str]]:
        """Parse area connectivity graph."""
        result: Dict[str, Set[str]] = {}
        raw_graph = state.get("area_graph") or state.get("areas") or {}
        
        if isinstance(raw_graph, dict):
            for area_name, neighbours in raw_graph.items():
                name = str(area_name)
                if isinstance(neighbours, (list, tuple, set)):
                    result[name] = {str(item) for item in neighbours if str(item)}
                else:
                    result[name] = set()
        elif isinstance(raw_graph, list):
            for entry in raw_graph:
                if not isinstance(entry, dict):
                    continue
                name = str(entry.get("name") or entry.get("area") or entry.get("id") or "")
                if not name:
                    continue
                neighbours = entry.get("accessible_neighbours") or entry.get("neighbours") or []
                if isinstance(neighbours, (list, tuple, set)):
                    result[name] = {str(item) for item in neighbours if str(item)}
                else:
                    result[name] = set()
        
        return result

    def _area_name_of_base(self, base: Dict[str, Any]) -> Optional[str]:
        """Extract area name from base."""
        area = base.get("area") or base.get("area_name") or base.get("region")
        if area is None:
            return None
        text = str(area).strip()
        return text or None

    def _area_name_of_base_by_tile(self, mapping: Any, tile: Tuple[int, int]) -> Optional[str]:
        """Get area name from mapping by tile."""
        if isinstance(mapping, dict):
            raw = mapping.get(f"{tile[0]},{tile[1]}") or mapping.get(tile) or mapping.get(tuple(tile))
            if raw is not None:
                text = str(raw).strip()
                return text or None
        return None

    def _area_for_tile(self, tile: Optional[Tuple[int, int]]) -> Optional[str]:
        """Get area name for tile position."""
        if tile is None:
            return None
        
        if tile in self.base_area_map_:
            return self.base_area_map_[tile]
        
        base = self.base_map_.get(tuple(tile))
        if base is None:
            return None
        
        return self._area_name_of_base(base)

    def _reachable_areas(self, area: str, blocked_areas: Optional[Set[str]] = None) -> Set[str]:
        """Get areas reachable from given area without crossing blocked areas (C++ reachable_areas)."""
        blocked = set(blocked_areas or set())
        if area in blocked:
            return set()
        
        queue = [area]
        seen = {area}
        result = set()
        
        while queue:
            current = queue.pop(0)
            result.add(current)
            
            for neighbour in self.area_graph_.get(current, set()):
                if neighbour not in seen and neighbour not in blocked:
                    seen.add(neighbour)
                    queue.append(neighbour)
        
        return result

    def _compute_island_map(self, start_area: Optional[str]) -> bool:
        """Check if map is island-style (starting bases unreachable from each other)."""
        if not start_area:
            return False
        
        reachable_from_start = self._reachable_areas(start_area)
        
        for base in self.bases_:
            if not base.get("starting"):
                continue
            
            area_name = self._area_name_of_base(base)
            if area_name and area_name not in reachable_from_start:
                return True
        
        return False

    def _parse_distance_map(self, value: Any) -> Dict[Tuple[int, int], int]:
        """Parse distance map from snapshot."""
        result: Dict[Tuple[int, int], int] = {}
        if isinstance(value, dict):
            for key, distance in value.items():
                parsed = self._parse_tile_pair(key)
                if parsed is None:
                    continue
                try:
                    result[parsed] = int(distance)
                except (TypeError, ValueError):
                    continue
        return result

    @staticmethod
    def _parse_tile_pair(value: Any) -> Optional[Tuple[int, int]]:
        """Parse tile pair from various formats."""
        text = str(value or "").strip()
        if not text:
            return None
        
        parts = text.split(",")
        if len(parts) != 2:
            return None
        
        try:
            return (int(parts[0]), int(parts[1]))
        except ValueError:
            return None

    def _parse_tile_set(self, value: Any) -> Set[Tuple[int, int]]:
        """Parse set of tile positions."""
        result: Set[Tuple[int, int]] = set()
        for entry in self._parse_semicolon_entries(value):
            parsed = self._parse_tile_pair(entry)
            if parsed is not None:
                result.add(parsed)
        return result

    @staticmethod
    def _parse_text_set(value: Any) -> Set[str]:
        """Parse set of text values."""
        if isinstance(value, (list, tuple, set)):
            return {str(item).strip() for item in value if str(item).strip()}
        
        text = str(value or "")
        return {part.strip() for part in text.split(";") if part.strip()}

    @staticmethod
    def _parse_semicolon_entries(value: Any) -> List[str]:
        """Parse semicolon-separated entries."""
        if isinstance(value, (list, tuple)):
            return [str(item).strip() for item in value if str(item).strip()]
        
        return [part.strip() for part in str(value or "").split(";") if part.strip()]

    @staticmethod
    def _manhattan_distance(a: Optional[Tuple[int, int]], b: Optional[Tuple[int, int]]) -> int:
        """Compute Manhattan distance between tile positions."""
        if a is None or b is None:
            return 10**9
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    @staticmethod
    def _has_minerals_and_gas(base: Dict[str, Any]) -> bool:
        """Check if base has both minerals and geysers."""
        return bool(base.get("minerals")) and bool(base.get("geysers"))

    @staticmethod
    def _tile_of_base(base: Dict[str, Any]) -> Optional[Tuple[int, int]]:
        """Extract tile position from base dict."""
        tile = base.get("tile") or base.get("location") or base.get("tile_position")
        
        if isinstance(tile, (list, tuple)) and len(tile) == 2:
            try:
                return (int(tile[0]), int(tile[1]))
            except (TypeError, ValueError):
                return None
        
        if isinstance(tile, str):
            parts = tile.split(",")
            if len(parts) == 2:
                try:
                    return (int(parts[0]), int(parts[1]))
                except ValueError:
                    return None
        
        return None

    @staticmethod
    def _parse_base_seen(value: Any) -> Dict[Tuple[int, int], int]:
        """Parse base_last_seen map."""
        result: Dict[Tuple[int, int], int] = {}
        if isinstance(value, dict):
            for key, seen_frame in value.items():
                parsed = BaseState._parse_tile_pair(key)
                if parsed is not None:
                    try:
                        result[parsed] = int(seen_frame)
                    except (TypeError, ValueError):
                        continue
        return result
    
    @staticmethod
    def is_ffe_pylon(tile_position: Tuple[int, int]) -> bool:
        """Check if pylon is FFE (Fast Expansion) pylon (C++ is_ffe_pylon parity)."""
        # FFE pylon is placed at specific map positions early game
        # This is a heuristic: true if placed outside natural base area
        # Would need more context from game state to determine accurately
        return False  # Placeholder
    
    def controlled_areas_from_bases(self, controlled_bases: Set[Tuple[int, int]], pylon_areas: Optional[Set[str]] = None) -> Set[str]:
        """Compute controlled areas from bases and pylon areas (C++ parity)."""
        pylon_areas = pylon_areas or set()
        result = set()
        
        # Add areas from controlled bases
        for base_tile in controlled_bases:
            area = self._area_for_tile(base_tile)
            if area:
                result.add(area)
        
        # Add pylon areas
        result.update(pylon_areas)
        
        # Add enclosed areas
        if result:
            enclosed = self.enclosed_areas(result)
            result.update(enclosed)
        
        return result
    
    @staticmethod
    def is_base_with_both_minerals_and_gas(base: Dict[str, Any]) -> bool:
        """Check if base has both minerals and geysers (alias for _has_minerals_and_gas)."""
        return bool(base.get("minerals")) and bool(base.get("geysers"))
    
    @staticmethod
    def is_large_area(area: Optional[str]) -> bool:
        """Check if area is large (altitude >= kLargeAreaAltitude)."""
        # Would need area data with altitude information
        # Placeholder - in real implementation, check area properties
        return False

    def draw(self) -> None:
        """Draw debug information (C++ draw parity)."""
        self.draw_bases()
        self.draw_areas()
    
    def draw_bases(self) -> None:
        """Draw base locations and information."""
        # In Python, drawing is handled by UI, not AI
        pass
    
    def draw_areas(self) -> None:
        """Draw area information."""
        # In Python, drawing is handled by UI, not AI
        pass
    
    def draw_unit_rectangle(self, tile_position: Tuple[int, int], unit_type: str, color: str) -> None:
        """Draw unit rectangle at position."""
        # In Python, drawing is handled by UI, not AI
        pass

