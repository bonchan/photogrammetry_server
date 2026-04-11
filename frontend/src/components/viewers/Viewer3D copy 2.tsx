// src/components/Viewer3D.tsx
import React, { Suspense, useState, useRef, useEffect } from 'react';
import { Canvas, useLoader, useThree, useFrame } from '@react-three/fiber';
import { OrbitControls, Bounds, Html, useProgress } from '@react-three/drei';
import * as THREE from 'three';
import { MTLLoader } from 'three/examples/jsm/loaders/MTLLoader.js';
import { OBJLoader } from 'three/examples/jsm/loaders/OBJLoader.js';
import { useData } from '@/context/DataContext';
import './Viewer3D.css';

interface PolyData {
  id: number;
  floorZ: number;
  volume: number;
  points2D: THREE.Vector2[];
  points3D: THREE.Vector3[];
  lineMesh?: THREE.Line;
}

// --- 1. THE LOADING COMPONENT ---
function Loader() {
  const { progress } = useProgress();
  return (
    <Html center zIndexRange={[100, 100]}>
      <div style={{ color: 'white', background: 'rgba(0,0,0,0.8)', padding: '20px', borderRadius: '8px', whiteSpace: 'nowrap' }}>
        <h2>Loading Model... {Math.round(progress)}%</h2>
      </div>
    </Html>
  );
}

