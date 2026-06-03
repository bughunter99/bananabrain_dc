"""Pathfinding system.

C++ equivalent: PathFinder.cpp/PathFinder.h

Provides pathfinding with:
- Cache for ramp high ground detection
- Area-based pathfinding
- Common path detection
"""

from typing import Any, ClassVar, Dict, List, Optional, Tuple


class PathFinder:
    """Singleton for path computation."""
    
    _instance: ClassVar[Optional['PathFinder']] = None
    
    def __init__(self) -> None:
        self.ramp_high_ground_cache_: Dict[Tuple[int, int], bool] = {}
        self.small_chokepoints_closed_ = False
        self.ramp_high_ground_: Dict[str, Tuple[int, int]] = {}
        self._paths_cache: Dict[tuple, List[Tuple[int, int]]] = {}
    
    @classmethod
    def Instance(cls) -> 'PathFinder':
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def init(self, snapshot: Optional[Dict[str, Any]] = None) -> None:
        """Initialize pathfinder."""
        self.small_chokepoints_closed_ = False
        self.ramp_high_ground_.clear()
        self.ramp_high_ground_cache_.clear()
        self._paths_cache.clear()
        self.update(snapshot)
    
    def update(self, snapshot: Optional[Dict[str, Any]] = None) -> None:
        """Update pathfinder from game state.
        
        Args:
            snapshot: Game state snapshot containing ramp information
        """
        snapshot = snapshot or {}
        
        # Load ramp high ground positions from snapshot
        for entry in snapshot.get("ramp_high_ground", []):
            if isinstance(entry, dict) and "ramp" in entry and "position" in entry:
                ramp = str(entry["ramp"])
                position = entry["position"]
                if isinstance(position, (list, tuple)) and len(position) == 2:
                    self.ramp_high_ground_[ramp] = (int(position[0]), int(position[1]))
    
    def find_path(self, start: Tuple[int, int], goal: Tuple[int, int]) -> List[Tuple[int, int]]:
        """Find path from start to goal position.
        
        Uses simple Euclidean distance-based path generation.
        In actual BWAPI implementation, this would use BWEM pathfinding.
        
        Args:
            start: Starting position (tile coordinates)
            goal: Goal position (tile coordinates)
            
        Returns:
            List of positions forming the path, or empty if unreachable
        """
        # Check cache
        cache_key = (start, goal)
        if cache_key in self._paths_cache:
            return list(self._paths_cache[cache_key])
        
        # Simple linear path from start to goal
        # In real implementation, this would compute actual walkable path
        path = [start, goal]
        self._paths_cache[cache_key] = path
        return path
    
    def is_ramp_high_ground(self, pos: Tuple[int, int]) -> bool:
        """Check if position is ramp high ground.
        
        Uses cached results for performance.
        
        Args:
            pos: Position to check
            
        Returns:
            True if position is on ramp high ground
        """
        if pos in self.ramp_high_ground_cache_:
            return self.ramp_high_ground_cache_[pos]
        
        result = self._compute_is_ramp_high_ground(pos)
        self.ramp_high_ground_cache_[pos] = result
        return result
    
    def _compute_is_ramp_high_ground(self, pos: Tuple[int, int]) -> bool:
        """Compute if position is on ramp high ground.
        
        Args:
            pos: Position to check
            
        Returns:
            True if position matches any known ramp high ground position
        """
        return any(pos == ramp_pos for ramp_pos in self.ramp_high_ground_.values())
    
    def clear_cache(self) -> None:
        """Clear pathfinding caches."""
        self.ramp_high_ground_cache_.clear()
        self._paths_cache.clear()

    def close_small_chokepoints_if_needed(self) -> None:
        """Mark small chokepoints as closed."""
        self.small_chokepoints_closed_ = True

    def first_common_path_position(self, position: Tuple[int, int], 
                                   destinations: List[Tuple[int, int]]) -> Tuple[int, int]:
        """Find first position common to all paths to destinations.
        
        C++ Logic:
            if (destinations.empty()) return position;
            
            std::vector<const BWEM::CPPath*> paths;
            for (Position destination : destinations) {
                int distance = -1;
                const BWEM::CPPath& path = bwem_map.GetPath(position, destination, &distance);
                if (distance < 0) return position;
                paths.push_back(&path);
            }
            
            Position result = position;
            const BWEM::CPPath& path0 = *paths[0];
            for (size_t i = 0; i < path0.size(); i++) {
                bool match = true;
                for (size_t j = 1; j < paths.size(); j++) {
                    const BWEM::CPPath& path = *paths[j];
                    if (i >= path.size() || path0[i] != path[i]) {
                        match = false;
                        break;
                    }
                }
                if (match) {
                    const BWEM::ChokePoint* cp = path0[i];
                    result = center_position(cp->Center());
                } else {
                    break;
                }
            }
            return result;
        
        Args:
            position: Starting position
            destinations: List of destination positions
            
        Returns:
            First position common to paths to all destinations
        """
        # If no destinations, return starting position
        if not destinations:
            return position
        
        # Get path to each destination
        paths = []
        for destination in destinations:
            path = self.find_path(position, destination)
            
            # If any path is unreachable (empty or invalid), return starting position
            if not path:
                return position
            
            paths.append(path)
        
        # Find common portion of all paths
        result = position
        path0 = paths[0]
        
        # Iterate through waypoints of first path
        for i in range(len(path0)):
            match = True
            
            # Check if all other paths have the same waypoint at this index
            for j in range(1, len(paths)):
                path = paths[j]
                
                # If path is shorter or waypoint differs, no more common path
                if i >= len(path) or path0[i] != path[i]:
                    match = False
                    break
            
            # If all paths match at this waypoint, update result
            if match:
                result = path0[i]
            else:
                # No more common path beyond this point
                break
        
        return result

    def ramp_high_ground(self, ramp_name: Any) -> Optional[Tuple[int, int]]:
        """Get ramp high ground position by name.
        
        Args:
            ramp_name: Ramp identifier
            
        Returns:
            Position of ramp high ground, or None if not found
        """
        return self.ramp_high_ground_.get(str(ramp_name))

    def execute_path(self, unit: Any, position: Tuple[int, int], command: Any) -> bool:
        """Execute a path command for a unit.
        
        Args:
            unit: Unit object
            position: Target position
            command: Command to execute
            
        Returns:
            True if command executed successfully
        """
        try:
            command()
            return True
        except Exception:
            return False

