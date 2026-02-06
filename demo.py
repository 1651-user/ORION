#!/usr/bin/env python3
"""
River Label Placement Demo

Demonstrates the river labeling algorithm on the provided ELBE river polygons.
Generates visual output showing optimal label placements.
"""

from pathlib import Path
import sys

from river_labeler import load_wkt_file, RiverLabeler, calculate_text_metrics
from visualizer import RiverVisualizer


def main():
    print("=" * 60)
    print("River Label Placement Algorithm Demo")
    print("=" * 60)
    
    # Paths
    script_dir = Path(__file__).parent
    wkt_file = script_dir / "river.wkt"
    output_dir = script_dir / "output"
    
    # Create output directory
    output_dir.mkdir(exist_ok=True)
    
    # Load river polygons
    print(f"\n📂 Loading river geometry from: {wkt_file}")
    if not wkt_file.exists():
        print(f"❌ Error: WKT file not found: {wkt_file}")
        sys.exit(1)
    
    polygons = load_wkt_file(str(wkt_file))
    print(f"✅ Loaded {len(polygons)} polygon(s)")
    
    # Configuration
    label_text = "ELBE"
    font_size = 12.0  # points
    padding = 5.0     # points
    
    print(f"\n📝 Label Configuration:")
    print(f"   Text: '{label_text}'")
    print(f"   Font size: {font_size} pt")
    print(f"   Padding: {padding} pt")
    
    # Calculate text metrics
    text_metrics = calculate_text_metrics(label_text, font_size)
    print(f"   Text dimensions: {text_metrics.width:.1f} × {text_metrics.height:.1f} pt")
    
    # Initialize labeler
    labeler = RiverLabeler(padding=padding, font_size=font_size)
    
    # Place labels in each polygon
    print("\n🔍 Finding Optimal Placements:")
    print("-" * 50)
    
    placements = labeler.place_labels_individually(polygons, label_text)
    
    for i, (polygon, placement) in enumerate(zip(polygons, placements)):
        bounds = polygon.bounds
        width = bounds[2] - bounds[0]
        height = bounds[3] - bounds[1]
        
        print(f"\n  Polygon {i + 1}:")
        print(f"    Bounds: ({bounds[0]:.0f}, {bounds[1]:.0f}) to ({bounds[2]:.0f}, {bounds[3]:.0f})")
        print(f"    Size: {width:.0f} × {height:.0f} pt")
        print(f"    Area: {polygon.area:.0f} sq pt")
        print(f"    📍 Label Position: ({placement.x:.1f}, {placement.y:.1f})")
        print(f"    🔄 Rotation: {placement.rotation:.1f}°")
        print(f"    📐 Available space: {placement.available_width:.1f} × {placement.available_height:.1f} pt")
        print(f"    ✓ Fits inside: {'Yes' if placement.fits_inside else 'No (fallback)'}")
    
    # Generate visualizations
    print("\n🎨 Generating Visualizations:")
    print("-" * 50)
    
    visualizer = RiverVisualizer()
    
    # SVG output
    svg_path = output_dir / "river_labels.svg"
    visualizer.generate_svg(
        polygons, placements, label_text,
        str(svg_path), font_size=font_size
    )
    print(f"  ✅ SVG saved: {svg_path}")
    
    # PNG output (combined view)
    png_path = output_dir / "river_labels.png"
    visualizer.generate_combined_view(
        polygons, placements, label_text,
        str(png_path), font_size=font_size, dpi=150
    )
    print(f"  ✅ PNG saved: {png_path}")
    
    # Individual polygon PNGs
    for i, (polygon, placement) in enumerate(zip(polygons, placements)):
        individual_path = output_dir / f"polygon_{i+1}.png"
        visualizer.generate_png(
            [polygon], [placement], label_text,
            str(individual_path), font_size=font_size, dpi=150
        )
        print(f"  ✅ Polygon {i+1} PNG saved: {individual_path}")
    
    print("\n" + "=" * 60)
    print("✨ Demo Complete!")
    print(f"   Output files are in: {output_dir}")
    print("=" * 60)
    
    return placements


if __name__ == "__main__":
    main()
