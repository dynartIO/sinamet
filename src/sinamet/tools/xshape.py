import pyproj
from shapely.ops import transform

def reproject(geometry, from_epsg: str | int, to_epsg: str | int):
    myproj = pyproj.Transformer.from_proj(
        pyproj.Proj(f'EPSG:{from_epsg}'),
        pyproj.Proj(f'EPSG:{to_epsg}'),
        always_xy=True)
    myprop = transform(myproj.transform, geometry)
    return myprop


def to_folium_mpolygon_locations(mpolygon):
    if mpolygon.geom_type == 'MultiPolygon':
        geoshape = [[(k[1], k[0]) for polygon in mpolygon.geoms for k in polygon.exterior.coords]]
    else:
        geoshape = [[(k[1], k[0]) for k in mpolygon.exterior.coords]]
    return geoshape