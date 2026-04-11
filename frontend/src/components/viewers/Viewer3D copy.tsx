import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
// Notice the .js extensions! This fixes the ts(2307) error in most Vite setups
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { OBJLoader } from 'three/examples/jsm/loaders/OBJLoader.js';
import { MTLLoader } from 'three/examples/jsm/loaders/MTLLoader.js';
import { useData } from '@/context/DataContext';
import './Viewer3D.css';

interface PolyData {
  id: number;
  floorZ: number;
  volume: number;
}

const Viewer3D: React.FC = () => {
  const { datasets, selectedFolder } = useData();
  const currentDataset = datasets.find(d => d.name === selectedFolder);

  const mountRef = useRef<HTMLDivElement>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);
  const engineRef = useRef<any>(null);

  // React UI State
  const [polygons, setPolygons] = useState<PolyData[]>([]);
  const [isDrawing, setIsDrawing] = useState(false);
  const [editingPolyId, setEditingPolyId] = useState<number | null>(null);
  const [loadingMsg, setLoadingMsg] = useState<string | null>("Initializing 3D Engine...");

  // --- 1. INITIALIZE THREE.JS (Runs once) ---
  useEffect(() => {
    if (!mountRef.current || !tooltipRef.current) return;

    let scene: THREE.Scene, camera: THREE.PerspectiveCamera, renderer: THREE.WebGLRenderer, controls: OrbitControls, mesh: THREE.Mesh | undefined, raycaster: THREE.Raycaster, mouse: THREE.Vector2;
    let animationFrameId: number;

    let enginePolys: any[] = [];
    let engineIsDrawing = false;
    let engineEditingPolyId: number | null = null;
    let currentPoints3D: THREE.Vector3[] = [];
    let currentLineMesh: THREE.Line | null = null;
    let hoveredPolyId: number | null = null;
    let polyCounter = 0;

    const init = () => {
      // Get the exact pixel size of the React Tab Panel
      const width = mountRef.current?.clientWidth || window.innerWidth;
      const height = mountRef.current?.clientHeight || window.innerHeight;

      scene = new THREE.Scene();
      camera = new THREE.PerspectiveCamera(75, width / height, 0.1, 10000);

      renderer = new THREE.WebGLRenderer({ antialias: true });
      renderer.setSize(width, height);
      mountRef.current?.appendChild(renderer.domElement);

      controls = new OrbitControls(camera, renderer.domElement);
      controls.mouseButtons = { LEFT: THREE.MOUSE.PAN, MIDDLE: THREE.MOUSE.ROTATE, RIGHT: null };

      raycaster = new THREE.Raycaster();
      mouse = new THREE.Vector2();

      scene.add(new THREE.AmbientLight(0xffffff, 1.0));

      window.addEventListener('mousedown', onMouseDown);
      window.addEventListener('click', onClick);
      window.addEventListener('dblclick', onDoubleClick);
      window.addEventListener('mousemove', onMouseMove);
      // window.addEventListener('contextmenu', e => e.preventDefault());

      animate();
    };

    const syncReactUI = () => {
      setPolygons(enginePolys.map(p => ({ id: p.id, floorZ: p.floorZ, volume: p.volume })));
      setIsDrawing(engineIsDrawing);
      setEditingPolyId(engineEditingPolyId);
    };

    // --- ENGINE API EXPOSED TO REACT ---
    engineRef.current = {
      loadModelFromAPI: (datasetName: string) => {
        setLoadingMsg(`Downloading 3D files for ${datasetName}...`);

        // Assuming Metashape named them 'model.obj' and 'model.mtl'
        const basePath = `/api/outputs/${datasetName}_out/`;
        const objUrl = `${basePath}model_decimated.obj`;
        const mtlUrl = `${basePath}model_decimated.mtl`;

        const manager = new THREE.LoadingManager();
        const mtlLoader = new MTLLoader(manager);
        const objLoader = new OBJLoader(manager);

        const onProgress = (xhr: ProgressEvent) => {
          if (xhr.lengthComputable) {
            const percent = Math.round((xhr.loaded / xhr.total) * 100);
            setLoadingMsg(`Loading Model... ${percent}%`);
          } else {
            setLoadingMsg(`Loading Model...`);
          }
        };

        const onObjLoad = (group: THREE.Group) => {
          if (mesh && mesh.parent) scene.remove(mesh.parent);
          enginePolys.forEach(p => scene.remove(p.lineMesh));
          enginePolys = [];
          syncReactUI();

          group.rotation.x = -Math.PI / 2;

          group.traverse(child => {
            if ((child as THREE.Mesh).isMesh) {
              const m = child as THREE.Mesh;
              m.geometry = m.geometry.index ? m.geometry.toNonIndexed() : m.geometry;
              m.geometry.computeVertexNormals();
              mesh = m;

              const mat = m.material as THREE.ShaderMaterial | THREE.MeshPhongMaterial;
              mat.onBeforeCompile = (shader) => {
                shader.uniforms.uPoly = { value: new Array(50).fill(new THREE.Vector2()) };
                shader.uniforms.uPolyLen = { value: 0 };
                shader.uniforms.uFloor = { value: -9999.0 };
                mat.userData.shader = shader;

                shader.vertexShader = `varying vec3 vLocalPos;\n` + shader.vertexShader.replace(
                  `#include <begin_vertex>`,
                  `#include <begin_vertex>\nvLocalPos = position;`
                );

                shader.fragmentShader = `
                  varying vec3 vLocalPos;
                  uniform vec2 uPoly[50];
                  uniform int uPolyLen;
                  uniform float uFloor;
                  bool isInside(vec2 pt) {
                      bool c = false;
                      for (int i = 0, j = 49; i < 50; i++) {
                          if (i >= uPolyLen) break;
                          j = (i == 0) ? uPolyLen - 1 : i - 1;
                          if (((uPoly[i].y > pt.y) != (uPoly[j].y > pt.y)) &&
                              (pt.x < (uPoly[j].x - uPoly[i].x) * (pt.y - uPoly[i].y) / (uPoly[j].y - uPoly[i].y) + uPoly[i].x)) {
                              c = !c;
                          }
                      }
                      return c;
                  }
                \n` + shader.fragmentShader.replace(
                  `#include <dithering_fragment>`,
                  `#include <dithering_fragment>
                  if (uPolyLen > 2 && vLocalPos.z > uFloor) {
                      if (isInside(vLocalPos.xy)) {
                          gl_FragColor = mix(gl_FragColor, vec4(0.0, 1.0, 0.0, gl_FragColor.a), 0.45);
                      }
                  }`
                );
              };
            }
          });
          scene.add(group);
          focusCamera(group);
          setLoadingMsg(null); // Hide loading screen
        };

        // Try to load MTL first, then OBJ. Fallback to just OBJ if MTL is missing.
        mtlLoader.load(
          mtlUrl,
          (materials) => {
            materials.preload();
            objLoader.setMaterials(materials);
            objLoader.load(objUrl, onObjLoad, onProgress, () => setLoadingMsg("Failed to load .obj"));
          },
          undefined,
          (err) => {
            console.warn("MTL not found, loading OBJ without materials...", err);
            objLoader.load(objUrl, onObjLoad, onProgress, () => setLoadingMsg("Failed to load .obj"));
          }
        );
      },

      toggleDrawMode: () => {
        if (!mesh) return alert("Load a model first.");
        engineIsDrawing = !engineIsDrawing;
        if (engineIsDrawing) {
          if (engineEditingPolyId !== null) engineRef.current.toggleEditMode(engineEditingPolyId);
        } else {
          if (currentLineMesh && mesh?.parent) mesh.parent.remove(currentLineMesh);
          currentLineMesh = null;
          currentPoints3D = [];
        }
        syncReactUI();
      },

      toggleEditMode: (id: number) => {
        if (engineIsDrawing) engineRef.current.toggleDrawMode();
        engineEditingPolyId = engineEditingPolyId === id ? null : id;

        enginePolys.forEach(p => {
          if (p.lineMesh) p.lineMesh.material.color.setHex((p.id === engineEditingPolyId) ? 0xffaa00 : 0x00ff00);
        });
        syncReactUI();
      },

      deletePolygon: (id: number) => {
        const idx = enginePolys.findIndex(p => p.id === id);
        if (idx > -1) {
          if (mesh?.parent) mesh.parent.remove(enginePolys[idx].lineMesh);
          enginePolys.splice(idx, 1);
          if (engineEditingPolyId === id) engineRef.current.toggleEditMode(id);
          clearShader();
          syncReactUI();
        }
      }
    };

    let clickTimeout: ReturnType<typeof setTimeout> | null = null;
    const onClick = (event: MouseEvent) => {
      if (event.button !== 0 || !mesh || (event.target as HTMLElement).tagName === 'BUTTON') return;
      if (clickTimeout !== null) { clearTimeout(clickTimeout); clickTimeout = null; }
      else { clickTimeout = setTimeout(() => { handleLeftClickComplete(event); clickTimeout = null; }, 200); }
    };

    const handleLeftClickComplete = (event: MouseEvent) => {
      updateMouse(event);
      raycaster.setFromCamera(mouse, camera);
      const intersects = raycaster.intersectObject(mesh!);
      if (intersects.length === 0) return;
      const pt = mesh!.worldToLocal(intersects[0].point.clone());

      if (engineIsDrawing) {
        currentPoints3D.push(pt);
        updateDrawingLine();
      }
      else if (engineEditingPolyId !== null) {
        const poly = enginePolys.find(p => p.id === engineEditingPolyId);
        if (poly) {
          const bestIdx = getClosestSegmentIndex(pt, poly.points3D);
          poly.points3D.splice(bestIdx + 1, 0, pt);
          recalculatePolygon(poly);
          syncReactUI();
        }
      }
    };

    const onMouseDown = (event: MouseEvent) => {
      if (event.button === 2 && engineEditingPolyId !== null && mesh) {
        updateMouse(event);
        raycaster.setFromCamera(mouse, camera);
        const intersects = raycaster.intersectObject(mesh);
        if (intersects.length > 0) {
          const pt = mesh.worldToLocal(intersects[0].point.clone());
          const poly = enginePolys.find(p => p.id === engineEditingPolyId);
          if (poly) {
            if (poly.points3D.length <= 3) return alert("A polygon must have at least 3 points.");
            let minDistSq = Infinity, bestIdx = -1;
            for (let i = 0; i < poly.points3D.length; i++) {
              let dSq = pt.distanceToSquared(poly.points3D[i]);
              if (dSq < minDistSq) { minDistSq = dSq; bestIdx = i; }
            }
            poly.points3D.splice(bestIdx, 1);
            recalculatePolygon(poly);
            syncReactUI();
          }
        }
      }
    };

    const onDoubleClick = () => {
      if (!engineIsDrawing || currentPoints3D.length < 3) return;
      polyCounter++;
      let poly = { id: polyCounter, points3D: currentPoints3D };
      recalculatePolygon(poly, true);
      if (currentLineMesh && mesh?.parent) mesh.parent.remove(currentLineMesh);
      currentLineMesh = null;
      engineRef.current.toggleDrawMode();
    };

    const onMouseMove = (event: MouseEvent) => {
      if (!mesh || engineIsDrawing || engineEditingPolyId !== null || !tooltipRef.current) {
        if (tooltipRef.current) tooltipRef.current.style.display = 'none';
        return;
      }
      updateMouse(event);
      raycaster.setFromCamera(mouse, camera);
      const intersects = raycaster.intersectObject(mesh);
      let foundPoly = null;
      if (intersects.length > 0) {
        const localPoint = mesh.worldToLocal(intersects[0].point.clone());
        const pt2D = new THREE.Vector2(localPoint.x, localPoint.y);
        for (let p of enginePolys) { if (pointInPolygon(pt2D, p.points2D)) { foundPoly = p; break; } }
      }

      if (foundPoly) {
        tooltipRef.current.style.display = 'block';
        tooltipRef.current.style.left = (event.clientX + 15) + 'px';
        tooltipRef.current.style.top = (event.clientY + 15) + 'px';
        tooltipRef.current.innerHTML = `<b>Poly #${foundPoly.id}</b><br>Vol: ${foundPoly.volume.toLocaleString(undefined, { maximumFractionDigits: 2 })} units³`;
        if (hoveredPolyId !== foundPoly.id) { hoveredPolyId = foundPoly.id; updateShader(foundPoly); }
      } else {
        tooltipRef.current.style.display = 'none';
        if (hoveredPolyId !== null) { hoveredPolyId = null; clearShader(); }
      }
    };

    const recalculatePolygon = (poly: any, isNew = false) => {
      let sumZ = 0;
      poly.points3D.forEach((p: THREE.Vector3) => sumZ += p.z);
      poly.floorZ = sumZ / poly.points3D.length;
      poly.points2D = poly.points3D.map((p: THREE.Vector3) => new THREE.Vector2(p.x, p.y));
      poly.volume = calculateVolumeInPolygon(poly.points2D, poly.floorZ);

      if (poly.lineMesh && mesh?.parent) mesh.parent.remove(poly.lineMesh);
      const geo = new THREE.BufferGeometry().setFromPoints([...poly.points3D, poly.points3D[0]]);
      const color = (engineEditingPolyId === poly.id) ? 0xffaa00 : 0x00ff00;
      const mat = new THREE.LineBasicMaterial({ color: color, linewidth: 3, depthTest: false });
      poly.lineMesh = new THREE.Line(geo, mat);
      poly.lineMesh.renderOrder = 999;
      if (mesh?.parent) mesh.parent.add(poly.lineMesh);

      if (isNew) enginePolys.push(poly);
      if (hoveredPolyId === poly.id) updateShader(poly);
    };

    const getClosestSegmentIndex = (point: THREE.Vector3, points: THREE.Vector3[]) => {
      let minDistSq = Infinity, bestIdx = -1;
      for (let i = 0; i < points.length; i++) {
        let j = (i + 1) % points.length, v = points[i], w = points[j];
        const vw = new THREE.Vector3().subVectors(w, v);
        const l2 = vw.lengthSq();
        let distSq;
        if (l2 === 0) distSq = point.distanceToSquared(v);
        else {
          let t = Math.max(0, Math.min(1, point.clone().sub(v).dot(vw) / l2));
          distSq = point.distanceToSquared(v.clone().add(vw.multiplyScalar(t)));
        }
        if (distSq < minDistSq) { minDistSq = distSq; bestIdx = i; }
      }
      return bestIdx;
    };

    const calculateVolumeInPolygon = (poly2D: THREE.Vector2[], floorZ: number) => {
      if (!mesh) return 0;
      let volume = 0;
      const pos = mesh.geometry.attributes.position.array;
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

    const pointInPolygon = (pt: THREE.Vector2, poly: THREE.Vector2[]) => {
      let inside = false;
      for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
        const intersect = ((poly[i].y > pt.y) !== (poly[j].y > pt.y)) && (pt.x < (poly[j].x - poly[i].x) * (pt.y - poly[i].y) / (poly[j].y - poly[i].y) + poly[i].x);
        if (intersect) inside = !inside;
      }
      return inside;
    };

    const updateShader = (poly: any) => {
      if (!mesh?.material || !(mesh.material as any).userData.shader) return;
      const uniforms = (mesh.material as any).userData.shader.uniforms;
      for (let i = 0; i < 50; i++) {
        if (i < poly.points2D.length) uniforms.uPoly.value[i].copy(poly.points2D[i]);
        else uniforms.uPoly.value[i].set(0, 0);
      }
      uniforms.uPolyLen.value = poly.points2D.length;
      uniforms.uFloor.value = poly.floorZ;
    };

    const clearShader = () => {
      if (!mesh?.material || !(mesh.material as any).userData.shader) return;
      (mesh.material as any).userData.shader.uniforms.uPolyLen.value = 0;
    };

    const updateDrawingLine = () => {
      if (currentLineMesh && mesh?.parent) mesh.parent.remove(currentLineMesh);
      const geo = new THREE.BufferGeometry().setFromPoints(currentPoints3D.map(p => p.clone()));
      const mat = new THREE.LineBasicMaterial({ color: 0xffff00, linewidth: 2, depthTest: false });
      currentLineMesh = new THREE.Line(geo, mat);
      currentLineMesh.renderOrder = 999;
      if (mesh?.parent) mesh.parent.add(currentLineMesh);
    };

    const updateMouse = (e: MouseEvent) => { mouse.x = (e.clientX / window.innerWidth) * 2 - 1; mouse.y = -(e.clientY / window.innerHeight) * 2 + 1; };
    const focusCamera = (obj: THREE.Object3D) => {
      const box = new THREE.Box3().setFromObject(obj);
      const center = box.getCenter(new THREE.Vector3());
      const size = box.getSize(new THREE.Vector3());
      camera.position.set(center.x + size.x, center.y + size.y, center.z + size.z);
      controls.target.copy(center);
      controls.update();
    };

    const animate = () => { animationFrameId = requestAnimationFrame(animate); renderer.render(scene, camera); };

    init();

    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener('mousedown', onMouseDown);
      window.removeEventListener('click', onClick);
      window.removeEventListener('dblclick', onDoubleClick);
      window.removeEventListener('mousemove', onMouseMove);
      mountRef.current?.removeChild(renderer.domElement);
      renderer.dispose();
    };
  }, []); // Only runs once on mount

  // --- 2. TRIGGER LOAD WHEN DATASET CHANGES ---
  useEffect(() => {
    if (engineRef.current && currentDataset?.name) {
      // Clear out the previous model's polygons
      setPolygons([]);
      setIsDrawing(false);
      setEditingPolyId(null);
      // Tell Three.js to download the new dataset
      engineRef.current.loadModelFromAPI(currentDataset.name);
    }
  }, [currentDataset?.name]);


  // Make sure we have a dataset selected, otherwise tell the user
  if (!currentDataset) {
    return <div style={{ padding: '40px', color: '#888' }}>Select a dataset to view the 3D Model.</div>;
  }

  return (
    <div className="studio-container">

      {/* Loading Overlay */}
      {loadingMsg && (
        <div className="drop-zone" style={{ background: 'rgba(0,0,0,0.8)', zIndex: 50, color: 'white', border: 'none' }}>
          <h2>{loadingMsg}</h2>
        </div>
      )}

      <div className="tooltip" ref={tooltipRef}>Vol: 0</div>

      {/* Main UI */}
      <div className="studio-ui">
        <b>3D POLYGON STUDIO</b>
        <span className="hint">Left = Pan | Middle = Orbit | Hover = Vol</span>

        <div className="toolbar">
          <button
            className={`btn primary ${isDrawing ? 'active' : ''}`}
            onClick={() => engineRef.current?.toggleDrawMode()}
            disabled={!!loadingMsg}
          >
            {isDrawing ? "❌ Cancel Drawing" : "➕ Draw New Polygon"}
          </button>
        </div>

        {isDrawing && (
          <div className="draw-hint" style={{ display: 'block', borderColor: '#00ff00' }}>
            <span style={{ color: '#00ff00' }}>
              <b>Draw Mode</b><br />Left-click: Add point<br />Double-click: Close Poly
            </span>
          </div>
        )}

        {editingPolyId !== null && (
          <div className="draw-hint" style={{ display: 'block', borderColor: '#ffaa00' }}>
            <span style={{ color: '#ffaa00' }}>
              <b>Editing Poly #{editingPolyId}</b><br />Left-click: Insert point on edge<br />Right-click: Delete vertex
            </span>
          </div>
        )}

        <div className="poly-container">
          {polygons.map(p => (
            <div key={p.id} className={`poly-item ${editingPolyId === p.id ? 'editing' : ''}`}>
              <div className="poly-info">
                <b>Poly #{p.id}</b><br />
                Floor: <span className="val">{p.floorZ.toFixed(2)}</span> | Vol: <span className="val">{p.volume.toLocaleString(undefined, { maximumFractionDigits: 1 })}</span>
              </div>
              <div className="poly-actions">
                <button className="btn-icon edit" onClick={() => engineRef.current?.toggleEditMode(p.id)}>✎</button>
                <button className="btn-icon del" onClick={() => engineRef.current?.deletePolygon(p.id)}>X</button>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div ref={mountRef} />
    </div>
  );
};


export default Viewer3D;