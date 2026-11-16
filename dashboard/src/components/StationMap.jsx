// Map of stations with pending points (free OpenStreetMap tiles through Leaflet).
import L from "leaflet";
import { MapContainer, Marker, TileLayer, Tooltip } from "react-leaflet";
import { plural } from "../format.js";

function pin(station) {
  return L.divIcon({
    className: "",
    html: `<span class="pin${station.overdue ? " pin-overdue" : ""}">${station.pending}</span>`,
    iconSize: [34, 34],
    iconAnchor: [17, 17],
  });
}

function describe(s) {
  return `${s.name}: ${s.pending} pending${s.overdue ? `, ${s.overdue} overdue` : ""}`;
}

// stations: [{ name, latitude, longitude, pending, overdue }]
export default function StationMap({ stations, onPick }) {
  const view = stations.length
    ? {
        bounds: L.latLngBounds(stations.map((s) => [s.latitude, s.longitude])),
        boundsOptions: { padding: [22, 22], maxZoom: 8 },
      }
    : { center: [27.3, 74.5], zoom: 6 };

  return (
    <MapContainer className="map" scrollWheelZoom={false} {...view}>
      <TileLayer
        attribution="&copy; OpenStreetMap contributors"
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {stations.map((s) => (
        <Marker key={s.name} position={[s.latitude, s.longitude]} icon={pin(s)} alt={describe(s)}
                eventHandlers={{ click: () => onPick(s.name) }}>
          <Tooltip direction="top" offset={[0, -16]}>
            <strong>{s.name}</strong>
            <br />
            {plural(s.pending, "pending point")}
            {s.overdue > 0 && `, ${s.overdue} overdue`}
          </Tooltip>
        </Marker>
      ))}
    </MapContainer>
  );
}
