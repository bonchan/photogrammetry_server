import React, { useState, useEffect, useRef } from 'react';
import { MapContainer, TileLayer, Pane, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';

import DroneIndicator from '../map/DroneIndicator';


// --- CHILD COMPONENT: Handles the CSS Clipping Logic ---
const SwipeLogic = ({ sliderPos, mode }: { sliderPos: number, mode: string }) => {
  const map = useMap();

  useEffect(() => {
    const pane = map.getPane('comparePane');
    if (!pane) return;

    if (mode !== 'swipe') {
      pane.style.clip = 'auto';
      return;
    }

    const updateClip = () => {
      const size = map.getSize();
      // Pixel position of slider relative to map container
      const sliderPixelX = size.x * sliderPos;

      const nw = map.containerPointToLayerPoint([0, 0]);
      const se = map.containerPointToLayerPoint(size);

      // Calculate where the slider is in the "World" (Layer Coordinates)
      const clipX = map.containerPointToLayerPoint([sliderPixelX, 0]).x;

      // Apply clip to the Pane
      pane.style.clip = `rect(${nw.y}px, ${clipX}px, ${se.y}px, ${nw.x}px)`;
    };

    // Run immediately and attach listeners
    updateClip();
    map.on('move', updateClip);
    map.on('zoom', updateClip);
    map.on('resize', updateClip);

    // Cleanup listeners
    return () => {
      map.off('move', updateClip);
      map.off('zoom', updateClip);
      map.off('resize', updateClip);
    };
  }, [map, sliderPos, mode]);

  return null;
};


// --- MAIN COMPONENT ---
const OrthoSwipe = () => {

  

  // State
  const [mode, setMode] = useState<'swipe' | 'opacity'>('swipe');
  const [sliderPos, setSliderPos] = useState(0.5);
  const [opacityBase, setOpacityBase] = useState(1);
  const [opacityCompare, setOpacityCompare] = useState(1);
  const [isDragging, setIsDragging] = useState(false);

  const containerRef = useRef<HTMLDivElement>(null);

  // --- Handle Dragging Logic ---
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isDragging || !containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      let pct = (e.clientX - rect.left) / rect.width;
      pct = Math.max(0, Math.min(1, pct)); // Clamp between 0 and 1
      setSliderPos(pct);
    };

    const handleMouseUp = () => setIsDragging(false);

    if (isDragging) {
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
    }

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging]);



  const TILES_1 = 'LOC-295__2026-04-16__09_21_17'
  const TILES_2 = 'LOC-295__2026-04-16__15_55_40'

  // Fixed URLs for your tile servers
  const baseTileUrl = `/api/outputs/${TILES_1}_out/exports/${TILES_1}_map_tiles/{z}/{x}/{y}.png`;
  const compareTileUrl = `/api/outputs/${TILES_2}_out/exports/${TILES_2}_map_tiles/{z}/{x}/{y}.png`;

  return (
    <div ref={containerRef} style={{ position: 'relative', width: '100%', height: '100vh', background: '#222', overflow: 'hidden' }}>

      {/* --- SWIPE HANDLE --- */}
      {mode === 'swipe' && (
        <div
          onMouseDown={(e) => { e.preventDefault(); setIsDragging(true); }}
          style={{
            position: 'absolute',
            top: 0, bottom: 0,
            left: `${sliderPos * 100}%`,
            width: '4px',
            background: 'white',
            zIndex: 6000,
            cursor: 'col-resize',
            boxShadow: '0 0 5px rgba(0,0,0,0.5)',
          }}
        >
          <div style={{
            position: 'absolute', top: '50%', left: '50%',
            transform: 'translate(-50%, -50%)',
            background: 'white', padding: '4px 8px',
            borderRadius: '10px', fontSize: '10px', fontWeight: 'bold',
            boxShadow: '0 1px 3px rgba(0,0,0,0.3)', whiteSpace: 'nowrap',
            pointerEvents: 'none', userSelect: 'none', color: '#333'
          }}>
            Compare | Base
          </div>
        </div>
      )}

      {/* --- FLOATING CONTROLS --- */}
      <div style={{
        position: 'absolute', top: '20px', left: '60px', zIndex: 5000,
        background: 'rgba(255, 255, 255, 0.95)', padding: '15px',
        borderRadius: '8px', width: '280px', boxShadow: '0 4px 15px rgba(0,0,0,0.5)',
        fontFamily: 'sans-serif', color: '#333'
      }}>
        <h3 style={{ margin: '0 0 10px 0', fontSize: '16px' }}>Ortho Compare</h3>

        <div style={{ display: 'flex', gap: '5px', marginTop: '15px', background: '#eee', padding: '3px', borderRadius: '4px' }}>
          <div
            onClick={() => setMode('swipe')}
            style={{ flex: 1, textAlign: 'center', padding: '5px', fontSize: '12px', cursor: 'pointer', borderRadius: '3px', background: mode === 'swipe' ? '#0078d4' : 'transparent', color: mode === 'swipe' ? 'white' : '#333' }}
          >Swipe</div>
          <div
            onClick={() => setMode('opacity')}
            style={{ flex: 1, textAlign: 'center', padding: '5px', fontSize: '12px', cursor: 'pointer', borderRadius: '3px', background: mode === 'opacity' ? '#0078d4' : 'transparent', color: mode === 'opacity' ? 'white' : '#333' }}
          >Opacity</div>
        </div>

        {mode === 'opacity' && (
          <div style={{ marginTop: '15px', fontSize: '12px', fontWeight: 'bold' }}>
            <label style={{ display: 'block', marginBottom: '5px' }}>Compare Layer Opacity</label>
            <input
              type="range" min="0" max="1" step="0.1" value={opacityCompare}
              onChange={(e) => setOpacityCompare(parseFloat(e.target.value))}
              style={{ width: '100%', marginBottom: '10px' }}
            />

            <label style={{ display: 'block', marginBottom: '5px' }}>Base Layer Opacity</label>
            <input
              type="range" min="0" max="1" step="0.1" value={opacityBase}
              onChange={(e) => setOpacityBase(parseFloat(e.target.value))}
              style={{ width: '100%' }}
            />
          </div>
        )}
      </div>

      {/* --- MAP --- */}
      <MapContainer center={[0, 0]} zoom={2} style={{ width: '100%', height: '100%', zIndex: 1 }} zoomControl={false}>

        <DroneIndicator datasetName={TILES_1}></DroneIndicator>

        <SwipeLogic sliderPos={sliderPos} mode={mode} />

        {/* Global Base Map */}
        <TileLayer
          url="http://{s}.google.com/vt/lyrs=s&x={x}&y={y}&z={z}"
          maxZoom={24} maxNativeZoom={22}
          subdomains={['mt0', 'mt1', 'mt2', 'mt3']}
          attribution="Google"
        />

        {/* Base Orthomosaic (Right Side) */}
        <Pane name="basePane" style={{ zIndex: 200 }}>
          <TileLayer url={baseTileUrl} maxZoom={24} maxNativeZoom={22} opacity={opacityBase} />
        </Pane>

        {/* Compare Orthomosaic (Left Side) */}
        <Pane name="comparePane" style={{ zIndex: 400 }}>
          <TileLayer url={compareTileUrl} maxZoom={24} maxNativeZoom={22} opacity={opacityCompare} />
        </Pane>

      </MapContainer>
    </div>
  );
};

export default OrthoSwipe;