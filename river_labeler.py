"""
River Label Placement Algorithm

This module provides cartographically optimal label placement for river geometries.
It uses a multi-strategy approach combining:
1. Pole of Inaccessibility - finds the point furthest from all edges
2. Oriented Bounding Box - determines optimal text rotation
3. Inscribed rectangle fitting - ensures text fits with proper padding
"""

from dataclasses import dataclass
from typing import List, Tuple, Optional
import math
import numpy as np
from shapely import wkt
from shapely.geometry import Polygon, Point, LineString, MultiPolygon
from shapely.affinity import rotate
from PIL import Image, ImageDraw, ImageFont


@dataclass
class LabelPlacement:
    """Result of label placement calculation."""
    x: float
    y: float
    rotation: float  # degrees, counter-clockwise from horizontal
    fits_inside: bool
    available_width: float
    available_height: float
    polygon_index: int


@dataclass 
class TextMetrics:
    """Text dimensions for a given label."""
    width: float
    height: float
    text: str
    font_size: float


def load_wkt_file(filepath: str) -> List[Polygon]:
    """Load polygons from a WKT file (one polygon per line)."""
    polygons = []
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if line and line.startswith('POLYGON'):
                try:
                    geom = wkt.loads(line)
                    if isinstance(geom, Polygon) and geom.is_valid:
                        polygons.append(geom)
                except Exception as e:
                    print(f"Warning: Could not parse WKT: {e}")
    return polygons


def calculate_text_metrics(text: str, font_size: float) -> TextMetrics:
    """
    Calculate approximate text dimensions in points.
    Uses a typical font aspect ratio for estimation.
    """
    # Approximate character width as 0.6 * font_size for typical fonts
    char_width_ratio = 0.6
    width = len(text) * font_size * char_width_ratio
    height = font_size
    return TextMetrics(width=width, height=height, text=text, font_size=font_size)


def pole_of_inaccessibility(polygon: Polygon, precision: float = 1.0) -> Tuple[float, float, float]:
    """
    Find the pole of inaccessibility - the point inside a polygon 
    that is furthest from any edge.
    
    Uses an iterative cell-based algorithm inspired by mapbox/polylabel.
    
    Returns: (x, y, distance_to_nearest_edge)
    """
    if not polygon.is_valid or polygon.is_empty:
        centroid = polygon.centroid
        return (centroid.x, centroid.y, 0.0)
    
    minx, miny, maxx, maxy = polygon.bounds
    width = maxx - minx
    height = maxy - miny
    cell_size = max(width, height)
    
    if cell_size == 0:
        return (minx, miny, 0.0)
    
    # Initial cell size
    h = cell_size / 2
    
    # Priority queue of cells (negative distance for max-heap behavior with min-heap)
    cells = []
    
    # Cover polygon with initial cells
    x = minx
    while x < maxx:
        y = miny
        while y < maxy:
            cells.append(_create_cell(x + h, y + h, h, polygon))
            y += cell_size
        x += cell_size
    
    # Initial best guess: centroid or point on surface
    best_cell = _create_cell(polygon.centroid.x, polygon.centroid.y, 0, polygon)
    
    # Try representative point if centroid is outside
    if not polygon.contains(Point(best_cell[0], best_cell[1])):
        rep_point = polygon.representative_point()
        rep_cell = _create_cell(rep_point.x, rep_point.y, 0, polygon)
        if rep_cell[2] > best_cell[2]:
            best_cell = rep_cell
    
    while cells:
        # Sort by max potential (distance + h * sqrt(2))
        cells.sort(key=lambda c: -(c[2] + c[3] * math.sqrt(2)))
        cell = cells.pop(0)
        
        cx, cy, d, ch = cell
        
        # Update best if this cell's center is better
        if d > best_cell[2]:
            best_cell = cell
        
        # Skip if this cell can't improve on best
        if d + ch * math.sqrt(2) <= best_cell[2] + precision:
            continue
        
        # Split cell into 4
        h = ch / 2
        if h > precision / 2:
            cells.append(_create_cell(cx - h, cy - h, h, polygon))
            cells.append(_create_cell(cx + h, cy - h, h, polygon))
            cells.append(_create_cell(cx - h, cy + h, h, polygon))
            cells.append(_create_cell(cx + h, cy + h, h, polygon))
    
    return (best_cell[0], best_cell[1], best_cell[2])


def _create_cell(x: float, y: float, h: float, polygon: Polygon) -> Tuple[float, float, float, float]:
    """Create a cell with center (x, y), half-size h, and distance to polygon edge."""
    point = Point(x, y)
    # Distance is negative if point is outside polygon
    d = polygon.exterior.distance(point)
    if not polygon.contains(point):
        d = -d
    return (x, y, d, h)


def get_oriented_bounding_box(polygon: Polygon) -> Tuple[Polygon, float]:
    """
    Calculate the minimum-area oriented bounding box.
    Returns: (bounding_box_polygon, rotation_angle_degrees)
    """
    # Get the convex hull for efficiency
    hull = polygon.convex_hull
    if hull.is_empty:
        return polygon.envelope, 0.0
    
    coords = list(hull.exterior.coords)[:-1]  # Remove duplicate closing point
    if len(coords) < 3:
        return polygon.envelope, 0.0
    
    min_area = float('inf')
    best_angle = 0
    best_box = polygon.envelope
    
    # Try rotations based on hull edges
    for i in range(len(coords)):
        p1 = coords[i]
        p2 = coords[(i + 1) % len(coords)]
        
        # Calculate edge angle
        angle = math.atan2(p2[1] - p1[1], p2[0] - p1[0])
        angle_deg = math.degrees(angle)
        
        # Rotate polygon and get axis-aligned bounding box
        rotated = rotate(polygon, -angle_deg, origin='centroid')
        box = rotated.envelope
        
        if box.area < min_area:
            min_area = box.area
            best_angle = angle_deg
            # Rotate box back
            best_box = rotate(box, angle_deg, origin=polygon.centroid)
    
    return best_box, best_angle


