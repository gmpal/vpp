import React, { useCallback, useEffect, useRef, useState } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import {
  Box, Dialog, DialogTitle, DialogContent, DialogActions,
  Button, TextField, MenuItem, Select, FormControl, InputLabel,
  Typography, Divider, Chip,
} from '@mui/material';
import {
  getSources, createSource, deleteSource,
  getHouseholds, createHousehold, deleteHousehold,
  getVehicles, createVehicle, HouseholdData,
} from '../api';
import { solarIntensityFactor } from '../utils/solarPosition';

interface ClickedLocation { longitude: number; latitude: number; }

interface ClickedBuilding {
  featureId: string | number;
  source: string;
  sourceLayer: string;
  lngLat: { lng: number; lat: number };
  buildingHeight: number;
}

const MAP_STYLE = 'https://tiles.openfreemap.org/styles/liberty';

// Default EV parameters when auto-creating from a community building
const DEFAULT_EV = {
  capacity_kwh: 60,
  soc_kwh: 30,
  max_charge_kw: 7.4,
  max_discharge_kw: 7.4,
  eta: 0.9,
};

const getFeatureHeight = (properties: Record<string, any> | null | undefined): number => {
  if (!properties) return 0;
  const h = Number(properties['render_height'] ?? properties['height'] ?? 0);
  return Number.isFinite(h) && h > 0 ? h : 0;
};

const isRealBuildingFeature = (f: maplibregl.MapGeoJSONFeature): boolean => {
  if (!f.properties) return false;
  if (f.id === undefined || f.id === null) return false;
  const geomType = f.geometry?.type;
  if (geomType !== 'Polygon' && geomType !== 'MultiPolygon') return false;
  const h = getFeatureHeight(f.properties as Record<string, any>);
  return h >= 2;
};