// --- 2. CORE ENGINE: HANDLES MESH, POLYGONS, & RAYCASTING ---
function Engine({ datasetName, isDrawing, editingPolyId, polygons, setPolygons, onPolyHover, toggleDrawMode }: any) {
  const basePath = `/api/outputs/${datasetName}_out/`;
  const { camera, scene, pointer, size } = useThree();
  const raycaster = new THREE.Raycaster();

  // Load Model
  const materials = useLoader(MTLLoader, `${basePath}model_decimated.mtl`);
  const obj = useLoader(OBJLoader, `${basePath}model_decimated.obj`, (loader) => {
    materials.preload();
    loader.setMaterials(materials);
  });

  // Engine state refs to bypass React render cycle during fast mouse movements
  const meshRef = useRef<THREE.Mesh | null>(null);
  const currentPoints3D = useRef<THREE.Vector3[]>([]);
  const currentLineMesh = useRef<THREE.Line | null>(null);
  const clickTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    obj.traverse((child) => {
      if ((child as THREE.Mesh).isMesh) {
        const m = child as THREE.Mesh;
        m.geometry = m.geometry.index ? m.geometry.toNonIndexed() : m.geometry;
        m.geometry.computeVertexNormals();
        if (m.material) (m.material as THREE.Material).side = THREE.DoubleSide;
        meshRef.current = m;

        // Setup Shader for green highlighting
        const mat = m.material as THREE.ShaderMaterial | THREE.MeshPhongMaterial;
        mat.onBeforeCompile = (shader) => {
          shader.uniforms.uPoly = { value: new Array(50).fill(new THREE.Vector2()) };
          shader.uniforms.uPolyLen = { value: 0 };
          shader.uniforms.uFloor = { value: -9999.0 };
          mat.userData.shader = shader;
          shader.vertexShader = `varying vec3 vLocalPos;\n` + shader.vertexShader.replace(`#include <begin_vertex>`, `#include <begin_vertex>\nvLocalPos = position;`);
          shader.fragmentShader = `
            varying vec3 vLocalPos; uniform vec2 uPoly[50]; uniform int uPolyLen; uniform float uFloor;
            bool isInside(vec2 pt) { bool c = false; for (int i=0, j=49; i<50; i++) { if (i>=uPolyLen) break; j=(i==0)?uPolyLen-1:i-1; if (((uPoly[i].y>pt.y)!=(uPoly[j].y>pt.y))&&(pt.x<(uPoly[j].x-uPoly[i].x)*(pt.y-uPoly[i].y)/(uPoly[j].y-uPoly[i].y)+uPoly[i].x)) c=!c; } return c; }
          \n` + shader.fragmentShader.replace(`#include <dithering_fragment>`, `#include <dithering_fragment>\nif (uPolyLen>2 && vLocalPos.z>uFloor) { if (isInside(vLocalPos.xy)) { gl_FragColor = mix(gl_FragColor, vec4(0.0, 1.0, 0.0, gl_FragColor.a), 0.45); } }`);
        };
      }
    });
  }, [obj]);

  // --- POLYGON MATH ---
  const pointInPolygon = (pt: THREE.Vector2, poly: THREE.Vector2[]) => {
    let inside = false;
    for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
      if (((poly[i].y > pt.y) !== (poly[j].y > pt.y)) && (pt.x < (poly[j].x - poly[i].x) * (pt.y - poly[i].y) / (poly[j].y - poly[i].y) + poly[i].x)) inside = !inside;
    }
    return inside;
  };

  const calculateVolumeInPolygon = (poly2D: THREE.Vector2[], floorZ: number) => {
    if (!meshRef.current) return 0;
    let volume = 0;
    const pos = meshRef.current.geometry.attributes.position.array;
    for (let i = 0; i < pos.length / 9; i++) {
      const idx = i * 9;
      const cx = (pos[idx] + pos[idx + 3] + pos[idx + 6]) / 3;
      const cy = (pos[idx + 1] + pos[idx + 4] + pos[idx + 7]) / 3;
      if (pointInPolygon(new THREE.Vector2(cx, cy), poly2D)) {
        const h1 = pos[idx + 2] - floorZ, h2 = pos[idx + 5] - floorZ, h3 = pos[idx + 8] - floorZ;
        if (h1 > 0 || h2 > 0 || h3 > 0) {
          const area = 0.5 * Math.abs(pos[idx] * (pos[idx + 4] - pos[idx + 7]) + pos[idx + 3] * (pos[idx + 7] - pos[idx + 1]) + pos[idx + 6] * (pos[idx + 1] - pos[idx + 4]));
          volume += area * (Math.max(0, h1) + Math.max(0, h2) + Math.max(0, h3)) / 3;
        }
      }
    }
    return volume;
  };

  const updateShader = (poly?: PolyData) => {
    if (!meshRef.current?.material || !(meshRef.current.material as any).userData.shader) return;
    const uniforms = (meshRef.current.material as any).userData.shader.uniforms;
    if (poly) {
      for (let i = 0; i < 50; i++) i < poly.points2D.length ? uniforms.uPoly.value[i].copy(poly.points2D[i]) : uniforms.uPoly.value[i].set(0, 0);
      uniforms.uPolyLen.value = poly.points2D.length;
      uniforms.uFloor.value = poly.floorZ;
    } else {
      uniforms.uPolyLen.value = 0;
    }
  };

  const drawLine = (points: THREE.Vector3[], color: number) => {
    const geo = new THREE.BufferGeometry().setFromPoints(points);
    const mat = new THREE.LineBasicMaterial({ color, linewidth: 3, depthTest: false });
    const line = new THREE.Line(geo, mat);
    line.renderOrder = 999;
    return line;
  };

  // --- MOUSE EVENTS ---
  const handlePointerDown = (e: any) => {
    if (!meshRef.current) return;
    e.stopPropagation();

    // Right Click Delete
    if (e.button === 2 && editingPolyId !== null) {
      const pt = meshRef.current.worldToLocal(e.point.clone());
      setPolygons((prev: PolyData[]) => prev.map(p => {
        if (p.id !== editingPolyId || p.points3D.length <= 3) return p;
        let bestIdx = 0, minDist = Infinity;
        p.points3D.forEach((v, i) => { const d = pt.distanceToSquared(v); if (d < minDist) { minDist = d; bestIdx = i; } });
        const newPoints = [...p.points3D]; newPoints.splice(bestIdx, 1);

        if (p.lineMesh) scene.remove(p.lineMesh);
        const newLine = drawLine([...newPoints, newPoints[0]], 0xffaa00);
        scene.add(newLine);
        return { ...p, points3D: newPoints, lineMesh: newLine };
      }));
      return;
    }

    // Left Click Add
    if (e.button === 0) {
      if (clickTimeout.current) { clearTimeout(clickTimeout.current); clickTimeout.current = null; }
      else {
        clickTimeout.current = setTimeout(() => {
          const pt = meshRef.current!.worldToLocal(e.point.clone());
          if (isDrawing) {
            currentPoints3D.current.push(pt);
            if (currentLineMesh.current) scene.remove(currentLineMesh.current);
            currentLineMesh.current = drawLine(currentPoints3D.current, 0xffff00);
            scene.add(currentLineMesh.current);
          }
          clickTimeout.current = null;
        }, 200);
      }
    }
  };

  const handleDoubleClick = () => {
    if (!isDrawing || currentPoints3D.current.length < 3) return;

    const pts = [...currentPoints3D.current];
    const floorZ = pts.reduce((sum, p) => sum + p.z, 0) / pts.length;
    const pts2D = pts.map(p => new THREE.Vector2(p.x, p.y));
    const vol = calculateVolumeInPolygon(pts2D, floorZ);

    const newLine = drawLine([...pts, pts[0]], 0x00ff00);
    scene.add(newLine);

    setPolygons((prev: PolyData[]) => [...prev, { id: Date.now(), floorZ, volume: vol, points2D: pts2D, points3D: pts, lineMesh: newLine }]);

    if (currentLineMesh.current) scene.remove(currentLineMesh.current);
    currentLineMesh.current = null;
    currentPoints3D.current = [];
    toggleDrawMode();
  };

  useFrame(() => {
    if (!meshRef.current || isDrawing || editingPolyId !== null) return;
    raycaster.setFromCamera(pointer, camera);
    const intersects = raycaster.intersectObject(meshRef.current);
    if (intersects.length > 0) {
      const pt = meshRef.current.worldToLocal(intersects[0].point.clone());
      const p2d = new THREE.Vector2(pt.x, pt.y);
      const found = polygons.find((p: PolyData) => pointInPolygon(p2d, p.points2D));
      if (found) { updateShader(found); onPolyHover(found, intersects[0].point); }
      else { updateShader(); onPolyHover(null); }
    } else {
      updateShader(); onPolyHover(null);
    }
  });

  return (
    <primitive
      object={obj}
      rotation={[-Math.PI / 2, 0, 0]}
      onPointerDown={handlePointerDown}
      onDoubleClick={handleDoubleClick}
    />
  );
}

