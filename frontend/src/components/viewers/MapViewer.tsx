import React, { useEffect, useState } from 'react';
import { MapContainer, TileLayer, useMap, LayersControl, useMapEvents, Marker, Tooltip } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import { useData } from '@/context/DataContext';



const MapViewer = () => {
  const { datasets, selectedFolder } = useData();
  const currentDataset = datasets.find(d => d.name === selectedFolder);

  if (!currentDataset || !currentDataset.isCompleted) {
    return <div className="viewer-empty">Process the dataset to view the map.</div>;
  }

  const tileUrl = `/api/outputs/${currentDataset.name}_out/tiles/{z}/{x}/{y}.png`;

  return (
    <div style={{ width: '100%', height: '100%', background: '#1a1a1a' }}>
      <MapContainer
        center={[0, 0]}
        zoom={18}
        style={{ width: '100%', height: '100%' }}
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
            <TileLayer
              url={tileUrl}
              tms={false}
              opacity={1.0}
              minNativeZoom={14}
              maxNativeZoom={22}
              minZoom={14}
              maxZoom={24}
            />
          </LayersControl.Overlay>

        </LayersControl>

        <DroneIndicator datasetName={currentDataset.name} />
      </MapContainer>
    </div>
  );
};

const droneIcon = new L.Icon({
  iconUrl: '/drone.png', // Update this to match your actual file name!
  iconSize: [32, 32],                // Width and height in pixels
  iconAnchor: [16, 32],              // The exact pixel that points to the coordinate (usually bottom-center)
  tooltipAnchor: [0, -32]            // Where the tooltip should float relative to the icon
});

// Helper to center the map on the drone data automatically
// Helper to center the map AND show a marker when zoomed out
function DroneIndicator({ datasetName }: { datasetName: string }) {
  const map = useMap();

  // State to hold our coordinates and the current zoom level
  const [center, setCenter] = useState<{ lat: number, lng: number } | null>(null);
  const [currentZoom, setCurrentZoom] = useState(map.getZoom());

  // 1. Listen for zoom changes and update state
  useMapEvents({
    zoomend: () => {
      setCurrentZoom(map.getZoom());
    },
  });

  // 2. Fetch the center coordinates on load
  useEffect(() => {
    const fetchCenter = async () => {
      try {
        const response = await fetch(`/api/outputs/${datasetName}_out/map_center.json`);

        if (response.ok) {
          const centerData = await response.json();
          setCenter(centerData);
          // Fly the camera to the model on first load
          map.setView([centerData.lat, centerData.lng], 18);
        } else {
          console.warn("map_center.json not found for this dataset.");
        }
      } catch (error) {
        console.error("Error fetching map center:", error);
      }
    };

    fetchCenter();
  }, [datasetName, map]);

  // 3. If we have coordinates AND the zoom is less than 14, draw the marker
  if (center && currentZoom < 15) {
    return (
      <Marker
        position={[center.lat, center.lng]}
        icon={droneIcon}
      >
        {/* A nice little label so they know what the pin is */}
        {/* <Tooltip permanent direction="top" offset={[0, -20]}>
          Drone Survey Location
        </Tooltip> */}
      </Marker >
    );
  }

  // Otherwise, render nothing (the tiles are visible!)
  return null;
}

function ZoomLogger() {
  const map = useMapEvents({
    zoomend: () => {
      console.log("Current Zoom Level:", map.getZoom());
    },
  });
  return null;
}

export default MapViewer;