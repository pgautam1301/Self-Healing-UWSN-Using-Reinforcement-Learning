"""
threejs_component.py - Interactive Three.js 3D Underwater Network Canvas.
Project: AquaNet Self-Healing UWSN Control Center
Renders an interactive, WebGL 3D subsea environment with:
- 12 real nodes at verified coordinates
- Seafloor (Z=0m) & surface gateway (Z=100m)
- Underwater floating particulate effect
- Interactive Show/Hide Links with smooth progressive line drawing
- Animated packet transmission along multi-hop routes
- Self-healing recovery route animation (bypassing dead Sensor 5)
- OrbitControls (rotate, zoom, pan)
- Clickable node inspection HUD
"""

import os
import json
from typing import Optional, Dict, Any


def get_threejs_html(
    active_step: int = 0,
    is_fault_active: bool = False,
    show_links_initially: bool = False,
    sim_time: float = 0.0,
    selected_node_id: Optional[int] = 5
) -> str:
    """Generates a self-contained HTML/JS bundle with embedded Three.js and OrbitControls."""
    
    # Path to local static libraries if available
    base_dir = os.path.dirname(os.path.abspath(__file__))
    three_path = os.path.join(base_dir, "static", "three.min.js")
    controls_path = os.path.join(base_dir, "static", "OrbitControls.js")

    three_js_code = ""
    orbit_controls_code = ""

    if os.path.exists(three_path) and os.path.exists(controls_path):
        try:
            with open(three_path, "r", encoding="utf-8") as f:
                three_js_code = f.read()
            with open(controls_path, "r", encoding="utf-8") as f:
                orbit_controls_code = f.read()
        except Exception:
            three_js_code = ""
            orbit_controls_code = ""

    # 12 Actual Project Nodes directly from scratch/underwater-network.cc
    nodes_data = [
        {"id": 12, "name": "Source Node 12", "type": "source", "x": 50.0, "y": 50.0, "z": 0.0, "energy": 100.0, "status": "Operational", "role": "Seafloor Application Source"},
        {"id": 1,  "name": "Sensor 1", "type": "sensor", "x": 90.0, "y": 90.0, "z": 10.0, "energy": 100.0, "status": "Operational", "role": "Intermediate Relay"},
        {"id": 2,  "name": "Sensor 2", "type": "sensor", "x": 130.0, "y": 130.0, "z": 18.0, "energy": 100.0, "status": "Operational", "role": "Intermediate Relay"},
        {"id": 3,  "name": "Sensor 3", "type": "sensor", "x": 170.0, "y": 170.0, "z": 26.0, "energy": 100.0, "status": "Operational", "role": "Intermediate Relay"},
        {"id": 4,  "name": "Sensor 4", "type": "sensor", "x": 210.0, "y": 210.0, "z": 34.0, "energy": 100.0, "status": "Operational", "role": "Branch Forwarder"},
        {"id": 5,  "name": "Sensor 5", "type": "sensor_failed" if is_fault_active else "sensor", "x": 250.0, "y": 250.0, "z": 42.0, "energy": 72.21 if is_fault_active else 100.0, "status": "FAILED (Halted at 50s)" if is_fault_active else "Operational", "role": "Fault Subject Node"},
        {"id": 6,  "name": "Sensor 6", "type": "sensor", "x": 290.0, "y": 290.0, "z": 50.0, "energy": 100.0, "status": "Operational", "role": "Spatial Recovery Candidate"},
        {"id": 7,  "name": "Sensor 7", "type": "sensor", "x": 330.0, "y": 330.0, "z": 58.0, "energy": 100.0, "status": "Operational", "role": "Intermediate Relay"},
        {"id": 8,  "name": "Sensor 8", "type": "sensor", "x": 370.0, "y": 370.0, "z": 66.0, "energy": 100.0, "status": "Operational", "role": "Intermediate Relay"},
        {"id": 9,  "name": "Sensor 9", "type": "sensor", "x": 410.0, "y": 410.0, "z": 74.0, "energy": 100.0, "status": "Operational", "role": "Intermediate Relay"},
        {"id": 10, "name": "Sensor 10", "type": "sensor", "x": 450.0, "y": 450.0, "z": 82.0, "energy": 100.0, "status": "Operational", "role": "Intermediate Relay"},
        {"id": 11, "name": "Surface Sink 11", "type": "sink", "x": 500.0, "y": 500.0, "z": 100.0, "energy": 100.0, "status": "Operational", "role": "Surface Gateway Sink"}
    ]

    nodes_json = json.dumps(nodes_data)

    # Use bundled JS if present, otherwise fallback to CDN scripts
    script_header = ""
    if three_js_code and orbit_controls_code:
        script_header = f"""
        <script>
        {three_js_code}
        </script>
        <script>
        {orbit_controls_code}
        </script>
        """
    else:
        script_header = """
        <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
        """

    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>AquaNet 3D Subsea Control Canvas</title>
    {script_header}
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            background: #09090B;
            color: #FAFAFA;
            font-family: -apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', sans-serif;
            overflow: hidden;
            width: 100vw;
            height: 100vh;
        }}
        #canvas-container {{
            width: 100%;
            height: 100%;
            position: relative;
        }}
        /* Floating Glassmorphic Top Controls */
        .controls-overlay {{
            position: absolute;
            top: 14px;
            left: 16px;
            z-index: 100;
            display: flex;
            gap: 10px;
            align-items: center;
        }}
        .action-btn {{
            background: #18181B;
            border: 1px solid rgba(167, 139, 250, 0.3);
            color: #DDD6FE;
            padding: 8px 14px;
            border-radius: 8px;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            backdrop-filter: blur(10px);
            transition: all 0.2s ease;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
        }}
        .action-btn:hover {{
            background: #222126;
            border-color: #A78BFA;
            color: #FAFAFA;
            box-shadow: 0 0 12px rgba(167, 139, 250, 0.35);
            transform: translateY(-1px);
        }}
        .action-btn.active {{
            background: rgba(167, 139, 250, 0.25);
            border-color: #A78BFA;
            color: #FFFFFF;
            box-shadow: 0 0 14px rgba(167, 139, 250, 0.5);
        }}
        .action-btn.fault-btn {{
            border-color: rgba(239, 68, 68, 0.4);
            color: #FCA5A5;
        }}
        .action-btn.fault-btn:hover, .action-btn.fault-btn.active {{
            background: rgba(239, 68, 68, 0.25);
            border-color: #EF4444;
            color: #FFFFFF;
            box-shadow: 0 0 14px rgba(239, 68, 68, 0.5);
        }}

        /* Legend HUD (Bottom-Left) */
        .legend-hud {{
            position: absolute;
            bottom: 14px;
            left: 16px;
            z-index: 100;
            background: rgba(24, 24, 27, 0.85);
            border: 1px solid rgba(167, 139, 250, 0.2);
            border-radius: 10px;
            padding: 10px 14px;
            font-size: 11px;
            backdrop-filter: blur(12px);
            display: flex;
            gap: 14px;
            align-items: center;
            box-shadow: 0 6px 20px rgba(0, 0, 0, 0.5);
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 6px;
            color: #A1A1AA;
        }}
        .legend-dot {{
            width: 8px;
            height: 8px;
            border-radius: 50%;
        }}

        /* Telemetry Node Info HUD Card (Top-Right) */
        .info-card {{
            position: absolute;
            top: 14px;
            right: 16px;
            z-index: 100;
            background: rgba(24, 24, 27, 0.9);
            border: 1px solid rgba(167, 139, 250, 0.35);
            border-radius: 12px;
            padding: 14px 18px;
            width: 260px;
            backdrop-filter: blur(14px);
            box-shadow: 0 8px 30px rgba(0, 0, 0, 0.6);
            transition: all 0.25s ease;
        }}
        .info-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid rgba(167, 139, 250, 0.2);
            padding-bottom: 8px;
            margin-bottom: 8px;
        }}
        .info-title {{
            font-size: 13px;
            font-weight: 700;
            color: #DDD6FE;
        }}
        .info-row {{
            display: flex;
            justify-content: space-between;
            font-size: 11px;
            margin-bottom: 4px;
            color: #A1A1AA;
        }}
        .info-val {{
            color: #FAFAFA;
            font-family: monospace;
            font-weight: 600;
        }}
        .badge-status {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 9999px;
            font-size: 9px;
            font-weight: 700;
            text-transform: uppercase;
        }}
        .badge-ok {{ background: rgba(52, 211, 153, 0.15); border: 1px solid #34D399; color: #34D399; }}
        .badge-fail {{ background: rgba(239, 68, 68, 0.2); border: 1px solid #EF4444; color: #F87171; }}

        /* Live Packet Telemetry Banner */
        .packet-banner {{
            position: absolute;
            bottom: 14px;
            right: 16px;
            z-index: 100;
            background: rgba(24, 24, 27, 0.85);
            border: 1px solid rgba(167, 139, 250, 0.25);
            border-radius: 8px;
            padding: 8px 14px;
            font-size: 11px;
            font-family: monospace;
            color: #C4B5FD;
            backdrop-filter: blur(10px);
        }}
    </style>
</head>
<body>
    <div id="canvas-container">
        <!-- Floating Header Controls -->
        <div class="controls-overlay">
            <button id="btn-toggle-links" class="action-btn">
                <span id="links-icon">👁️</span> <span id="links-text">Show Links</span>
            </button>
            <button id="btn-packet" class="action-btn">
                <span>⚡</span> <span id="packet-btn-text">Transmit Packet</span>
            </button>
            <button id="btn-fault" class="action-btn fault-btn {'active' if is_fault_active else ''}">
                <span>⚠️</span> <span id="fault-btn-text">{'Sensor 5 Fault Active (t ≥ 50s)' if is_fault_active else 'Simulate t = 50s Fault'}</span>
            </button>
            <button id="btn-reset-cam" class="action-btn">
                <span>🔄</span> Reset Camera
            </button>
        </div>

        <!-- Node Telemetry Card -->
        <div id="node-info-card" class="info-card">
            <div class="info-header">
                <div id="info-node-name" class="info-title">Sensor 5 (Node 5)</div>
                <span id="info-node-badge" class="badge-status badge-ok">OPERATIONAL</span>
            </div>
            <div class="info-row">
                <span>Coordinates:</span>
                <span id="info-node-coords" class="info-val">(250, 250, 42) m</span>
            </div>
            <div class="info-row">
                <span>Elevation / Depth:</span>
                <span id="info-node-depth" class="info-val">Z = 42m (Depth 58m)</span>
            </div>
            <div class="info-row">
                <span>Battery Energy:</span>
                <span id="info-node-energy" class="info-val">100.0 J</span>
            </div>
            <div class="info-row">
                <span>Acoustic Range:</span>
                <span id="info-node-range" class="info-val">250.0 m</span>
            </div>
            <div class="info-row" style="margin-top:6px; border-top:1px solid rgba(255,255,255,0.1); padding-top:4px;">
                <span>Role:</span>
                <span id="info-node-role" class="info-val" style="color:#C4B5FD;">Branch Forwarder</span>
            </div>
        </div>

        <!-- Active Packet Telemetry -->
        <div id="packet-banner" class="packet-banner">
            <span id="packet-status-text">Route Status: Primary Normal Route (Pre-Failure)</span>
        </div>

        <!-- Bottom-Left Legend -->
        <div class="legend-hud">
            <div class="legend-item"><div class="legend-dot" style="background:#C4B5FD;"></div> Source (Node 12)</div>
            <div class="legend-item"><div class="legend-dot" style="background:#A78BFA;"></div> Sensor Relays (1-10)</div>
            <div class="legend-item"><div class="legend-dot" style="background:#34D399;"></div> Surface Gateway (Sink 11)</div>
            <div class="legend-item"><div class="legend-dot" style="background:#EF4444;"></div> Faulty Sensor 5</div>
            <div class="legend-item"><div class="legend-dot" style="background:#34D399; border: 1px dashed #34D399;"></div> Recovery Bypass</div>
        </div>
    </div>

    <script>
        const nodesData = {nodes_json};
        let isFaultActive = {'true' if is_fault_active else 'false'};
        let showLinks = {'true' if show_links_initially else 'false'};
        let selectedNodeId = {selected_node_id if selected_node_id else 5};

        // Coordinate scaling to fit Three.js viewport
        // UWSN domain: X in [0, 500], Y in [0, 500], Elevation Z in [0, 100]
        // Center around (250, 50, 250)
        function toSceneCoords(nx, ny, nz) {{
            const scale = 0.6;
            return {{
                x: (nx - 250) * scale,
                y: (nz - 50) * scale * 1.6, // vertical elevation
                z: (ny - 250) * scale
            }};
        }}

        // Setup Three.js Scene, Camera, Renderer
        const container = document.getElementById('canvas-container');
        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0x09090B);
        scene.fog = new THREE.FogExp2(0x09090B, 0.0016);

        const camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 1, 3000);
        camera.position.set(240, 180, 320);

        const renderer = new THREE.WebGLRenderer({{ antialias: true, alpha: false }});
        renderer.setSize(window.innerWidth, window.innerHeight);
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        renderer.toneMapping = THREE.ACESFilmicToneMapping;
        renderer.toneMappingExposure = 1.2;
        container.appendChild(renderer.domElement);

        const controls = new THREE.OrbitControls(camera, renderer.domElement);
        controls.enableDamping = true;
        controls.dampingFactor = 0.05;
        controls.maxDistance = 900;
        controls.minDistance = 60;
        controls.target.set(0, 0, 0);

        // Ambient and Directional Lighting
        const ambientLight = new THREE.AmbientLight(0x18181B, 1.8);
        scene.add(ambientLight);

        const dirLight = new THREE.DirectionalLight(0xC4B5FD, 1.4);
        dirLight.position.set(100, 300, 150);
        scene.add(dirLight);

        const bottomLight = new THREE.PointLight(0x3B82F6, 1.2, 500);
        bottomLight.position.set(0, -60, 0);
        scene.add(bottomLight);

        // Seafloor Grid (Z = 0m, scene Y = -80)
        const seafloorY = toSceneCoords(0, 0, 0).y;
        const seafloorGrid = new THREE.GridHelper(380, 20, 0x3F3F46, 0x18181B);
        seafloorGrid.position.y = seafloorY;
        scene.add(seafloorGrid);

        // Water Surface Grid (Z = 100m, scene Y = +80)
        const surfaceY = toSceneCoords(0, 0, 100).y;
        const surfaceGrid = new THREE.GridHelper(380, 20, 0x8B5CF6, 0x2E1065);
        surfaceGrid.position.y = surfaceY;
        surfaceGrid.material.opacity = 0.25;
        surfaceGrid.material.transparent = true;
        scene.add(surfaceGrid);

        // Marine Floating Particles Effect (Underwater Snow / Plankton)
        const particleCount = 450;
        const particleGeo = new THREE.BufferGeometry();
        const particlePositions = new Float32Array(particleCount * 3);
        for(let i = 0; i < particleCount * 3; i += 3) {{
            particlePositions[i] = (Math.random() - 0.5) * 500;
            particlePositions[i+1] = (Math.random() - 0.5) * 200;
            particlePositions[i+2] = (Math.random() - 0.5) * 500;
        }}
        particleGeo.setAttribute('position', new THREE.BufferAttribute(particlePositions, 3));
        const particleMat = new THREE.PointsMaterial({{
            color: 0xC4B5FD,
            size: 2.2,
            transparent: true,
            opacity: 0.35,
            blending: THREE.AdditiveBlending
        }});
        const particleSystem = new THREE.Points(particleGeo, particleMat);
        scene.add(particleSystem);

        // Node Meshes & Selection Mapping
        const nodeMeshes = {{}};
        const nodeGroup = new THREE.Group();
        scene.add(nodeGroup);

        // Create 3D Nodes
        nodesData.forEach(n => {{
            const sc = toSceneCoords(n.x, n.y, n.z);
            let geo, mat;

            if (n.type === 'source') {{
                geo = new THREE.OctahedronGeometry(6.5);
                mat = new THREE.MeshStandardMaterial({{
                    color: 0xC4B5FD,
                    emissive: 0x8B5CF6,
                    emissiveIntensity: 0.5,
                    roughness: 0.2,
                    metalness: 0.8
                }});
            }} else if (n.type === 'sink') {{
                geo = new THREE.BoxGeometry(9, 9, 9);
                mat = new THREE.MeshStandardMaterial({{
                    color: 0x34D399,
                    emissive: 0x059669,
                    emissiveIntensity: 0.6,
                    roughness: 0.2,
                    metalness: 0.7
                }});
            }} else {{
                geo = new THREE.SphereGeometry(5.2, 32, 32);
                const isFail = (n.id === 5 && isFaultActive);
                mat = new THREE.MeshStandardMaterial({{
                    color: isFail ? 0xEF4444 : 0xA78BFA,
                    emissive: isFail ? 0xDC2626 : 0x7C3AED,
                    emissiveIntensity: isFail ? 0.9 : 0.45,
                    roughness: 0.3,
                    metalness: 0.6
                }});
            }}

            const mesh = new THREE.Mesh(geo, mat);
            mesh.position.set(sc.x, sc.y, sc.z);
            mesh.userData = n;
            nodeGroup.add(mesh);
            nodeMeshes[n.id] = mesh;

            // Halo glow ring
            const haloGeo = new THREE.RingGeometry(6.8, 7.8, 32);
            const haloMat = new THREE.MeshBasicMaterial({{
                color: (n.id === 5 && isFaultActive) ? 0xEF4444 : 0xC4B5FD,
                side: THREE.DoubleSide,
                transparent: true,
                opacity: 0.35
            }});
            const halo = new THREE.Mesh(haloGeo, haloMat);
            halo.rotation.x = Math.PI / 2;
            mesh.add(halo);
            mesh.userData.halo = halo;
        }});

        // Selected Node Highlight Reticle
        const reticleGeo = new THREE.RingGeometry(9.0, 10.5, 32);
        const reticleMat = new THREE.MeshBasicMaterial({{
            color: 0xFBBF24,
            side: THREE.DoubleSide,
            transparent: true,
            opacity: 0.85
        }});
        const selectionReticle = new THREE.Mesh(reticleGeo, reticleMat);
        selectionReticle.rotation.x = Math.PI / 2;
        scene.add(selectionReticle);

        function updateSelectionReticle(nodeId) {{
            const mesh = nodeMeshes[nodeId];
            if (mesh) {{
                selectionReticle.visible = true;
                selectionReticle.position.copy(mesh.position);
            }} else {{
                selectionReticle.visible = false;
            }}
        }}

        // Links Group (Initially Hidden)
        const linksGroup = new THREE.Group();
        linksGroup.visible = showLinks;
        scene.add(linksGroup);

        // Pre-Failure Primary Route: 12 -> 1 -> 4 -> 5 -> 7 -> 11
        // Post-Failure Recovery Route: 12 -> 1 -> 4 -> 6 -> 7 -> 11
        function buildAcousticLinks() {{
            while(linksGroup.children.length > 0) {{
                linksGroup.remove(linksGroup.children[0]);
            }}

            const txRange = 250.0;
            for (let i = 0; i < nodesData.length; i++) {{
                for (let j = i + 1; j < nodesData.length; j++) {{
                    const n1 = nodesData[i];
                    const n2 = nodesData[j];
                    const dist = Math.hypot(n1.x - n2.x, n1.y - n2.y, n1.z - n2.z);

                    if (dist <= txRange) {{
                        const p1 = toSceneCoords(n1.x, n1.y, n1.z);
                        const p2 = toSceneCoords(n2.x, n2.y, n2.z);
                        const isDeadLink = (n1.id === 5 || n2.id === 5) && isFaultActive;

                        const points = [new THREE.Vector3(p1.x, p1.y, p1.z), new THREE.Vector3(p2.x, p2.y, p2.z)];
                        const lineGeo = new THREE.BufferGeometry().setFromPoints(points);

                        let lineMat;
                        if (isDeadLink) {{
                            lineMat = new THREE.LineDashedMaterial({{
                                color: 0xEF4444,
                                dashSize: 4,
                                gapSize: 3,
                                opacity: 0.65,
                                transparent: true
                            }});
                        }} else {{
                            lineMat = new THREE.LineBasicMaterial({{
                                color: 0xA78BFA,
                                transparent: true,
                                opacity: 0.35
                            }});
                        }}

                        const line = new THREE.Line(lineGeo, lineMat);
                        if (isDeadLink) line.computeLineDistances();
                        linksGroup.add(line);
                    }}
                }}
            }}

            // Highlight Route Lines
            if (isFaultActive) {{
                // Recovery Route in Green: 4 -> 6 -> 7 -> 11
                const recPath = [4, 6, 7, 11];
                const recPoints = recPath.map(id => {{
                    const n = nodesData.find(nd => nd.id === id);
                    const sc = toSceneCoords(n.x, n.y, n.z);
                    return new THREE.Vector3(sc.x, sc.y, sc.z);
                }});
                const recGeo = new THREE.BufferGeometry().setFromPoints(recPoints);
                const recMat = new THREE.LineBasicMaterial({{
                    color: 0x34D399,
                    linewidth: 3,
                    transparent: true,
                    opacity: 0.95
                }});
                const recLine = new THREE.Line(recGeo, recMat);
                linksGroup.add(recLine);
            }} else {{
                // Primary Route in Cyan/Lavender: 4 -> 5 -> 7 -> 11
                const primPath = [4, 5, 7, 11];
                const primPoints = primPath.map(id => {{
                    const n = nodesData.find(nd => nd.id === id);
                    const sc = toSceneCoords(n.x, n.y, n.z);
                    return new THREE.Vector3(sc.x, sc.y, sc.z);
                }});
                const primGeo = new THREE.BufferGeometry().setFromPoints(primPoints);
                const primMat = new THREE.LineBasicMaterial({{
                    color: 0xC4B5FD,
                    linewidth: 2,
                    transparent: true,
                    opacity: 0.85
                }});
                const primLine = new THREE.Line(primGeo, primMat);
                linksGroup.add(primLine);
            }}
        }}

        buildAcousticLinks();
        updateSelectionReticle(selectedNodeId);

        // Animated Traveling Packet
        const packetGeo = new THREE.SphereGeometry(3.2, 16, 16);
        const packetMat = new THREE.MeshBasicMaterial({{ color: 0xFDE047 }});
        const packetMesh = new THREE.Mesh(packetGeo, packetMat);
        packetMesh.visible = false;
        scene.add(packetMesh);

        // Packet Light Glow
        const packetLight = new THREE.PointLight(0xFDE047, 1.8, 60);
        packetMesh.add(packetLight);

        let isPacketActive = false;
        let packetHopIndex = 0;
        let packetT = 0;
        let activeRoutePath = [12, 1, 4, 5, 7, 11];

        function startPacketTransmission() {{
            activeRoutePath = isFaultActive ? [12, 1, 4, 6, 7, 11] : [12, 1, 4, 5, 7, 11];
            packetHopIndex = 0;
            packetT = 0;
            isPacketActive = true;
            packetMesh.visible = true;
            document.getElementById('packet-btn-text').innerText = "Transmitting...";
        }}

        // Raycasting for Node Selection
        const raycaster = new THREE.Raycaster();
        const mouse = new THREE.Vector2();

        window.addEventListener('click', (event) => {{
            const rect = renderer.domElement.getBoundingClientRect();
            mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
            mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

            raycaster.setFromCamera(mouse, camera);
            const intersects = raycaster.intersectObjects(nodeGroup.children);

            if (intersects.length > 0) {{
                const targetNode = intersects[0].object.userData;
                selectNode(targetNode);
            }}
        }});

        function selectNode(n) {{
            selectedNodeId = n.id;
            updateSelectionReticle(n.id);

            const isFail = (n.id === 5 && isFaultActive);
            document.getElementById('info-node-name').innerText = n.name;
            const badge = document.getElementById('info-node-badge');
            badge.className = isFail ? "badge-status badge-fail" : "badge-status badge-ok";
            badge.innerText = isFail ? "FAILED" : "OPERATIONAL";

            document.getElementById('info-node-coords').innerText = `(${{n.x}}, ${{n.y}}, ${{n.z}}) m`;
            document.getElementById('info-node-depth').innerText = `Z = ${{n.z}}m (Depth ${{100 - n.z}}m)`;
            document.getElementById('info-node-energy').innerText = isFail ? "72.21 J (Halted)" : `${{n.energy.toFixed(1)}} J`;
            document.getElementById('info-node-role').innerText = n.role;
        }}

        // Interactive Button Event Listeners
        const btnToggleLinks = document.getElementById('btn-toggle-links');
        btnToggleLinks.addEventListener('click', () => {{
            showLinks = !showLinks;
            linksGroup.visible = showLinks;

            document.getElementById('links-text').innerText = showLinks ? "Hide Links" : "Show Links";
            document.getElementById('links-icon').innerText = showLinks ? "👁️‍🗨️" : "👁️";
            btnToggleLinks.className = showLinks ? "action-btn active" : "action-btn";

            if (showLinks) {{
                // Smooth camera zoom toward network center
                controls.target.set(0, 0, 0);
                const targetPos = new THREE.Vector3(180, 140, 240);
                let t = 0;
                const camAnim = setInterval(() => {{
                    t += 0.05;
                    camera.position.lerp(targetPos, 0.1);
                    if (t >= 1) clearInterval(camAnim);
                }}, 20);
            }}
        }});

        const btnPacket = document.getElementById('btn-packet');
        btnPacket.addEventListener('click', () => {{
            startPacketTransmission();
        }});

        const btnFault = document.getElementById('btn-fault');
        btnFault.addEventListener('click', () => {{
            isFaultActive = !isFaultActive;
            btnFault.className = isFaultActive ? "action-btn fault-btn active" : "action-btn fault-btn";
            document.getElementById('fault-btn-text').innerText = isFaultActive ? "Sensor 5 Fault Active (t ≥ 50s)" : "Simulate t = 50s Fault";

            // Update Sensor 5 appearance
            const s5Mesh = nodeMeshes[5];
            if (s5Mesh) {{
                s5Mesh.material.color.setHex(isFaultActive ? 0xEF4444 : 0xA78BFA);
                s5Mesh.material.emissive.setHex(isFaultActive ? 0xDC2626 : 0x7C3AED);
                s5Mesh.material.emissiveIntensity = isFaultActive ? 0.95 : 0.45;
                if (s5Mesh.userData.halo) {{
                    s5Mesh.userData.halo.material.color.setHex(isFaultActive ? 0xEF4444 : 0xC4B5FD);
                }}
            }}

            // Rebuild links with green bypass
            buildAcousticLinks();

            // Update Telemetry Banner
            const banner = document.getElementById('packet-status-text');
            if (isFaultActive) {{
                banner.innerHTML = "<span style='color:#EF4444;'>[FAULT ACTIVE]</span> Sensor 5 Offline | Self-Healing Bypass via Sensor 6 Active";
            }} else {{
                banner.innerText = "Route Status: Primary Normal Route (Pre-Failure)";
            }}

            // Update selection HUD if S5 selected
            if (selectedNodeId === 5) {{
                selectNode(nodesData.find(nd => nd.id === 5));
            }}
        }});

        const btnResetCam = document.getElementById('btn-reset-cam');
        btnResetCam.addEventListener('click', () => {{
            camera.position.set(240, 180, 320);
            controls.target.set(0, 0, 0);
        }});

        // Animation Loop
        let clock = new THREE.Clock();
        function animate() {{
            requestAnimationFrame(animate);
            const delta = clock.getDelta();

            // Rotate particle system slowly
            particleSystem.rotation.y += 0.0006;

            // Reticle rotation
            selectionReticle.rotation.z += 0.015;

            // Packet Forwarding Animation
            if (isPacketActive) {{
                packetT += delta * 1.5;
                const fromId = activeRoutePath[packetHopIndex];
                const toId = activeRoutePath[packetHopIndex + 1];

                const n1 = nodesData.find(nd => nd.id === fromId);
                const n2 = nodesData.find(nd => nd.id === toId);

                if (n1 && n2) {{
                    const p1 = toSceneCoords(n1.x, n1.y, n1.z);
                    const p2 = toSceneCoords(n2.x, n2.y, n2.z);

                    packetMesh.position.lerpVectors(
                        new THREE.Vector3(p1.x, p1.y, p1.z),
                        new THREE.Vector3(p2.x, p2.y, p2.z),
                        Math.min(packetT, 1.0)
                    );

                    document.getElementById('packet-status-text').innerText = 
                        `Packet Hop: Node ${{fromId}} ➔ Node ${{toId}} (${{Math.round(packetT * 100)}}%)`;

                    if (packetT >= 1.0) {{
                        packetT = 0;
                        packetHopIndex++;

                        // Pulse receiving node
                        const recvMesh = nodeMeshes[toId];
                        if (recvMesh) {{
                            recvMesh.scale.set(1.4, 1.4, 1.4);
                            setTimeout(() => recvMesh.scale.set(1, 1, 1), 220);
                        }}

                        if (packetHopIndex >= activeRoutePath.length - 1) {{
                            isPacketActive = false;
                            packetMesh.visible = false;
                            document.getElementById('packet-btn-text').innerText = "Transmit Packet";
                            document.getElementById('packet-status-text').innerText = 
                                isFaultActive ? "Packet Delivered to Surface Sink 11 via Sensor 6 Bypass (+20.0)" : "Packet Delivered to Surface Sink 11 (+20.0)";
                        }}
                    }}
                }} else {{
                    isPacketActive = false;
                    packetMesh.visible = false;
                }}
            }}

            controls.update();
            renderer.render(scene, camera);
        }}

        animate();

        // Responsive Resizing
        window.addEventListener('resize', () => {{
            camera.aspect = window.innerWidth / window.innerHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(window.innerWidth, window.innerHeight);
        }});
    </script>
</body>
</html>
    """
    return html_content
