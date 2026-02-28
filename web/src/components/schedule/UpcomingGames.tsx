"use client";

import { useState, useMemo } from "react";
import dynamic from "next/dynamic";
import type { ScheduleGame, SiteData } from "@/types";
import { convertEasternToLocal } from "@/lib/timezone";

const ScheduleMap = dynamic(() => import("@/components/maps/ScheduleMap"), {
  ssr: false,
});

interface UpcomingGamesProps {
  games: ScheduleGame[];
  data: SiteData;
}

export default function UpcomingGames({ games, data }: UpcomingGamesProps) {
  const [statusFilter, setStatusFilter] = useState("scheduled");
  const [searchText, setSearchText] = useState("");
  const [showMap, setShowMap] = useState(false);

  const todayStr = useMemo(() => new Date().toISOString().slice(0, 10), []);
  const weekLaterStr = useMemo(() => {
    const d = new Date();
    d.setDate(d.getDate() + 7);
    return d.toISOString().slice(0, 10);
  }, []);
  const [startDate, setStartDate] = useState(todayStr);
  const [endDate, setEndDate] = useState(weekLaterStr);

  const statusOptions = ["All", "scheduled", "in_progress", "final", "canceled", "postponed"];

  const setQuickFilter = (preset: string) => {
    const now = new Date();
    const toISO = (d: Date) => d.toISOString().slice(0, 10);
    if (preset === "today") {
      setStartDate(toISO(now));
      setEndDate(toISO(now));
    } else if (preset === "week") {
      setStartDate(toISO(now));
      const end = new Date(now);
      end.setDate(end.getDate() + 6);
      setEndDate(toISO(end));
    } else if (preset === "nextweek") {
      const start = new Date(now);
      start.setDate(start.getDate() + (7 - start.getDay()));
      const end = new Date(start);
      end.setDate(end.getDate() + 6);
      setStartDate(toISO(start));
      setEndDate(toISO(end));
    } else if (preset === "month") {
      setStartDate(toISO(now));
      const end = new Date(now.getFullYear(), now.getMonth() + 1, 0);
      setEndDate(toISO(end));
    } else if (preset === "all") {
      setStartDate("");
      setEndDate("");
    }
  };

  const filtered = useMemo(() => {
    return games.filter((g) => {
      if (statusFilter !== "All" && g.status !== statusFilter) return false;
      if (startDate || endDate) {
        const gameDate = (g.date || "").slice(0, 10);
        if (!gameDate) return false;
        if (startDate && gameDate < startDate) return false;
        if (endDate && gameDate > endDate) return false;
      }
      if (searchText) {
        const s = searchText.toLowerCase();
        const home = (g.home_team?.name || "").toLowerCase();
        const away = (g.away_team?.name || "").toLowerCase();
        const venue = (g.venue?.name || "").toLowerCase();
        const city = (g.venue?.city || "").toLowerCase();
        if (!home.includes(s) && !away.includes(s) && !venue.includes(s) && !city.includes(s))
          return false;
      }
      return true;
    });
  }, [games, statusFilter, startDate, endDate, searchText]);

  const grouped = useMemo(() => {
    const groups: Record<string, ScheduleGame[]> = {};
    filtered.forEach((g) => {
      const key = g.date_display || "Unknown";
      if (!groups[key]) groups[key] = [];
      groups[key].push(g);
    });
    return groups;
  }, [filtered]);

  const statusColors: Record<string, string> = {
    scheduled: "#28a745",
    in_progress: "#ff6b35",
    final: "#666",
    canceled: "#dc3545",
    postponed: "#ffc107",
  };

  const getTeamLogo = (team: { name?: string; logo_url?: string }) => {
    if (team.logo_url) return team.logo_url;
    const espnId = data.ncaaTeamLogos?.[team.name || ""];
    if (espnId)
      return `https://a.espncdn.com/i/teamlogos/ncaa/500/${espnId}.png`;
    return "";
  };

  const activeQuick = useMemo((): string => {
    if (!startDate && !endDate) return "all";
    const now = new Date();
    const toISO = (d: Date) => d.toISOString().slice(0, 10);
    if (startDate === toISO(now) && endDate === toISO(now)) return "today";
    const weekEnd = new Date(now);
    weekEnd.setDate(weekEnd.getDate() + 6);
    if (startDate === toISO(now) && endDate === toISO(weekEnd)) return "week";
    const monthEnd = new Date(now.getFullYear(), now.getMonth() + 1, 0);
    if (startDate === toISO(now) && endDate === toISO(monthEnd)) return "month";
    return "";
  }, [startDate, endDate]);

  return (
    <div>
      <div className="schedule-filter-bar">
        <input
          type="text"
          placeholder="Search teams, venues, cities..."
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          className="filter-input"
        />
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="filter-select"
        >
          {statusOptions.map((s) => (
            <option key={s} value={s}>
              {s === "All" ? "All Statuses" : s.charAt(0).toUpperCase() + s.slice(1).replace("_", " ")}
            </option>
          ))}
        </select>
        <span className="filter-count">{filtered.length} games</span>
        <button
          onClick={() => setShowMap(!showMap)}
          className={`toggle-btn${showMap ? " active" : ""}`}
        >
          {showMap ? "Hide Map" : "Show Map"}
        </button>
      </div>

      <div className="schedule-date-bar">
        <span className="schedule-date-label">Dates:</span>
        <input
          type="date"
          value={startDate}
          onChange={(e) => setStartDate(e.target.value)}
          className="schedule-date-input"
        />
        <span className="schedule-date-sep">to</span>
        <input
          type="date"
          value={endDate}
          onChange={(e) => setEndDate(e.target.value)}
          className="schedule-date-input"
        />
        {[
          { key: "today", label: "Today" },
          { key: "week", label: "This Week" },
          { key: "nextweek", label: "Next Week" },
          { key: "month", label: "This Month" },
          { key: "all", label: "Full Season" },
        ].map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setQuickFilter(key)}
            className={`pill-btn${activeQuick === key ? " active" : ""}`}
          >
            {label}
          </button>
        ))}
      </div>

      {showMap && <ScheduleMap games={filtered} data={data} />}

      {Object.entries(grouped).map(([dateLabel, dateGames]) => (
        <div key={dateLabel} className="schedule-day-group">
          <h3 className="schedule-day-header">
            {dateLabel} ({dateGames.length} games)
          </h3>
          <div className="schedule-cards">
            {dateGames.map((game, idx) => (
              <div key={game.d1bb_key || idx} className="game-card">
                <div className="game-card-top">
                  <span
                    className="game-card-status"
                    style={{ color: statusColors[game.status] || "#666" }}
                  >
                    {game.status === "scheduled"
                      ? convertEasternToLocal(game.time_detail, game.date) || game.time_detail || "TBD"
                      : game.status.replace("_", " ")}
                  </span>
                  {game.venue?.name && (
                    <span className="game-card-venue-name">{game.venue.name}</span>
                  )}
                </div>

                <div className="game-card-teams">
                  <div className="game-card-team">
                    {getTeamLogo(game.away_team) && (
                      <img src={getTeamLogo(game.away_team)} alt="" className="game-card-team-logo" />
                    )}
                    <span className="game-card-team-name">
                      {game.away_team?.rank ? `#${game.away_team.rank} ` : ""}
                      {game.away_team?.name || "TBD"}
                    </span>
                    {game.away_team?.record && (
                      <span className="game-card-team-record">{game.away_team.record}</span>
                    )}
                  </div>
                  <div className="game-card-team">
                    {getTeamLogo(game.home_team) && (
                      <img src={getTeamLogo(game.home_team)} alt="" className="game-card-team-logo" />
                    )}
                    <span className="game-card-team-name">
                      {game.home_team?.rank ? `#${game.home_team.rank} ` : ""}
                      {game.home_team?.name || "TBD"}
                    </span>
                    {game.home_team?.record && (
                      <span className="game-card-team-record">{game.home_team.record}</span>
                    )}
                  </div>
                </div>

                {game.venue?.city && (
                  <div className="game-card-location">
                    {game.venue.city}
                    {game.venue.state ? `, ${game.venue.state}` : ""}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      ))}

      {filtered.length === 0 && (
        <div className="empty-state">
          No games match your filters. Try adjusting the search or filters above.
        </div>
      )}
    </div>
  );
}
