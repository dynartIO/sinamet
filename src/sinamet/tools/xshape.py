def to_folium_mpolygon_locations(mpolygon):
    if mpolygon.geom_type == 'MultiPolygon':
        geoshape = [[(k[1], k[0]) for polygon in mpolygon.geoms for k in polygon.exterior.coords]]
    else:
        geoshape = [[(k[1], k[0]) for k in mpolygon.exterior.coords]]
    return geoshape