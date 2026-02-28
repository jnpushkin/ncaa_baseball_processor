"use client";

import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { ScheduleGame, SiteData } from "@/types";
import { convertEasternToLocal } from "@/lib/timezone";

interface ScheduleMapProps {
  games: ScheduleGame[];
  data: SiteData;
}

export default function ScheduleMap({ games, data }: ScheduleMapProps) {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstance = useRef<L.Map | null>(null);
  const markersRef = useRef<L.Marker[]>([]);

  useEffect(() => {
    if (!mapRef.current || mapInstance.current) return;
    mapInstance.current = L.map(mapRef.current).setView([39.5, -98.35], 4);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 18,
      attribution: "&copy; OpenStreetMap contributors",
    }).addTo(mapInstance.current);
    return () => {
      if (mapInstance.current) {
        mapInstance.current.remove();
        mapInstance.current = null;
      }
    };
  }, []);

  useEffect(() => {
    if (!mapInstance.current) return;
    markersRef.current.forEach((m) => m.remove());
    markersRef.current = [];

    const resolveLocation = (g: ScheduleGame) => {
      const venue = g.venue || {};
      const city = venue.city;
      const state = venue.state;
      if (city && state) {
        const venueLookup = data.venueCityCoords || {};
        const key = `${city},${state}`;
        if (venueLookup[key]) return venueLookup[key];
      }
      const name = g.home_team?.name;
      if (!name) return null;
      if (data.stadiumLocations?.[name]) return data.stadiumLocations[name];
      for (const info of Object.values(data.milbStadiumLocations || {})) {
        if (info.team === name) return info;
      }
      for (const info of Object.values(data.partnerStadiumLocations || {})) {
        if (info.team === name) return info;
      }
      return null;
    };

    const venues: Record<
      string,
      {
        lat: number;
        lng: number;
        name: string;
        city?: string;
        state?: string;
        games: ScheduleGame[];
      }
    > = {};

    games.forEach((g) => {
      const loc = resolveLocation(g);
      if (!loc || !loc.lat || !loc.lng) return;
      const vKey = `${loc.lat},${loc.lng}`;
      const venueName =
        g.venue?.name || g.venue?.city || g.home_team?.name || "";
      if (!venues[vKey])
        venues[vKey] = {
          lat: loc.lat,
          lng: loc.lng,
          name: venueName,
          city: g.venue?.city,
          state: g.venue?.state,
          games: [],
        };
      venues[vKey].games.push(g);
    });

    Object.values(venues).forEach((v) => {
      const count = v.games.length;
      const icon = L.divIcon({
        className: "schedule-marker",
        html: `<div style="width:${count > 1 ? 22 : 16}px;height:${count > 1 ? 22 : 16}px;background:#28a745;border-radius:50%;border:2px solid white;box-shadow:0 2px 4px rgba(0,0,0,0.3);display:flex;align-items:center;justify-content:center;color:white;font-size:${count > 1 ? "10" : "0"}px;font-weight:700;">${count > 1 ? count : ""}</div>`,
        iconSize: [count > 1 ? 22 : 16, count > 1 ? 22 : 16],
        iconAnchor: [count > 1 ? 11 : 8, count > 1 ? 11 : 8],
      });

      const locationLabel =
        v.name +
        (v.city ? ` — ${v.city}${v.state ? ", " + v.state : ""}` : "");
      const popupLines = v.games
        .map((g) => {
          const away = g.away_team?.name || "TBD";
          const home = g.home_team?.name || "TBD";
          const time =
            convertEasternToLocal(g.time_detail, g.date) ||
            g.time_detail ||
            "TBD";
          return `<div style="margin:4px 0;font-size:12px;"><strong>${away} @ ${home}</strong><br/>${g.date_display || ""} - ${time}</div>`;
        })
        .join("");

      const marker = L.marker([v.lat, v.lng], { icon })
        .bindPopup(
          `<div style="max-height:200px;overflow-y:auto;"><strong>${locationLabel}</strong><br/>${count} game${count > 1 ? "s" : ""}<hr style="margin:4px 0;"/>${popupLines}</div>`
        )
        .addTo(mapInstance.current!);
      markersRef.current.push(marker);
    });
  }, [games, data]);

  return (
    <div
      ref={mapRef}
      style={{
        height: "450px",
        borderRadius: "8px",
        border: "1px solid #ddd",
        marginBottom: "16px",
      }}
    ></div>
  );
}