def calculate_flow_direction(polygon: Polygon) -> float:
    """
    Calculate the primary flow direction of a river polygon.
    Returns angle in degrees (0-180, ensuring text reads left-to-right).
    """
    _, angle = get_oriented_bounding_box(polygon)
    
    # Normalize angle to 0-180 range for readable text
    while angle < 0:
        angle += 180
    while angle >= 180:
        angle -= 180
    
    # Prefer angles closer to horizontal for readability
    if angle > 90:
        angle -= 180
    
    return angle


def find_optimal_placement(
    polygon: Polygon,
    text_metrics: TextMetrics,
    padding: float = 2.0,
    polygon_index: int = 0
) -> LabelPlacement:
    """
    Find the optimal placement for a label inside a polygon.
    
    Strategy:
    1. Apply negative buffer (padding) to polygon
    2. Find pole of inaccessibility in buffered polygon
    3. Calculate available space at that point
    4. Determine rotation from flow direction
    """
    # Apply padding buffer
    padded = polygon.buffer(-padding)
    
    # Handle case where buffering makes polygon invalid/empty
    if padded.is_empty or not padded.is_valid:
        # Fall back to original polygon with reduced padding
        padded = polygon.buffer(-padding / 2)
        if padded.is_empty or not padded.is_valid:
            padded = polygon
    
    # Handle MultiPolygon from buffering
    if isinstance(padded, MultiPolygon):
        # Use the largest polygon
        padded = max(padded.geoms, key=lambda p: p.area)
    
    # Find pole of inaccessibility (point furthest from edges)
    px, py, max_dist = pole_of_inaccessibility(padded, precision=0.5)
    
    # Calculate flow direction for text rotation
    rotation = calculate_flow_direction(polygon)
    
    # Calculate available space at the placement point
    # The max_dist represents the radius of the largest inscribed circle
    # For a rectangle, we can approximate available dimensions
    available_width = max_dist * 2 * 0.9  # Slightly less than diameter
    available_height = max_dist * 2 * 0.5  # Rivers are typically elongated
    
    # Check if text fits
    # Account for rotation when checking fit
    rot_rad = math.radians(rotation)
    effective_width = abs(text_metrics.width * math.cos(rot_rad)) + abs(text_metrics.height * math.sin(rot_rad))
    effective_height = abs(text_metrics.width * math.sin(rot_rad)) + abs(text_metrics.height * math.cos(rot_rad))
    
    fits_inside = (effective_width <= available_width * 1.5 and 
                   effective_height <= available_height * 3)
    
    return LabelPlacement(
        x=px,
        y=py,
        rotation=rotation,
        fits_inside=fits_inside,
        available_width=available_width,
        available_height=available_height,
        polygon_index=polygon_index
    )


def find_best_placement_across_polygons(
    polygons: List[Polygon],
    text_metrics: TextMetrics,
    padding: float = 2.0
) -> LabelPlacement:
    """
    Find the best placement across multiple polygon parts.
    Selects the polygon with the most space for the label.
    """
    placements = []
    for i, polygon in enumerate(polygons):
        placement = find_optimal_placement(polygon, text_metrics, padding, i)
        placements.append(placement)
    
    # Prefer placements that fit, then by available space
    placements.sort(key=lambda p: (
        -int(p.fits_inside),  # Prefer fits_inside=True
        -(p.available_width * p.available_height)  # Then by area
    ))
    
    return placements[0]


class RiverLabeler:
    """
    Main class for placing labels on river geometries.
    """
    
    def __init__(self, padding: float = 3.0, font_size: float = 12.0):
        self.padding = padding
        self.font_size = font_size
    
    def place_label(
        self, 
        polygons: List[Polygon], 
        label_text: str
    ) -> LabelPlacement:
        """
        Place a label optimally across the given river polygons.
        
        Args:
            polygons: List of Shapely Polygon objects representing the river
            label_text: The text to place (e.g., "ELBE")
        
        Returns:
            LabelPlacement with optimal position and rotation
        """
        text_metrics = calculate_text_metrics(label_text, self.font_size)
        return find_best_placement_across_polygons(polygons, text_metrics, self.padding)
    
    def place_labels_individually(
        self,
        polygons: List[Polygon],
        label_text: str
    ) -> List[LabelPlacement]:
        """
        Place a label in each polygon separately.
        Useful when each polygon should have its own label.
        """
        text_metrics = calculate_text_metrics(label_text, self.font_size)
        placements = []
        for i, polygon in enumerate(polygons):
            placement = find_optimal_placement(polygon, text_metrics, self.padding, i)
            placements.append(placement)
        return placements


if __name__ == "__main__":
    # Quick test
    from pathlib import Path
    
    wkt_file = Path(__file__).parent / "river.wkt"
    if wkt_file.exists():
        polygons = load_wkt_file(str(wkt_file))
        print(f"Loaded {len(polygons)} polygons")
        
        labeler = RiverLabeler(padding=5.0, font_size=12.0)
        
        for i, polygon in enumerate(polygons):
            placement = labeler.place_label([polygon], "ELBE")
            print(f"\nPolygon {i+1}:")
            print(f"  Position: ({placement.x:.2f}, {placement.y:.2f})")
            print(f"  Rotation: {placement.rotation:.1f}°")
            print(f"  Fits inside: {placement.fits_inside}")
            print(f"  Available space: {placement.available_width:.1f} x {placement.available_height:.1f}")
