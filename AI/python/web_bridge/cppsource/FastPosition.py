"""Fast position types for spatial calculations in BananaBrain.

Maps C++ FastPosition, FastWalkPosition, FastTilePosition structs to Python.
These are optimized position types used for grid-based calculations.

Coordinate conversions:
- FastPosition: Game pixel coordinates (x, y) - 32x32 = 1 tile
- FastWalkPosition: Walk coordinates (x, y) - 4x4 = 1 tile, 8x8 = 1 pixel  
- FastTilePosition: Tile coordinates (x, y)

Map dimensions:
- Tiles: [0, mapWidth) x [0, mapHeight)
- Pixels: [0, mapWidth*32) x [0, mapHeight*32)
- Walk: [0, mapWidth*4) x [0, mapHeight*4)
"""

import math
from dataclasses import dataclass
from typing import Tuple, Optional, Any


# Singleton stub for map dimensions (would be filled from game state)
class _MapDimensions:
    width: int = 256
    height: int = 256
    
    @classmethod
    def set_dimensions(cls, w: int, h: int):
        cls.width = w
        cls.height = h


@dataclass(frozen=True)
class FastPosition:
    """Game pixel coordinate (32x32 per tile)."""
    x: int = 0
    y: int = 0
    
    def __post_init__(self):
        # Validate object state (frozen dataclass)
        if self.x == -1 and self.y == -1:  # Special None value
            pass
    
    @property
    def is_none(self) -> bool:
        """Check if this is the special None position."""
        return self.x == -1 and self.y == -1
    
    def is_valid(self) -> bool:
        """Check if position is within map bounds."""
        return (0 <= self.x < _MapDimensions.width * 32 and 
                0 <= self.y < _MapDimensions.height * 32)
    
    def make_valid(self) -> 'FastPosition':
        """Clamp position to valid map bounds."""
        x = max(0, min(self.x, _MapDimensions.width * 32 - 1))
        y = max(0, min(self.y, _MapDimensions.height * 32 - 1))
        return FastPosition(x, y)
    
    def get_approx_distance(self, other: 'FastPosition') -> int:
        """Approximate distance (Chebyshev) to another position."""
        dx = abs(self.x - other.x)
        dy = abs(self.y - other.y)
        return max(dx, dy)  # Approximation: max(dx, dy)
    
    def get_distance(self, other: 'FastPosition') -> float:
        """Exact Euclidean distance to another position."""
        dx = self.x - other.x
        dy = self.y - other.y
        return math.sqrt(dx * dx + dy * dy)
    
    def get_length(self) -> float:
        """Magnitude of this vector from origin."""
        return math.sqrt(self.x * self.x + self.y * self.y)
    
    @classmethod
    def from_walk_position(cls, walk_pos: 'FastWalkPosition') -> 'FastPosition':
        """Convert from walk position (multiply by 8)."""
        return cls(walk_pos.x * 8, walk_pos.y * 8)
    
    @classmethod
    def from_tile_position(cls, tile_pos: 'FastTilePosition') -> 'FastPosition':
        """Convert from tile position (multiply by 32)."""
        return cls(tile_pos.x * 32, tile_pos.y * 32)
    
    def to_walk_position(self) -> 'FastWalkPosition':
        """Convert to walk position (divide by 8)."""
        return FastWalkPosition(self.x // 8, self.y // 8)
    
    def to_tile_position(self) -> 'FastTilePosition':
        """Convert to tile position (divide by 32)."""
        return FastTilePosition(self.x // 32, self.y // 32)
    
    def __lt__(self, other: 'FastPosition') -> bool:
        return (self.x, self.y) < (other.x, other.y)
    
    def __add__(self, other: 'FastPosition') -> 'FastPosition':
        return FastPosition(self.x + other.x, self.y + other.y)
    
    def __sub__(self, other: 'FastPosition') -> 'FastPosition':
        return FastPosition(self.x - other.x, self.y - other.y)
    
    def __truediv__(self, divisor: int) -> 'FastPosition':
        return FastPosition(self.x // divisor, self.y // divisor)
    
    def __neg__(self) -> 'FastPosition':
        return FastPosition(-self.x, -self.y)


@dataclass(frozen=True)
class FastWalkPosition:
    """Walk coordinate (4x4 per tile, 8x8 per pixel)."""
    x: int = 0
    y: int = 0
    
    @property
    def is_none(self) -> bool:
        """Check if this is the special None position."""
        return self.x == -1 and self.y == -1
    
    def is_valid(self) -> bool:
        """Check if position is within map bounds."""
        return (0 <= self.x < _MapDimensions.width * 4 and 
                0 <= self.y < _MapDimensions.height * 4)
    
    def make_valid(self) -> 'FastWalkPosition':
        """Clamp position to valid map bounds."""
        x = max(0, min(self.x, _MapDimensions.width * 4 - 1))
        y = max(0, min(self.y, _MapDimensions.height * 4 - 1))
        return FastWalkPosition(x, y)
    
    def get_approx_distance(self, other: 'FastWalkPosition') -> int:
        """Approximate distance to another position."""
        dx = abs(self.x - other.x)
        dy = abs(self.y - other.y)
        return max(dx, dy)
    
    @classmethod
    def from_pixel_position(cls, pixel_pos: FastPosition) -> 'FastWalkPosition':
        """Convert from pixel position (divide by 8)."""
        return cls(pixel_pos.x // 8, pixel_pos.y // 8)
    
    @classmethod
    def from_tile_position(cls, tile_pos: 'FastTilePosition') -> 'FastWalkPosition':
        """Convert from tile position (multiply by 4)."""
        return cls(tile_pos.x * 4, tile_pos.y * 4)
    
    def to_pixel_position(self) -> FastPosition:
        """Convert to pixel position (multiply by 8)."""
        return FastPosition(self.x * 8, self.y * 8)
    
    def to_tile_position(self) -> 'FastTilePosition':
        """Convert to tile position (divide by 4)."""
        return FastTilePosition(self.x // 4, self.y // 4)
    
    def __lt__(self, other: 'FastWalkPosition') -> bool:
        return (self.x, self.y) < (other.x, other.y)
    
    def __add__(self, other: 'FastWalkPosition') -> 'FastWalkPosition':
        return FastWalkPosition(self.x + other.x, self.y + other.y)
    
    def __sub__(self, other: 'FastWalkPosition') -> 'FastWalkPosition':
        return FastWalkPosition(self.x - other.x, self.y - other.y)
    
    def __truediv__(self, divisor: int) -> 'FastWalkPosition':
        return FastWalkPosition(self.x // divisor, self.y // divisor)


@dataclass(frozen=True)
class FastTilePosition:
    """Tile coordinate."""
    x: int = 0
    y: int = 0
    
    @property
    def is_none(self) -> bool:
        """Check if this is the special None position."""
        return self.x == -1 and self.y == -1
    
    def is_valid(self) -> bool:
        """Check if position is within map bounds."""
        return 0 <= self.x < _MapDimensions.width and 0 <= self.y < _MapDimensions.height
    
    def make_valid(self) -> 'FastTilePosition':
        """Clamp position to valid map bounds."""
        x = max(0, min(self.x, _MapDimensions.width - 1))
        y = max(0, min(self.y, _MapDimensions.height - 1))
        return FastTilePosition(x, y)
    
    def get_approx_distance(self, other: 'FastTilePosition') -> int:
        """Approximate distance to another tile."""
        dx = abs(self.x - other.x)
        dy = abs(self.y - other.y)
        return max(dx, dy)
    
    @classmethod
    def from_pixel_position(cls, pixel_pos: FastPosition) -> 'FastTilePosition':
        """Convert from pixel position (divide by 32)."""
        return cls(pixel_pos.x // 32, pixel_pos.y // 32)
    
    @classmethod
    def from_walk_position(cls, walk_pos: FastWalkPosition) -> 'FastTilePosition':
        """Convert from walk position (divide by 4)."""
        return cls(walk_pos.x // 4, walk_pos.y // 4)
    
    def to_pixel_position(self) -> FastPosition:
        """Convert to pixel position (multiply by 32)."""
        return FastPosition(self.x * 32, self.y * 32)
    
    def to_walk_position(self) -> FastWalkPosition:
        """Convert to walk position (multiply by 4)."""
        return FastWalkPosition(self.x * 4, self.y * 4)
    
    def __lt__(self, other: 'FastTilePosition') -> bool:
        return (self.x, self.y) < (other.x, other.y)
    
    def __add__(self, other: 'FastTilePosition') -> 'FastTilePosition':
        return FastTilePosition(self.x + other.x, self.y + other.y)
    
    def __sub__(self, other: 'FastTilePosition') -> 'FastTilePosition':
        return FastTilePosition(self.x - other.x, self.y - other.y)
    
    def __truediv__(self, divisor: int) -> 'FastTilePosition':
        return FastTilePosition(self.x // divisor, self.y // divisor)


# Special "None" values matching BWAPI semantics
FAST_POSITION_NONE = FastPosition(-1, -1)
FAST_WALK_POSITION_NONE = FastWalkPosition(-1, -1)
FAST_TILE_POSITION_NONE = FastTilePosition(-1, -1)
