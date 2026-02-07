# ORION
# River Label Placement Algorithm

An intelligent algorithm for automatically placing text labels inside river polygon geometries, ensuring optimal positioning, rotation, and readability.

## Overview

ORION solves the cartographic challenge of labeling river features on maps. Given irregular polygon shapes representing rivers, the algorithm finds the optimal position to place text labels so they:
- Fit inside the polygon boundaries
- Follow the river's natural flow direction
- Maintain proper spacing from edges
- Remain readable

## Features

- **Pole of Inaccessibility Algorithm** - Finds the visual center point furthest from all edges
- **Automatic Rotation** - Labels rotate to follow river flow direction
- **Padding Support** - Configurable spacing from polygon edges
- **Multiple Output Formats** - Generates both SVG and PNG visualizations
- **Batch Processing** - Handle multiple polygon segments efficiently

## Installation

```bash
# Clone the repository
git clone https://github.com/1651-user/ORION.git
cd ORION

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Requirements

- Python 3.8+
- Shapely 2.0+
- Matplotlib 3.7+
- Pillow 10.0+
- NumPy 1.24+
- svgwrite 1.4+

## Usage

### Quick Demo

```bash
python demo.py
```

This will process the sample ELBE river data and generate visualizations in the `output/` folder.

### Using the API

```python
from river_labeler import RiverLabeler, load_wkt_file

# Load river polygons from WKT file
polygons = load_wkt_file("river.wkt")

# Initialize labeler
labeler = RiverLabeler(padding=5.0, font_size=12.0)

# Get optimal label placements
placements = labeler.place_labels_individually(polygons, "ELBE")

for placement in placements:
    print(f"Position: ({placement.x}, {placement.y})")
    print(f"Rotation: {placement.rotation}°")
    print(f"Fits inside: {placement.fits_inside}")
```

### Generating Visualizations

```python
from visualizer import RiverVisualizer

visualizer = RiverVisualizer()

# Generate SVG
visualizer.generate_svg(polygons, placements, "ELBE", "output.svg")

# Generate PNG
visualizer.generate_png(polygons, placements, "ELBE", "output.png")
```

## Project Structure

```
ORION/
├── river_labeler.py    # Core labeling algorithm
├── visualizer.py       # SVG/PNG visualization
├── demo.py             # Demonstration script
├── river.wkt           # Sample ELBE river data
├── requirements.txt    # Python dependencies
└── output/             # Generated visualizations
```

## Algorithm

The algorithm combines three geometric techniques:

1. **Pole of Inaccessibility (PoI)** - Iteratively finds the point inside the polygon with maximum distance from all edges

2. **Oriented Bounding Box (OBB)** - Calculates the minimum-area rotated bounding rectangle to determine flow direction

3. **Negative Buffer** - Applies inward padding to ensure labels don't touch polygon edges

## Sample Output

The algorithm processes the ELBE river (3 polygon segments) and produces:

| Polygon | Position | Rotation | Status |
|---------|----------|----------|--------|
| 1 | (11761, 24546) | 86.3° | ✓ Fits |
| 2 | (11331, 25199) | -7.9° | ✓ Fits |
| 3 | (11757, 24986) | -65.2° | ✓ Fits |

## Team

- **Sravya Isukapatla** - Algorithm Developer
- **Rahul Patra** - Visualization Developer
- **Shubham Kumar** - Integration & Testing Lead

## License

This project was developed for the hackathon competition.
