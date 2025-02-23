// SourceMap.tsx
import React from 'react';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';

type Source = {
  source_id: string;
  type: 'solar' | 'wind';
  lat: number;
  lon: number;
};

type SourceMapProps = {
  sources: Source[];
};

const SourceMap: React.FC<SourceMapProps> = ({ sources }) => {
  // Set an initial center. This could be dynamically calculated based on your sources.
  const centerPosition: [number, number] = [20, 0];

  return (
    <MapContainer center={centerPosition} zoom={2} style={{ height: '400px', width: '100%' }}>
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {sources.map((source) => (
        <Marker key={source.source_id} position={[source.lat, source.lon]}>
          <Popup>
            <strong>{source.type.charAt(0).toUpperCase() + source.type.slice(1)} Source</strong>
            <br />
            ID: {source.source_id}
          </Popup>
        </Marker>
      ))}
    </MapContainer>
  );
};

export default SourceMap;