const Map3D: React.FC = () => {
  const mapContainer = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const markersRef = useRef<maplibregl.Marker[]>([]);
  const buildingLayerIdsRef = useRef<string[]>([]);
  const mapReadyRef = useRef(false);
  const buildingTileSourceRef = useRef<string | null>(null);
  const buildingTileSourceLayerRef = useRef<string | null>(null);

  const [sources, setSources] = useState<any[]>([]);
  const [households, setHouseholds] = useState<HouseholdData[]>([]);
  const [vehicles, setVehicles] = useState<any[]>([]);

  // Source-add dialog (click on empty land)
  const [clickedLoc, setClickedLoc] = useState<ClickedLocation | null>(null);
  const [sourceDialog, setSourceDialog] = useState(false);
  const [addType, setAddType] = useState<'solar'>('solar');
  const [addName, setAddName] = useState('');

  // Building community dialog (click on OSM building)
  const [clickedBuilding, setClickedBuilding] = useState<ClickedBuilding | null>(null);
  const [buildingDialog, setBuildingDialog] = useState(false);
  const [buildingName, setBuildingName] = useState('');
  const [buildingType, setBuildingType] = useState<'household' | 'office'>('household');
  const [solarPanels, setSolarPanels] = useState(4);
  const [numPeople, setNumPeople] = useState(3);
  const [numEvs, setNumEvs] = useState(1);

  // Info popup for already-enrolled buildings
  const [infoBuilding, setInfoBuilding] = useState<HouseholdData | null>(null);
  const [infoDialog, setInfoDialog] = useState(false);
  const [infoBuildingFeature, setInfoBuildingFeature] = useState<ClickedBuilding | null>(null);

  const householdsRef = useRef<HouseholdData[]>([]);
  useEffect(() => { householdsRef.current = households; }, [households]);

  // Apply feature-state "enrolled: true" for all households with a known osm_feature_id.
  // setFeatureState is cached by MapLibre and reapplied automatically when tiles reload,
  // so this works for buildings outside the current viewport too.
  const applyEnrolledFeatureStates = useCallback((hhs: HouseholdData[]) => {
    const map = mapRef.current;
    if (!map || !mapReadyRef.current) return;
    const tileSource = buildingTileSourceRef.current;
    const tileSourceLayer = buildingTileSourceLayerRef.current;
    if (!tileSource || !tileSourceLayer) return;
    hhs.forEach(hh => {
      if (!hh.osm_feature_id) return;
      map.setFeatureState(
        { source: tileSource, sourceLayer: tileSourceLayer, id: hh.osm_feature_id },
        { enrolled: true },
      );
    });
  }, []);

  // Clear enrolled state for a single building
  const clearEnrolledFeatureState = useCallback((osmFeatureId: string) => {
    const map = mapRef.current;
    const tileSource = buildingTileSourceRef.current;
    const tileSourceLayer = buildingTileSourceLayerRef.current;
    if (!map || !tileSource || !tileSourceLayer) return;
    map.removeFeatureState(
      { source: tileSource, sourceLayer: tileSourceLayer, id: osmFeatureId },
      'enrolled',
    );
  }, []);

  // Initialize map once
  useEffect(() => {
    if (mapRef.current || !mapContainer.current) return;
    const m = new maplibregl.Map({
      container: mapContainer.current,
      style: MAP_STYLE,
      center: [4.35, 50.85],
      zoom: 14,
      pitch: 45,
      bearing: -10,
    });
    m.addControl(new maplibregl.NavigationControl(), 'top-right');

    m.on('style.load', () => {
      mapReadyRef.current = true;

      // Find fill-extrusion layers that represent individual buildings only.
      const layers = m.getStyle().layers;
      const extrusionLayers = layers.filter(
        l => l.type === 'fill-extrusion' && l.id.toLowerCase().includes('building')
      );
      buildingLayerIdsRef.current = extrusionLayers.map(l => l.id);

      // Detect the tile source and source-layer used by building extrusion layers.
      // In the liberty style all building layers share the same source, so we just take the first one.
      if (extrusionLayers.length > 0) {
        const firstLayer = extrusionLayers[0] as maplibregl.FillExtrusionLayerSpecification;
        const tileSource = firstLayer.source as string;
        const tileSourceLayer = firstLayer['source-layer'] ?? 'building';
        buildingTileSourceRef.current = tileSource;
        buildingTileSourceLayerRef.current = tileSourceLayer;

        // Add a separate highlight layer on top of the existing building layers.
        // Using a filter on feature-state means only enrolled buildings are drawn —
        // the original layers are left completely untouched.
        m.addLayer({
          id: 'enrolled-buildings-highlight',
          type: 'fill-extrusion',
          source: tileSource,
          'source-layer': tileSourceLayer,
          filter: ['boolean', ['feature-state', 'enrolled'], false],
          paint: {
            'fill-extrusion-color': '#FFD700',
            'fill-extrusion-height': ['coalesce', ['get', 'render_height'], ['get', 'height'], 6],
            'fill-extrusion-base': ['coalesce', ['get', 'render_min_height'], ['get', 'min_height'], 0],
            'fill-extrusion-opacity': 0.85,
          },
        });
      }

      // Apply enrolled states for already-loaded households
      applyEnrolledFeatureStates(householdsRef.current);

      // Cursor change on hover over buildings
      buildingLayerIdsRef.current.forEach(layerId => {
        m.on('mouseenter', layerId, () => { m.getCanvas().style.cursor = 'pointer'; });
        m.on('mouseleave', layerId, () => { m.getCanvas().style.cursor = ''; });
      });
    });

    // Re-apply feature states whenever tiles finish loading (e.g. after pan/zoom).
    // MapLibre caches them, but newly loaded tiles need the state reapplied.
    m.on('idle', () => {
      applyEnrolledFeatureStates(householdsRef.current);
    });

    m.on('click', (e) => {
      // Include the highlight overlay so clicking an enrolled (yellow) building still fires
      const layerIds = [...buildingLayerIdsRef.current, 'enrolled-buildings-highlight'].filter(id => m.getLayer(id));
      const buildingFeatures = layerIds.length > 0
        ? m.queryRenderedFeatures(e.point, { layers: layerIds })
        : [];

      // Keep only real 3D building polygons with stable IDs.
      const realBuildings = buildingFeatures.filter(isRealBuildingFeature);
      if (realBuildings.length > 0) {
        const feat = realBuildings[0];
        const featureId = feat.id!;
        const clickedBldg: ClickedBuilding = {
          featureId,
          source: feat.source,
          sourceLayer: feat.sourceLayer ?? 'building',
          lngLat: { lng: e.lngLat.lng, lat: e.lngLat.lat },
          buildingHeight: getFeatureHeight(feat.properties as Record<string, any>),
        };
        // Match by feature ID AND proximity — tile feature IDs are not globally unique,
        // so the same number can appear on different buildings in different tiles.
        const existingHH = householdsRef.current.find(hh => {
          if (hh.osm_feature_id !== String(featureId)) return false;
          if (hh.latitude == null || hh.longitude == null) return false;
          const dLat = (hh.latitude - e.lngLat.lat) * 111320;
          const dLng = (hh.longitude - e.lngLat.lng) * 111320 * Math.cos(e.lngLat.lat * Math.PI / 180);
          return Math.sqrt(dLat * dLat + dLng * dLng) < 150; // within 150 m
        });
        if (existingHH) {
          setInfoBuilding(existingHH);
          setInfoBuildingFeature(clickedBldg);
          setInfoDialog(true);
        } else {
          setClickedBuilding(clickedBldg);
          setBuildingName('');
          setBuildingType('household');
          setSolarPanels(4);
          setNumPeople(3);
          setNumEvs(1);
          setBuildingDialog(true);
        }
      } else {
        // Empty area — add solar source
        setClickedLoc({ longitude: e.lngLat.lng, latitude: e.lngLat.lat });
        setAddName('');
        setAddType('solar');
        setSourceDialog(true);
      }
    });

    mapRef.current = m;
    return () => {
      m.remove();
      mapRef.current = null;
      mapReadyRef.current = false;
      buildingTileSourceRef.current = null;
      buildingTileSourceLayerRef.current = null;
    };
  }, [applyEnrolledFeatureStates]);

  const loadData = useCallback(async () => {
    try {
      const [s, h, v] = await Promise.all([getSources(), getHouseholds(), getVehicles()]);
      setSources(s);
      setHouseholds(h);
      setVehicles(v);
      applyEnrolledFeatureStates(h);
    } catch (e) {
      console.error('Failed to load map data', e);
    }
  }, [applyEnrolledFeatureStates]);

  useEffect(() => {
    loadData();
    const id = setInterval(loadData, 10000);
    return () => clearInterval(id);
  }, [loadData]);

  // Re-apply feature states whenever households change
  useEffect(() => {
    applyEnrolledFeatureStates(households);
  }, [households, applyEnrolledFeatureStates]);

  // Expose delete callbacks for popup HTML buttons
  useEffect(() => {
    (window as any).__deleteSource = async (id: string) => { await deleteSource(id); loadData(); };
    (window as any).__deleteHousehold = async (id: string) => { await deleteHousehold(id); loadData(); };
  }, [loadData]);

  // Rebuild markers for sources, community rooftops, and vehicles
  useEffect(() => {
    if (!mapRef.current) return;
    markersRef.current.forEach(m => m.remove());
    markersRef.current = [];

    const intensity = solarIntensityFactor(50.85, 4.35, new Date());

    const addMarker = (lng: number, lat: number, emoji: string, bg: string, border: string, popupHtml: string) => {
      const el = Object.assign(document.createElement('div'), {
        textContent: emoji,
        style: `width:34px;height:34px;border-radius:50%;background:${bg};border:2px solid ${border};
                display:flex;align-items:center;justify-content:center;cursor:pointer;font-size:17px;
                box-shadow:0 2px 6px rgba(0,0,0,0.4);`,
      });
      const popup = new maplibregl.Popup({ offset: 25, maxWidth: '220px' }).setHTML(popupHtml);
      const marker = new maplibregl.Marker({ element: el })
        .setLngLat([lng, lat])
        .setPopup(popup)
        .addTo(mapRef.current!);
      markersRef.current.push(marker);
    };

    const addRooftopSolarMarker = (lng: number, lat: number, name: string, panels: number, altitudeMeters: number) => {
      const el = document.createElement('div');
      el.style.cssText = `
        width: 28px;
        height: 40px;
        cursor: pointer;
        transform: translateY(-2px);
        filter: drop-shadow(0 1px 4px rgba(0,0,0,0.45));
      `;
      el.innerHTML = `
        <svg viewBox="0 0 28 40" width="28" height="40" aria-hidden="true">
          <circle cx="14" cy="13" r="10" fill="#1565C0" stroke="#E3F2FD" stroke-width="2"/>
          <path d="M9 10h10v6H9z" fill="#90CAF9" stroke="#E3F2FD" stroke-width="1"/>
          <path d="M11 10v6M14 10v6M17 10v6M9 13h10" stroke="#E3F2FD" stroke-width="0.8"/>
          <path d="M14 37 L8 24 L20 24 Z" fill="#1565C0" stroke="#E3F2FD" stroke-width="2"/>
        </svg>
      `;
      const popup = new maplibregl.Popup({ offset: 20, maxWidth: '220px' }).setHTML(`
        <b>${name}</b><br/>
        <small>Community rooftop • ${panels} solar panel${panels === 1 ? '' : 's'}</small>
      `);
      const marker = new maplibregl.Marker({ element: el, anchor: 'bottom', altitude: altitudeMeters + 1 })
        .setLngLat([lng, lat])
        .setPopup(popup)
        .addTo(mapRef.current!);
      markersRef.current.push(marker);
    };

    sources.filter(s => s.source_type === 'solar').forEach(s => {
      const bg = intensity > 0 ? `rgba(255,200,0,${(0.4 + intensity * 0.6).toFixed(2)})` : 'rgba(120,120,120,0.5)';
      addMarker(s.longitude, s.latitude, '☀', bg, '#f0c040', `
        <b>${s.name || s.source_id}</b><br/>
        <small>${s.current_value != null ? s.current_value.toFixed(2) + ' kW' : 'No data'}</small><br/>
        <button onclick="window.__deleteSource('${s.source_id}')"
          style="margin-top:4px;color:red;border:1px solid red;background:none;cursor:pointer;padding:2px 8px;border-radius:4px;font-size:11px">
          Remove
        </button>`);
    });

    households
      .filter(hh => hh.latitude != null && hh.longitude != null && !!hh.osm_feature_id)
      .forEach(hh => {
        // Use a sensible default altitude for the rooftop marker (typical 2-story building ~8m)
        addRooftopSolarMarker(hh.longitude!, hh.latitude!, hh.name, hh.solar_panels ?? 0, 8);
      });

    vehicles.filter(ev => ev.latitude && ev.longitude).forEach(ev => {
      const isHome = ev.status === 'home';
      const bg = isHome ? 'rgba(33,150,243,0.7)' : 'rgba(255,152,0,0.7)';
      const border = isHome ? '#2196f3' : '#ff9800';
      const soc = ev.capacity_kwh > 0 ? (ev.soc_kwh / ev.capacity_kwh * 100).toFixed(0) : 0;
      addMarker(ev.longitude, ev.latitude, '🚗', bg, border, `
        <b>${ev.name}</b> (${ev.status})<br/>
        <small>SOC: ${ev.soc_kwh.toFixed(1)}/${ev.capacity_kwh} kWh (${soc}%)</small>`);
    });
  }, [sources, households, vehicles]);

  // Add a source (solar/wind) at clicked location
  const handleAddSource = async () => {
    if (!clickedLoc) return;
    try {
      await createSource({ source_type: addType, latitude: clickedLoc.latitude, longitude: clickedLoc.longitude, name: addName || undefined });
      setSourceDialog(false);
      setClickedLoc(null);
      loadData();
    } catch (e) {
      console.error('Failed to add source', e);
    }
  };

  // Enroll a building in the community
  const handleAddBuilding = async () => {
    if (!clickedBuilding) return;
    try {
      const hh = await createHousehold({
        name: buildingName || `Building ${String(clickedBuilding.featureId).slice(-4)}`,
        latitude: clickedBuilding.lngLat.lat,
        longitude: clickedBuilding.lngLat.lng,
        solar_panels: solarPanels,
        building_type: buildingType,
        num_people: numPeople,
        num_evs: numEvs,
        osm_feature_id: String(clickedBuilding.featureId),
      });

      // Auto-create EVs
      for (let i = 0; i < numEvs; i++) {
        await createVehicle({
          household_id: hh.household_id,
          name: `${hh.name} EV ${i + 1}`,
          ...DEFAULT_EV,
        });
      }

      // Immediately highlight building via feature-state (no geometry capture needed)
      const tileSource = buildingTileSourceRef.current;
      const tileSourceLayer = buildingTileSourceLayerRef.current;
      if (mapRef.current && tileSource && tileSourceLayer) {
        mapRef.current.setFeatureState(
          { source: tileSource, sourceLayer: tileSourceLayer, id: String(clickedBuilding.featureId) },
          { enrolled: true },
        );
      }

      setBuildingDialog(false);
      setClickedBuilding(null);
      loadData();
    } catch (e) {
      console.error('Failed to add building', e);
    }
  };

  // Remove a building from the community
  const handleRemoveBuilding = async () => {
    if (!infoBuilding) return;
    try {
      await deleteHousehold(infoBuilding.household_id);

      // Clear enrolled feature-state
      if (infoBuilding.osm_feature_id) {
        clearEnrolledFeatureState(infoBuilding.osm_feature_id);
      }

      setInfoDialog(false);
      setInfoBuilding(null);
      loadData();
    } catch (e) {
      console.error('Failed to remove building', e);
    }
  };

  return (
    <Box sx={{ width: '100%', height: '100%', position: 'relative' }}>
      <div ref={mapContainer} style={{ width: '100%', height: '100%' }} />

      {/* Source add dialog (solar) */}
      <Dialog open={sourceDialog} onClose={() => setSourceDialog(false)} maxWidth="xs" fullWidth>
        <DialogTitle>Add Energy Source</DialogTitle>
        <DialogContent>
          <FormControl fullWidth sx={{ mb: 2, mt: 1 }}>
            <InputLabel>Type</InputLabel>
            <Select value={addType} onChange={e => setAddType(e.target.value as any)} label="Type">
              <MenuItem value="solar">Solar Panel</MenuItem>
            </Select>
          </FormControl>
          <TextField label="Name (optional)" value={addName} onChange={e => setAddName(e.target.value)} fullWidth />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSourceDialog(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleAddSource}>Add</Button>
        </DialogActions>
      </Dialog>

      {/* Building community enrollment dialog */}
      <Dialog open={buildingDialog} onClose={() => setBuildingDialog(false)} maxWidth="xs" fullWidth>
        <DialogTitle>Add Building to Community</DialogTitle>
        <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
          <TextField
            label="Building name (optional)"
            value={buildingName}
            onChange={e => setBuildingName(e.target.value)}
            fullWidth
          />
          <Divider />
          <FormControl fullWidth>
            <InputLabel>Building type</InputLabel>
            <Select value={buildingType} onChange={e => setBuildingType(e.target.value as any)} label="Building type">
              <MenuItem value="household">Household / Residential</MenuItem>
              <MenuItem value="office">Office / Commercial</MenuItem>
            </Select>
          </FormControl>
          <TextField
            label="Number of people"
            type="number"
            value={numPeople}
            onChange={e => setNumPeople(Math.max(1, parseInt(e.target.value) || 1))}
            helperText="Acts as a consumption multiplier"
            fullWidth
            inputProps={{ min: 1 }}
          />
          <Divider />
          <TextField
            label="Solar panels"
            type="number"
            value={solarPanels}
            onChange={e => setSolarPanels(Math.max(0, parseInt(e.target.value) || 0))}
            helperText="Acts as a production multiplier"
            fullWidth
            inputProps={{ min: 0 }}
          />
          <TextField
            label="Electric cars"
            type="number"
            value={numEvs}
            onChange={e => setNumEvs(Math.max(0, parseInt(e.target.value) || 0))}
            helperText="Each car = 60 kWh battery (V2G capable)"
            fullWidth
            inputProps={{ min: 0 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setBuildingDialog(false)}>Cancel</Button>
          <Button variant="contained" color="warning" onClick={handleAddBuilding}>
            Add to Community
          </Button>
        </DialogActions>
      </Dialog>

      {/* Info dialog for already-enrolled buildings */}
      <Dialog open={infoDialog} onClose={() => setInfoDialog(false)} maxWidth="xs" fullWidth>
        <DialogTitle>
          {infoBuilding?.name}
          <Chip
            label={infoBuilding?.building_type}
            size="small"
            sx={{ ml: 1, textTransform: 'capitalize' }}
          />
        </DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
            <Typography variant="body2">☀ Solar panels: <b>{infoBuilding?.solar_panels}</b></Typography>
            <Typography variant="body2">👥 People: <b>{infoBuilding?.num_people}</b></Typography>
            <Typography variant="body2">🚗 Electric cars: <b>{infoBuilding?.num_evs}</b></Typography>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setInfoDialog(false)}>Close</Button>
          <Button variant="outlined" color="error" onClick={handleRemoveBuilding}>
            Remove from Community
          </Button>
        </DialogActions>
      </Dialog>

      {/* Map legend */}
      <Box sx={{
        position: 'absolute', bottom: 16, left: 16, zIndex: 1,
        bgcolor: 'rgba(0,0,0,0.72)', borderRadius: 2, p: 1.5,
        display: 'flex', flexDirection: 'column', gap: 0.4,
        pointerEvents: 'none',
      }}>
        <Typography variant="caption" color="white" fontWeight="bold">Click to interact</Typography>
        {[['🏗', 'Building → Add to Community'], ['☀', 'Empty → Add Solar']].map(([icon, label]) => (
          <Typography key={label} variant="caption" color="white">{icon} {label}</Typography>
        ))}
        <Divider sx={{ borderColor: 'rgba(255,255,255,0.2)', my: 0.5 }} />
        {[['🔆', 'Community rooftop solar'], ['☀', 'Solar'], ['🚗', 'EV']].map(([icon, label]) => (
          <Typography key={label} variant="caption" color="white">{icon} {label}</Typography>
        ))}
      </Box>
    </Box>
  );
};

export default Map3D;
