import { useEffect, useState } from 'react';
import { MapContainer, TileLayer, LayerGroup, LayersControl, GeoJSON, useMapEvents, } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { useData } from '@/context/DataContext';
import './MapViewer.css';

import DroneIndicator from '../map/DroneIndicator';



const MapViewer = () => {
  const { datasets, selectedFolder } = useData();
  const [data, setData] = useState<any | null>(null);
  const [tileMeta, setTileMeta] = useState<{ minZoom: number, maxZoom: number, bounds: [[number, number], [number, number]] } | null>(null);

  const currentDataset = datasets.find(d => d.name === selectedFolder);
  if (!currentDataset || !currentDataset.isCompleted) {
    return <div className="viewer-empty">Process the dataset to view the map.</div>;
  }

  const tileUrl = `/api/outputs/${currentDataset.name}_out/exports/${currentDataset.name}_map_tiles/{z}/{x}/{y}.png`;

  useEffect(() => {
    if (currentDataset) {
      const tileInfoUrl = `/api/outputs/${currentDataset.name}_out/exports/${currentDataset.name}_map_tiles/tile_info.json`;
      fetch(tileInfoUrl)
        .then(res => res.ok ? res.json() : null)
        .then(data => setTileMeta(data))
        .catch(() => setTileMeta(null));

      fetch(`/api/outputs/${currentDataset.name}_out/exports/detections.json`)
        .then(res => res.json())
        .then(json => {
          if (json.success) {
            console.log(json)
            setData(json);


          }
        })
        .catch(err => console.error("Detections not found:", err));
    }
  }, [currentDataset]);

  const getFeatureStyle = (feature: any) => {
    if (feature.properties.type === 'progress_ribbon') {
      return {
        color: feature.properties.color || '#3388ff',
        weight: 6,
        opacity: 0.7,
        lineJoin: 'round'
      };
    }
    return {
      color: '#ffcc00', // Yellow for markers
      weight: 3
    };
  };

  return (
    <div style={{ width: '100%', height: '100%', background: '#1a1a1a' }}>
      {/* --- PROGRESS DASHBOARD --- */}
      {data?.summary && (
        <div className="map-stats-overlay">
          <h3 className="stats-title">Work Progress</h3>
          <div className="stats-total">Total: {data.summary.total_meters.toLocaleString()}m</div>

          <div className="stats-list">
            {data.summary.states.map((s: any) => (
              <div key={s.name} className="stats-item">
                <div className="stats-labels">
                  <span className="state-name">{s.name}</span>
                  <span className="state-percent">{s.percent}%</span>
                </div>
                <div className="progress-bg">
                  {/* The color comes from your Python PROCESS_STATES mapping */}
                  <div
                    className="progress-fill"
                    style={{
                      width: `${s.percent}%`,
                      backgroundColor: data.trace.features.find((f: any) => f.properties.state === s.name)?.properties.color || '#fff'
                    }}
                  />
                </div>
                <div className="state-meters">{s.meters.toLocaleString()}m</div>
              </div>
            ))}
          </div>
        </div>
      )}
      <MapContainer
        center={[0, 0]}
        zoom={18}
        style={{ width: '100%', height: '100%', backgroundColor: 'transparent' }}
        minZoom={10}
        maxZoom={24}
      >
        <ZoomLogger />
        <LayersControl position="topright">

          {/* --- BASE MAPS (Radio Buttons) --- */}

          <LayersControl.BaseLayer checked name="Google Satellite">
            <TileLayer
              url="https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}"
              attribution='&copy; Google'
              maxZoom={22}
              maxNativeZoom={22}
            />
          </LayersControl.BaseLayer>

          <LayersControl.BaseLayer name="Esri World Imagery">
            <TileLayer
              url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
              attribution='&copy; <a href="https://www.esri.com/">Esri</a>, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EBP, and the GIS User Community'
              maxZoom={22}
              maxNativeZoom={22}
            />
          </LayersControl.BaseLayer>

          <LayersControl.BaseLayer name="OpenStreetMap">
            <TileLayer
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              attribution='&copy; OpenStreetMap contributors'
              maxZoom={22}
              maxNativeZoom={19} // OSM natively stops at 19
            />
          </LayersControl.BaseLayer>

          {/* --- OVERLAYS (Checkboxes) --- */}

          <LayersControl.Overlay checked name="Drone Survey (Orthomosaic)">
            {tileMeta ? (
              <TileLayer
                key={`${currentDataset.name}-${tileMeta.minZoom}`}
                url={tileUrl}
                tms={false}
                opacity={1.0}
                bounds={tileMeta?.bounds}
                minNativeZoom={tileMeta?.minZoom || 14}
                maxNativeZoom={tileMeta?.maxZoom || 22}
                // minNativeZoom={14}
                // maxNativeZoom={22}
                minZoom={14}
                maxZoom={24}
                keepBuffer={2}
                updateWhenZooming={false}
                errorTileUrl="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
              />) : (
              // Optional: A Layer that does nothing while loading to prevent crashes
              <LayerGroup />
            )}
          </LayersControl.Overlay>

          {/* --- THE PIPELINE TRACE LAYER --- */}
          {data?.trace && (
            <LayersControl.Overlay checked name="Pipeline Progress">
              <GeoJSON
                key={JSON.stringify(data.trace)}
                data={data.trace}
                style={getFeatureStyle}
                onEachFeature={(feature: any, layer: any) => {
                  if (feature.properties && feature.properties.name) {
                    layer.bindTooltip(feature.properties.name, { sticky: true });
                  }
                }}
              />
            </LayersControl.Overlay>
          )}

        </LayersControl>

        <DroneIndicator datasetName={currentDataset.name} />
      </MapContainer>
    </div>
  );
};




function ZoomLogger() {
  const map = useMapEvents({
    zoomend: () => {
      console.log("Current Zoom Level:", map.getZoom());
    },
  });
  return null;
}

export default MapViewer;