// --- 3. THE MAIN VIEWER UI ---
const Viewer3D: React.FC = () => {
  const { datasets, selectedFolder } = useData();
  const currentDataset = datasets.find(d => d.name === selectedFolder);

  const [polygons, setPolygons] = useState<PolyData[]>([]);
  const [isDrawing, setIsDrawing] = useState(false);
  const [editingPolyId, setEditingPolyId] = useState<number | null>(null);
  const [hoverData, setHoverData] = useState<{ poly: PolyData, screenPos: THREE.Vector3 } | null>(null);

  useEffect(() => { setPolygons([]); setIsDrawing(false); setEditingPolyId(null); }, [currentDataset?.name]);

  if (!currentDataset) return <div style={{ padding: '40px', color: '#888' }}>Select a dataset to view the 3D Model.</div>;

  return (
    <div className="studio-container">

      {/* 3D Canvas */}
      <div style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%' }}>
        <Canvas 
          // 1. ZENITHAL VIEW: High up on Y, offset Z by 0.01 to prevent Gimbal Lock orbit glitches
          camera={{ position: [0, 500, 0.01], fov: 60, up: [0, 1, 0] }}
        >
          <ambientLight intensity={1.0} />
          
          <Suspense fallback={<Loader />}>
            <Bounds fit clip observe margin={1.2}>
              
              {/* 2. THE UP ARROW: Points straight up (+Y) from center (0,0,0) */}
              <arrowHelper 
                args={[
                  new THREE.Vector3(0, 1, 0), // Direction (Up)
                  new THREE.Vector3(0, 0, 0), // Origin (Center)
                  150,                        // Length
                  0x00ff00,                   // Color (Green)
                  20,                         // Head length
                  10                          // Head width
                ]} 
              />

              <Engine 
                datasetName={currentDataset.name} 
                isDrawing={isDrawing} 
                editingPolyId={editingPolyId}
                polygons={polygons} 
                setPolygons={setPolygons}
                toggleDrawMode={() => setIsDrawing(!isDrawing)}
                onPolyHover={(poly: PolyData | null, pt?: THREE.Vector3) => setHoverData(poly && pt ? {poly, screenPos: pt} : null)}
              />
            </Bounds>
          </Suspense>
          
          <OrbitControls 
            makeDefault
            mouseButtons={{ 
              LEFT: THREE.MOUSE.PAN, 
              MIDDLE: THREE.MOUSE.ROTATE, 
              RIGHT: null as unknown as THREE.MOUSE 
            }}
            enableDamping={true} // Turning this on makes panning/orbiting feel much smoother
            dampingFactor={0.05}
            maxPolarAngle={Math.PI / 2} // Blocks camera from going underneath the floor
          />
        </Canvas>
      </div>

      {/* HTML Hover Tooltip */}
      {hoverData && !isDrawing && editingPolyId === null && (
        <div style={{ position: 'absolute', top: '20px', right: '400px', background: 'rgba(0,255,0,0.9)', color: 'black', padding: '6px 12px', borderRadius: '4px', fontWeight: 'bold', zIndex: 100, pointerEvents: 'none' }}>
          <b>Poly #{hoverData.poly.id.toString().slice(-4)}</b><br />Vol: {hoverData.poly.volume.toLocaleString(undefined, { maximumFractionDigits: 2 })} units³
        </div>
      )}

      {/* HTML UI Panel */}
      <div className="studio-ui" style={{ pointerEvents: 'auto' }}>
        <b>3D POLYGON STUDIO</b>
        <span className="hint">Left=Pan | Mid=Orbit | Hover=Vol</span>

        <div className="toolbar">
          <button className={`btn primary ${isDrawing ? 'active' : ''}`} onClick={() => setIsDrawing(!isDrawing)}>
            {isDrawing ? "❌ Cancel Drawing" : "➕ Draw New Polygon"}
          </button>
        </div>

        {isDrawing && (
          <div className="draw-hint" style={{ display: 'block', borderColor: '#00ff00' }}>
            <span style={{ color: '#00ff00' }}><b>Draw Mode</b><br />Left-click: Add point<br />Double-click: Close Poly</span>
          </div>
        )}

        {editingPolyId !== null && (
          <div className="draw-hint" style={{ display: 'block', borderColor: '#ffaa00' }}>
            <span style={{ color: '#ffaa00' }}><b>Editing Poly</b><br />Right-click: Delete vertex</span>
          </div>
        )}

        <div className="poly-container">
          {polygons.map(p => (
            <div key={p.id} className={`poly-item ${editingPolyId === p.id ? 'editing' : ''}`}>
              <div className="poly-info">
                <b>Poly #{p.id.toString().slice(-4)}</b><br />
                Floor: <span className="val">{p.floorZ.toFixed(2)}</span> | Vol: <span className="val">{p.volume.toLocaleString(undefined, { maximumFractionDigits: 1 })}</span>
              </div>
              <div className="poly-actions">
                <button className="btn-icon edit" onClick={() => setEditingPolyId(editingPolyId === p.id ? null : p.id)}>✎</button>
                <button className="btn-icon del" onClick={() => setPolygons(prev => { const n = prev.filter(x => x.id !== p.id); if (p.lineMesh) p.lineMesh.removeFromParent(); return n; })}>X</button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default Viewer3D;