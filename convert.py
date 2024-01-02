""" Script to convert shapes on a PNG into RDS GeoFencing polygons using JSON format """

from functools import partial
import json
import numpy as np
import cv2
import pyproj
import utm
from shapely.geometry import Polygon
from shapely import geometry
from shapely import affinity
from shapely.ops import transform

# JSON structure to be generated
json_root = []

# Settings
images = [
    #{'file': 'images/rocket.png', 'desc': 'Rocket', 'scale': 1,
    #    'lat': 47.554703108406244, 'lon': 9.086087020816901},
    #{'file': 'images/fireworks-clip-art-new-years-firework-big-bw.png', 'desc': 'Firework',
    #    'scale': 10, 'lat': 47.554703108406244, 'lon': 9.086087020816901}
    #{'file': 'images/1280px-Stadler_Rail_logotype.svg.png', 'desc': 'Stadler',
    #    'scale': 40, 'lat': 52.38330030263479, 'lon': 12.819399185363995},
    #{'file': 'images/happy_new_year_2024.png', 'desc': 'Happy New Year 2024',
    #    'scale': 40, 'lat': 34.04928845536877, 'lon': -117.4095019119793}
    {'file': 'images/flirt_front.png', 'desc': 'FLIRT',
        'scale': 40, 'lat': 51.5053512759227, 'lon': -0.2102589290821343}
        
]

# Iterate through all given images
for image in images:

    # Load image and convert to binary black and white
    img = cv2.imread(image['file'], cv2.IMREAD_GRAYSCALE)
    _, img = cv2.threshold(img, 120, 255, cv2.THRESH_BINARY)
    cv2.flip(img, 0, img)

    # Find contours using OpenCV and convert to Shapely polygon
    contours = map(np.squeeze, cv2.findContours(
        img, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)[0][:-1])
    polygons = map(Polygon, contours)

    # Calculate reference point in UTM coordinate system based on WGS84 projection
    lat = image['lat']
    lon = image['lon']
    [utm_east, utm_north, zone1, zone2] = utm.from_latlon(lat, lon)
    wgs84_to_utm_ = partial(
        pyproj.transform,
        pyproj.Proj(proj='longlat', datum='WGS84',
                    no_defs=True, ellps='WGS84'),
        pyproj.Proj(proj='utm', zone=zone1, ellps='WGS84', preserve_units=False))

    utm_to_wgs84 = partial(
        pyproj.transform,
        pyproj.Proj(proj='utm', zone=zone1,
                    ellps='WGS84', preserve_units=False),
        pyproj.Proj(proj='longlat', datum='WGS84', no_defs=True, ellps='WGS84'))
    utm_reference_t = transform(wgs84_to_utm_, geometry.Point(lon, lat))

    # Convert every Shapely polygon into a Stadler GeoFencing geoshape JSON object
    num_polygons = 0
    for polygon in polygons:

        # Simplify polygon
        polygon = polygon.simplify(2.0, preserve_topology=False)

        # Place polygon with Shapely coordinate system into UTM coordinate system
        polygon_scaled = affinity.scale(
            polygon, xfact=image['scale'], yfact=image['scale'], origin=geometry.Point(0, 0))
        polygon_utm = affinity.translate(
            polygon_scaled, xoff=utm_reference_t.x, yoff=utm_reference_t.y)

        # Convert to WGS84
        polygon_wgs84 = transform(utm_to_wgs84, polygon_utm)

        # Prepare JSON polygon object
        desc = image['desc']
        j_data = {}
        j_data["name"] = {}
        j_data["name"]["value"] = f'{desc} {num_polygons:02}'
        j_data["geoShape"] = {}
        j_data["geoShape"]["type"] = "polygon"
        j_data["geoShape"]["fencePoints"] = []

        # Attach all WGS84 points to JSON
        points = []
        points.extend(polygon_wgs84.exterior.coords[:-1])
        for p in points:
            fencePoint = {}
            fencePoint["lat"] = {}
            fencePoint["lat"]["NormValue"] = p[1]
            fencePoint["lat"]["NormUnit"] = "°"
            fencePoint["latDirection"] = "NORTH"
            fencePoint["long"] = {}
            fencePoint["long"]["NormValue"] = p[0]
            fencePoint["long"]["NormUnit"] = "°"
            fencePoint["longDirection"] = "EAST"
            j_data["geoShape"]["fencePoints"].append(fencePoint)

        # Add to JSON root
        json_root.append(j_data)

        # Increase polygon counter
        num_polygons = num_polygons + 1

# Write JSON file
with open('geo-area.json', 'w', encoding='utf-8') as f:
    json.dump(json_root, f, ensure_ascii=False, indent=4)
