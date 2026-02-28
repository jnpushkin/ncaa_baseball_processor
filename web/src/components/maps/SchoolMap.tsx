"use client";

import { useState, useEffect, useRef, useMemo } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type {
  SiteData,
  StadiumLocation,
  MilbStadiumLocation,
  PartnerStadiumLocation,
  ChecklistConference,
  MilbChecklistLevel,
} from "@/types";

interface SchoolMapProps {
  stadiums: Record<string, StadiumLocation>;
  teamsSeenHome: string[];
  teamsSeenAway: string[];
  checklist: Record<string, ChecklistConference>;
  milbStadiums: Record<string, MilbStadiumLocation>;
  milbVenuesVisited: string[];
  partnerStadiums: Record<string, PartnerStadiumLocation>;
  partnerVenuesVisited: string[];
  data: SiteData;
}

export default function SchoolMap({
  stadiums,
  teamsSeenHome,
  teamsSeenAway,
  checklist,
  milbStadiums,
  milbVenuesVisited,
  partnerStadiums,
  partnerVenuesVisited,
  data,
}: SchoolMapProps) {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstance = useRef<L.Map | null>(null);
  const markersRef = useRef<L.Marker[]>([]);
  const [selectedConf, setSelectedConf] = useState("All");
  const [filter, setFilter] = useState("all");
  const [showMilb, setShowMilb] = useState(true);
  const [showPartner, setShowPartner] = useState(true);

  const hasMilbData = milbStadiums && Object.keys(milbStadiums).length > 0;
  const hasPartnerData =
    partnerStadiums && Object.keys(partnerStadiums).length > 0;

  const conferences = useMemo(() => {
    return ["All", ...Object.keys(checklist).sort()];
  }, [checklist]);

  const getTeamDisplayName = (team: string) => {
    if (!team) return team;
    const lower = team.toLowerCase();
    const nicknames = data.ncaaTeamNicknames || {};
    let proper = team;
    let nickname = "";
    for (const [k, v] of Object.entries(nicknames)) {
      if (k.toLowerCase() === lower) {
        proper = k;
        nickname = v;
        break;
      }
    }
    return nickname ? `${proper} ${nickname}` : team;
  };

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

    let teamsToShow: string[] = [];
    if (selectedConf === "All") {
      Object.values(checklist).forEach((c) => {
        teamsToShow.push(...c.teams);
      });
    } else if (selectedConf === "MiLB") {
      teamsToShow = [];
    } else if (checklist[selectedConf]) {
      teamsToShow = checklist[selectedConf].teams;
    }

    if (filter === "seen") {
      teamsToShow = teamsToShow.filter(
        (t) => teamsSeenHome.includes(t) || teamsSeenAway.includes(t)
      );
    } else if (filter === "visited") {
      teamsToShow = teamsToShow.filter((t) => teamsSeenHome.includes(t));
    } else if (filter === "unseen") {
      teamsToShow = teamsToShow.filter(
        (t) => !teamsSeenHome.includes(t) && !teamsSeenAway.includes(t)
      );
    }

    // NCAA markers
    teamsToShow.forEach((team) => {
      const info = stadiums[team];
      if (!info) return;
      const isHome = teamsSeenHome.includes(team);
      const isAway = teamsSeenAway.includes(team);
      const color = isHome ? "#28a745" : isAway ? "#007bff" : "#999";

      const icon = L.divIcon({
        className: "custom-marker",
        html: `<div style="width: 14px; height: 14px; background: ${color}; border-radius: 50%; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);"></div>`,
        iconSize: [14, 14],
        iconAnchor: [7, 7],
      });

      const marker = L.marker([info.lat, info.lng], { icon })
        .bindPopup(
          `<strong>${team}</strong><br>${info.stadium}<br><em>${isHome ? "Visited" : isAway ? "Seen (Away)" : "Not Seen"}</em>`
        )
        .addTo(mapInstance.current!);
      markersRef.current.push(marker);
    });

    // MiLB markers
    if (showMilb && milbStadiums && (selectedConf === "All" || selectedConf === "MiLB")) {
      Object.entries(milbStadiums).forEach(([venueName, info]) => {
        const isVisited = milbVenuesVisited?.includes(venueName);
        if (filter === "visited" && !isVisited) return;
        if (filter === "unseen" && isVisited) return;
        if (filter === "seen" && !isVisited) return;

        const opacity = isVisited ? 1.0 : 0.5;
        const size = isVisited ? 28 : 22;
        const logo = (data.localLogos && data.localLogos[info.team]) || info.logo;

        const icon = L.divIcon({
          className: "logo-marker",
          html: `<div style="width: ${size}px; height: ${size}px; opacity: ${opacity}; background: white; border-radius: 50%; padding: 2px; box-shadow: 0 2px 6px rgba(0,0,0,0.3); ${isVisited ? "border: 2px solid #ff6b35;" : ""} display: flex; align-items: center; justify-content: center;">
            <img src="${logo}" style="width: 100%; height: 100%; object-fit: contain;" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';" />
            <span style="display: none; font-weight: bold; font-size: ${size * 0.5}px; color: #333; align-items: center; justify-content: center; width: 100%; height: 100%;">&#9918;</span>
          </div>`,
          iconSize: [size, size],
          iconAnchor: [size / 2, size / 2],
        });

        const displayName = getTeamDisplayName(info.team);
        const marker = L.marker([info.lat, info.lng], { icon })
          .bindPopup(
            `<div style="text-align:center;"><img src="${logo}" style="width:50px;height:50px;margin-bottom:8px;" onerror="this.outerHTML='<span style=\\'font-size:40px;\\'>&#9918;</span>'" /><br><strong>${displayName}</strong><br>${venueName}<br><em>MiLB (${info.level}) - ${isVisited ? "Visited" : "Not Visited"}</em></div>`
          )
          .addTo(mapInstance.current!);
        markersRef.current.push(marker);
      });
    }

    // Partner markers
    if (showPartner && partnerStadiums && (selectedConf === "All" || selectedConf === "Partner")) {
      Object.entries(partnerStadiums).forEach(([stadiumName, info]) => {
        const isVisited = partnerVenuesVisited?.includes(stadiumName);
        if (filter === "visited" && !isVisited) return;
        if (filter === "unseen" && isVisited) return;
        if (filter === "seen" && !isVisited) return;

        const opacity = isVisited ? 1.0 : 0.5;
        const size = isVisited ? 26 : 20;
        const logo = (data.localLogos && data.localLogos[info.team]) || info.logo;

        const icon = L.divIcon({
          className: "logo-marker",
          html: `<div style="width: ${size}px; height: ${size}px; opacity: ${opacity}; background: white; border-radius: 50%; padding: 2px; box-shadow: 0 2px 6px rgba(0,0,0,0.3); ${isVisited ? "border: 2px solid #9c27b0;" : ""} display: flex; align-items: center; justify-content: center;">
            <img src="${logo}" style="width: 100%; height: 100%; object-fit: contain;" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';" />
            <span style="display: none; font-weight: bold; font-size: ${size * 0.5}px; color: #333; align-items: center; justify-content: center; width: 100%; height: 100%;">&#9918;</span>
          </div>`,
          iconSize: [size, size],
          iconAnchor: [size / 2, size / 2],
        });

        const displayName = getTeamDisplayName(info.team);
        const marker = L.marker([info.lat, info.lng], { icon })
          .bindPopup(
            `<div style="text-align:center;"><img src="${logo}" style="width:50px;height:50px;margin-bottom:8px;" onerror="this.outerHTML='<span style=\\'font-size:40px;\\'>&#9918;</span>'" /><br><strong>${displayName}</strong><br>${stadiumName}<br><em>${info.league} - ${isVisited ? "Visited" : "Not Visited"}</em></div>`
          )
          .addTo(mapInstance.current!);
        markersRef.current.push(marker);
      });
    }
  }, [
    stadiums, teamsSeenHome, teamsSeenAway, selectedConf, filter, checklist,
    showMilb, milbStadiums, milbVenuesVisited, showPartner, partnerStadiums,
    partnerVenuesVisited, data,
  ]);

  const levelColors = data.levelColors || {};

  return (
    <div className="panel">
      <div className="panel-header">
        <h2>Stadium Map</h2>
      </div>
      <div style={{ padding: "16px" }}>
        <div style={{ marginBottom: "16px", display: "flex", gap: "12px", flexWrap: "wrap", alignItems: "center" }}>
          <select
            className="search-box"
            style={{ width: "auto", minWidth: "150px", margin: 0 }}
            value={selectedConf}
            onChange={(e) => setSelectedConf(e.target.value)}
          >
            {conferences.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
            {hasMilbData && <option value="MiLB">MiLB Only</option>}
          </select>
          <select
            className="search-box"
            style={{ width: "auto", minWidth: "150px", margin: 0 }}
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          >
            <option value="all">All Venues</option>
            <option value="seen">Seen</option>
            <option value="visited">Visited</option>
            <option value="unseen">Not Seen</option>
          </select>
          {hasMilbData && (
            <label style={{ display: "flex", alignItems: "center", gap: "6px", cursor: "pointer" }}>
              <input type="checkbox" checked={showMilb} onChange={(e) => setShowMilb(e.target.checked)} />
              Show MiLB
            </label>
          )}
          {hasPartnerData && (
            <label style={{ display: "flex", alignItems: "center", gap: "6px", cursor: "pointer" }}>
              <input type="checkbox" checked={showPartner} onChange={(e) => setShowPartner(e.target.checked)} />
              Show Partner
            </label>
          )}
        </div>
        <div ref={mapRef} style={{ height: "500px", borderRadius: "8px", border: "1px solid #ddd" }}></div>
        <div style={{ marginTop: "12px", display: "flex", gap: "16px", fontSize: "14px", color: "#666", flexWrap: "wrap", alignItems: "center" }}>
          <span>
            <span style={{ display: "inline-block", width: "12px", height: "12px", borderRadius: "50%", background: "#28a745", marginRight: "4px" }}></span>
            NCAA Visited
          </span>
          <span>
            <span style={{ display: "inline-block", width: "12px", height: "12px", borderRadius: "50%", background: "#007bff", marginRight: "4px" }}></span>
            NCAA Seen (Away)
          </span>
          <span>
            <span style={{ display: "inline-block", width: "12px", height: "12px", borderRadius: "50%", background: "#999", marginRight: "4px" }}></span>
            NCAA Not Seen
          </span>
          {hasMilbData && (
            <span>
              <span style={{ display: "inline-block", width: "16px", height: "16px", borderRadius: "50%", border: "2px solid #ff6b35", background: "white", marginRight: "4px" }}></span>
              MiLB Visited (logo)
            </span>
          )}
          {hasMilbData && (
            <span>
              <span style={{ display: "inline-block", width: "14px", height: "14px", borderRadius: "50%", background: "white", opacity: 0.5, marginRight: "4px", boxShadow: "0 1px 3px rgba(0,0,0,0.2)" }}></span>
              MiLB (logo)
            </span>
          )}
          {hasPartnerData && (
            <span>
              <span style={{ display: "inline-block", width: "14px", height: "14px", borderRadius: "50%", border: "2px solid #9c27b0", background: "white", marginRight: "4px" }}></span>
              Partner Visited (logo)
            </span>
          )}
          {hasPartnerData && (
            <span>
              <span style={{ display: "inline-block", width: "12px", height: "12px", borderRadius: "50%", background: "white", opacity: 0.5, marginRight: "4px", boxShadow: "0 1px 3px rgba(0,0,0,0.2)" }}></span>
              Partner (logo)
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
