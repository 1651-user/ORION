"""
River Label Visualization Module

Generates SVG and PNG visualizations of river polygons with placed labels.
"""

import math
from pathlib import Path
from typing import List, Tuple, Optional
import svgwrite
from shapely.geometry import Polygon
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.transforms import Affine2D
import numpy as np

from river_labeler import LabelPlacement, TextMetrics, calculate_text_metrics


class RiverVisualizer:
    """
    Visualize river polygons with placed labels.
    Supports SVG and PNG output formats.
    """
    
    # Color scheme
    RIVER_FILL = "#4A90D9"  # Blue
    RIVER_STROKE = "#2E5A8C"  # Darker blue
    LABEL_COLOR = "#1A1A2E"  # Dark text
    BACKGROUND = "#F5F5F5"  # Light gray
    PADDING_INDICATOR = "#FF6B6B"  # Red for padding visualization
    
    def __init__(self, margin: float = 50):
        self.margin = margin
    
    def _get_bounds(self, polygons: List[Polygon]) -> Tuple[float, float, float, float]:
        """Get combined bounding box for all polygons."""
        all_bounds = [p.bounds for p in polygons]
        minx = min(b[0] for b in all_bounds)
        miny = min(b[1] for b in all_bounds)
        maxx = max(b[2] for b in all_bounds)
        maxy = max(b[3] for b in all_bounds)
        return minx, miny, maxx, maxy
    
    def _transform_coords(
        self, 
        x: float, 
        y: float, 
        bounds: Tuple[float, float, float, float],
        canvas_width: float,
        canvas_height: float
    ) -> Tuple[float, float]:
        """Transform geometry coordinates to canvas coordinates."""
        minx, miny, maxx, maxy = bounds
        geom_width = maxx - minx
        geom_height = maxy - miny
        
        # Scale to fit canvas with margin
        available_width = canvas_width - 2 * self.margin
        available_height = canvas_height - 2 * self.margin
        
        scale = min(available_width / geom_width, available_height / geom_height)
        
        # Center the geometry
        offset_x = (canvas_width - geom_width * scale) / 2
        offset_y = (canvas_height - geom_height * scale) / 2
        
        # Transform (flip Y axis for SVG coordinate system)
        tx = (x - minx) * scale + offset_x
        ty = canvas_height - ((y - miny) * scale + offset_y)
        
        return tx, ty
    
    def _polygon_to_svg_path(
        self,
        polygon: Polygon,
        bounds: Tuple[float, float, float, float],
        canvas_width: float,
        canvas_height: float
    ) -> str:
        """Convert a Shapely polygon to an SVG path string."""
        coords = list(polygon.exterior.coords)
        path_parts = []
        
        for i, (x, y) in enumerate(coords):
            tx, ty = self._transform_coords(x, y, bounds, canvas_width, canvas_height)
            if i == 0:
                path_parts.append(f"M {tx:.2f} {ty:.2f}")
            else:
                path_parts.append(f"L {tx:.2f} {ty:.2f}")
        
        path_parts.append("Z")
        return " ".join(path_parts)
    
    def generate_svg(
        self,
        polygons: List[Polygon],
        placements: List[LabelPlacement],
        label_text: str,
        output_path: str,
        font_size: float = 12.0,
        canvas_width: float = 800,
        canvas_height: float = 600
    ) -> str:
        """
        Generate an SVG visualization.
        
        Args:
            polygons: List of river polygon geometries
            placements: List of label placement results
            label_text: The label text to display
            output_path: Path to save the SVG file
            font_size: Font size in points
            canvas_width: SVG canvas width
            canvas_height: SVG canvas height
            
        Returns:
            Path to the saved SVG file
        """
        bounds = self._get_bounds(polygons)
        minx, miny, maxx, maxy = bounds
        geom_width = maxx - minx
        geom_height = maxy - miny
        
        # Adjust canvas aspect ratio to match geometry
        aspect = geom_width / geom_height if geom_height > 0 else 1
        if aspect > canvas_width / canvas_height:
            canvas_height = canvas_width / aspect
        else:
            canvas_width = canvas_height * aspect
        
        # Create SVG
        dwg = svgwrite.Drawing(
            output_path, 
            size=(f"{canvas_width}px", f"{canvas_height}px"),
            viewBox=f"0 0 {canvas_width} {canvas_height}"
        )
        
        # Add background
        dwg.add(dwg.rect(
            insert=(0, 0),
            size=(canvas_width, canvas_height),
            fill=self.BACKGROUND
        ))
        
        # Add title
        dwg.add(dwg.text(
            f"River: {label_text}",
            insert=(canvas_width / 2, 25),
            text_anchor="middle",
            font_size="16px",
            font_family="Arial, sans-serif",
            font_weight="bold",
            fill="#333"
        ))
        
        # Calculate scale for font size adjustment
        available_width = canvas_width - 2 * self.margin
        scale = available_width / geom_width
        scaled_font_size = font_size * scale * 1.5  # Scale up for visibility
        
        # Draw polygons
        for i, polygon in enumerate(polygons):
            path_d = self._polygon_to_svg_path(polygon, bounds, canvas_width, canvas_height)
            
            # Polygon fill
            dwg.add(dwg.path(
                d=path_d,
                fill=self.RIVER_FILL,
                stroke=self.RIVER_STROKE,
                stroke_width=2,
                fill_opacity=0.8
            ))
        
        # Draw labels
        for placement in placements:
            # Transform label position
            lx, ly = self._transform_coords(
                placement.x, placement.y, 
                bounds, canvas_width, canvas_height
            )
            
            # Create rotated text group
            # Note: SVG rotation is clockwise, and we've flipped Y, so adjust angle
            svg_rotation = -placement.rotation
            
            text_elem = dwg.text(
                label_text,
                insert=(lx, ly),
                text_anchor="middle",
                dominant_baseline="central",
                font_size=f"{scaled_font_size}px",
                font_family="Arial, sans-serif",
                font_weight="bold",
                fill=self.LABEL_COLOR,
                transform=f"rotate({svg_rotation} {lx} {ly})"
            )
            
            # Add text shadow for better visibility
            shadow = dwg.text(
                label_text,
                insert=(lx + 1, ly + 1),
                text_anchor="middle",
                dominant_baseline="central",
                font_size=f"{scaled_font_size}px",
                font_family="Arial, sans-serif",
                font_weight="bold",
                fill="white",
                fill_opacity=0.7,
                transform=f"rotate({svg_rotation} {lx + 1} {ly + 1})"
            )
            dwg.add(shadow)
            dwg.add(text_elem)
            
            # Add placement indicator (small circle at center)
            dwg.add(dwg.circle(
                center=(lx, ly),
                r=3,
                fill="#FF4444",
                fill_opacity=0.5
            ))
        
        # Add legend
        legend_y = canvas_height - 30
        dwg.add(dwg.text(
            f"Label positions shown with red dots • Font size: {font_size}pt",
            insert=(canvas_width / 2, legend_y),
            text_anchor="middle",
            font_size="10px",
            font_family="Arial, sans-serif",
            fill="#666"
        ))
        
        dwg.save()
        return output_path
    
    def generate_png(
        self,
        polygons: List[Polygon],
        placements: List[LabelPlacement],
        label_text: str,
        output_path: str,
        font_size: float = 12.0,
        dpi: int = 150
    ) -> str:
        """
        Generate a PNG visualization using matplotlib.
        """
        bounds = self._get_bounds(polygons)
        minx, miny, maxx, maxy = bounds
        geom_width = maxx - minx
        geom_height = maxy - miny
        
        # Calculate figure size (in inches)
        aspect = geom_width / geom_height if geom_height > 0 else 1
        fig_width = 10
        fig_height = fig_width / aspect
        
        fig, ax = plt.subplots(figsize=(fig_width, fig_height), dpi=dpi)
        ax.set_facecolor(self.BACKGROUND)
        
        # Draw polygons
        for i, polygon in enumerate(polygons):
            x, y = polygon.exterior.xy
            ax.fill(x, y, color=self.RIVER_FILL, alpha=0.8, edgecolor=self.RIVER_STROKE, linewidth=2)
        
        # Draw labels
        for placement in placements:
            # Add text with rotation
            ax.text(
                placement.x, placement.y, 
                label_text,
                fontsize=font_size * 2,  # Scale up for visibility
                fontweight='bold',
                color=self.LABEL_COLOR,
                ha='center', va='center',
                rotation=placement.rotation,
                rotation_mode='anchor',
                bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.7, edgecolor='none')
            )
            
            # Add placement indicator
            ax.plot(placement.x, placement.y, 'ro', markersize=5, alpha=0.7)
        
        ax.set_aspect('equal')
        ax.set_xlim(minx - self.margin, maxx + self.margin)
        ax.set_ylim(miny - self.margin, maxy + self.margin)
        ax.set_title(f"River: {label_text}", fontsize=14, fontweight='bold')
        ax.axis('off')
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=dpi, bbox_inches='tight', facecolor=self.BACKGROUND)
        plt.close()
        
        return output_path
    
    def generate_combined_view(
        self,
        polygons: List[Polygon],
        placements: List[LabelPlacement],
        label_text: str,
        output_path: str,
        font_size: float = 12.0,
        dpi: int = 150
    ) -> str:
        """
        Generate a combined view showing all polygons in one image.
        """
        bounds = self._get_bounds(polygons)
        minx, miny, maxx, maxy = bounds
        geom_width = maxx - minx
        geom_height = maxy - miny
        
        # Calculate figure size
        aspect = geom_width / geom_height if geom_height > 0 else 1
        fig_width = 12
        fig_height = max(8, fig_width / aspect)
        
        fig, ax = plt.subplots(figsize=(fig_width, fig_height), dpi=dpi)
        ax.set_facecolor('#E8F4F8')
        
        # Color palette for different polygons
        colors = ['#4A90D9', '#5DA5DA', '#60B5CC', '#4ECDC4']
        
        # Draw all polygons
        for i, polygon in enumerate(polygons):
            x, y = polygon.exterior.xy
            color = colors[i % len(colors)]
            ax.fill(x, y, color=color, alpha=0.7, edgecolor='#2E5A8C', linewidth=1.5, 
                   label=f'Polygon {i+1}')
        
        # Draw labels
        for i, placement in enumerate(placements):
            ax.text(
                placement.x, placement.y,
                label_text,
                fontsize=font_size * 1.8,
                fontweight='bold',
                color='#1A1A2E',
                ha='center', va='center',
                rotation=placement.rotation,
                rotation_mode='anchor',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.85, edgecolor='#666')
            )
            
            # Mark center point
            ax.plot(placement.x, placement.y, 'r.', markersize=8)
            
            # Add annotation with placement info
            info_text = f"({placement.x:.0f}, {placement.y:.0f})\nAngle: {placement.rotation:.1f}°"
            ax.annotate(
                info_text,
                xy=(placement.x, placement.y),
                xytext=(15, -25),
                textcoords='offset points',
                fontsize=7,
                color='#444',
                bbox=dict(boxstyle='round,pad=0.2', facecolor='#FFF9C4', alpha=0.9)
            )
        
        ax.set_aspect('equal')
        margin = max(geom_width, geom_height) * 0.05
        ax.set_xlim(minx - margin, maxx + margin)
        ax.set_ylim(miny - margin, maxy + margin)
        
        ax.set_title(f"River Label Placement: '{label_text}'", fontsize=16, fontweight='bold', pad=20)
        ax.legend(loc='upper right', fontsize=9)
        
        # Add grid
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.set_xlabel('X (points)', fontsize=10)
        ax.set_ylabel('Y (points)', fontsize=10)
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=dpi, bbox_inches='tight', facecolor='white')
        plt.close()
        
        return output_path


if __name__ == "__main__":
    # Quick test visualization
    from river_labeler import load_wkt_file, RiverLabeler
    from pathlib import Path
    
    wkt_file = Path(__file__).parent / "river.wkt"
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    
    if wkt_file.exists():
        polygons = load_wkt_file(str(wkt_file))
        print(f"Loaded {len(polygons)} polygons")
        
        labeler = RiverLabeler(padding=5.0, font_size=12.0)
        placements = labeler.place_labels_individually(polygons, "ELBE")
        
        visualizer = RiverVisualizer()
        
        # Generate outputs
        svg_path = visualizer.generate_svg(
            polygons, placements, "ELBE",
            str(output_dir / "river_labels.svg")
        )
        print(f"Generated: {svg_path}")
        
        png_path = visualizer.generate_combined_view(
            polygons, placements, "ELBE",
            str(output_dir / "river_labels.png")
        )
        print(f"Generated: {png_path}")
