import { useEffect, useState } from 'react';
import { useMap, useMapEvents, Marker } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';



const droneIcon = new L.Icon({
  iconUrl: '/drone.png', // Update this to match your actual file name!
  iconSize: [32, 32],                // Width and height in pixels
  iconAnchor: [16, 32],              // The exact pixel that points to the coordinate (usually bottom-center)
  tooltipAnchor: [0, -32]            // Where the tooltip should float relative to the icon
});


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
        const response = await fetch(`/api/outputs/${datasetName}_out/exports/map_center.json`);

        if (response.ok) {
          const centerData = await response.json();
          setCenter(centerData);
          // Fly the camera to the model on first load
          map.setView([centerData.lat, centerData.lng], 18);
        } else {
          console.warn("map_center.json not found for this dataset.");
          map.setView([0, 0], 5);
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

export default DroneIndicator