"use client";

/* eslint-disable @next/next/no-img-element */

import { useEffect, useState, useMemo } from "react";
import dynamic from "next/dynamic";
import type { ScheduleGame, SiteData } from "@/types";
import { fetchJsonWithRetry } from "@/lib/fetchJson";
import { convertEasternToLocal } from "@/lib/timezone";

const ScheduleMap = dynamic(() => import("@/components/maps/ScheduleMap"), {
  ssr: false,
});

interface UpcomingGamesProps {
  games: ScheduleGame[];
  data: SiteData;
}

type DateRangeOverride = {
  start: string;
  end: string;
} | null;

const SCHEDULE_PAGE_SIZE = 250;

function toISODate(date: Date) {
  return date.toISOString().slice(0, 10);
}

function addDays(dateString: string, days: number) {
  const date = new Date(`${dateString}T00:00:00`);
  date.setDate(date.getDate() + days);
  return toISODate(date);
}

function deriveDefaultRange(scheduleDates: string[], today: string) {
  const weekEnd = addDays(today, 6);
  if (!scheduleDates.length) return { start: today, end: weekEnd, mode: "current" };

  const first = scheduleDates[0];
  const last = scheduleDates[scheduleDates.length - 1];
  const hasCurrentWindow = scheduleDates.some((date) => date >= today && date <= weekEnd);
  if (hasCurrentWindow) return { start: today, end: weekEnd, mode: "current" };

  const nextAvailable = scheduleDates.find((date) => date >= today);
  if (nextAvailable) {
    return { start: nextAvailable, end: addDays(nextAvailable, 6), mode: "nextAvailable" };
  }

  return { start: addDays(last, -6) < first ? first : addDays(last, -6), end: last, mode: "latestAvailable" };
}

export default function UpcomingGames({ games, data }: UpcomingGamesProps) {
  const [statusFilter, setStatusFilter] = useState("scheduled");
  const [searchText, setSearchText] = useState("");
  const [showMap, setShowMap] = useState(false);
  const [loadedScheduleGames, setLoadedScheduleGames] = useState<Record<string, ScheduleGame[]>>({});
  const [scheduleError, setScheduleError] = useState<string | null>(null);
  const [dateOverride, setDateOverride] = useState<DateRangeOverride>(null);
  const [visibleLimitState, setVisibleLimitState] = useState({ key: "", limit: SCHEDULE_PAGE_SIZE });

  const todayStr = useMemo(() => toISODate(new Date()), []);

  const statusOptions = ["All", "scheduled", "in_progress", "final", "canceled", "postponed"];
  const scheduleIndex = useMemo(() => data.scheduleIndex ?? [], [data.scheduleIndex]);
  const scheduleDates = useMemo(
    () => scheduleIndex.map((entry) => entry.date).filter((date) => date && date !== "unknown").sort(),
    [scheduleIndex]
  );
  const defaultRange = useMemo(() => deriveDefaultRange(scheduleDates, todayStr), [scheduleDates, todayStr]);
  const startDate = dateOverride?.start ?? defaultRange.start;
  const endDate = dateOverride?.end ?? defaultRange.end;
  const scheduleCoverage = data.dataMetadata?.schedule;
  const isShowingFallbackRange = !dateOverride && defaultRange.mode !== "current";

  const setQuickFilter = (preset: string) => {
    const now = new Date();
    if (preset === "today") {
      const today = toISODate(now);
      setDateOverride({ start: today, end: today });
    } else if (preset === "week") {
      const today = toISODate(now);
      const end = new Date(now);
      end.setDate(end.getDate() + 6);
      setDateOverride({ start: today, end: toISODate(end) });
    } else if (preset === "nextweek") {
      const start = new Date(now);
      start.setDate(start.getDate() + (7 - start.getDay()));
      const end = new Date(start);
      end.setDate(end.getDate() + 6);
      setDateOverride({ start: toISODate(start), end: toISODate(end) });
    } else if (preset === "month") {
      const end = new Date(now.getFullYear(), now.getMonth() + 1, 0);
      setDateOverride({ start: toISODate(now), end: toISODate(end) });
    } else if (preset === "all") {
      setDateOverride({ start: "", end: "" });
    } else if (preset === "auto") {
      setDateOverride(null);
    }
  };

  const requiredScheduleEntries = useMemo(() => {
    if (scheduleIndex.length === 0) return [];
    return scheduleIndex.filter((entry) => {
      if (startDate && entry.date < startDate) return false;
      if (endDate && entry.date > endDate) return false;
      return true;
    });
  }, [scheduleIndex, startDate, endDate]);

  useEffect(() => {
    if (requiredScheduleEntries.length === 0) return;
    const missingEntries = requiredScheduleEntries.filter(
      (entry) => !loadedScheduleGames[entry.date]
    );
    if (missingEntries.length === 0) return;

    let cancelled = false;

    Promise.all(
      missingEntries.map((entry) =>
        fetchJsonWithRetry<ScheduleGame[]>(entry.path)
          .then((loadedGames) => [entry.date, loadedGames] as const)
      )
    )
      .then((loadedEntries) => {
        if (cancelled) return;
        setScheduleError(null);
        setLoadedScheduleGames((current) => {
          const next = { ...current };
          loadedEntries.forEach(([date, loadedGames]) => {
            next[date] = loadedGames;
          });
          return next;
        });
      })
      .catch((error) => {
        if (!cancelled) {
          setScheduleError(error instanceof Error ? error.message : "Failed to load schedule");
        }
      });

    return () => {
      cancelled = true;
    };
  }, [requiredScheduleEntries, loadedScheduleGames]);

  const pendingScheduleCount = useMemo(() => {
    return requiredScheduleEntries.filter((entry) => !loadedScheduleGames[entry.date]).length;
  }, [loadedScheduleGames, requiredScheduleEntries]);
  const isLoadingSchedule = pendingScheduleCount > 0 && !scheduleError;

  const activeGames = useMemo(() => {
    if (scheduleIndex.length === 0) return games;
    return requiredScheduleEntries.flatMap((entry) => loadedScheduleGames[entry.date] ?? []);
  }, [games, loadedScheduleGames, requiredScheduleEntries, scheduleIndex.length]);

  const expectedGameCount = useMemo(() => {
    if (scheduleIndex.length === 0) return games.length;
    return requiredScheduleEntries.reduce((sum, entry) => sum + entry.count, 0);
  }, [games.length, requiredScheduleEntries, scheduleIndex.length]);

  const filtered = useMemo(() => {
    return activeGames.filter((g) => {
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
  }, [activeGames, statusFilter, startDate, endDate, searchText]);

  const filterKey = `${statusFilter}|${searchText}|${startDate}|${endDate}`;
  const visibleLimit =
    visibleLimitState.key === filterKey ? visibleLimitState.limit : SCHEDULE_PAGE_SIZE;
  const visibleFiltered = useMemo(
    () => filtered.slice(0, visibleLimit),
    [filtered, visibleLimit]
  );
  const hiddenCount = Math.max(0, filtered.length - visibleFiltered.length);

  const grouped = useMemo(() => {
    const groups: Record<string, ScheduleGame[]> = {};
    visibleFiltered.forEach((g) => {
      const key = g.date_display || "Unknown";
      if (!groups[key]) groups[key] = [];
      groups[key].push(g);
    });
    return groups;
  }, [visibleFiltered]);

  const statusColors: Record<string, string> = {
    scheduled: "#28a745",
    in_progress: "#ff6b35",
    final: "#666",
    canceled: "#dc3545",
    postponed: "#ffc107",
  };

  const getTeamLogo = (team: { name?: string; logo_url?: string }) => {
    if (team.logo_url) return team.logo_url;
    const ncaaLogo = data.ncaaTeamLogos?.[team.name || ""];
    if (typeof ncaaLogo === "string" && /^https?:\/\//.test(ncaaLogo)) {
      return ncaaLogo;
    }
    if (ncaaLogo)
      return `https://a.espncdn.com/i/teamlogos/ncaa/500/${ncaaLogo}.png`;
    return "";
  };

  const activeQuick = useMemo((): string => {
    if (!dateOverride) return "auto";
    if (!startDate && !endDate) return "all";
    const now = new Date();
    const today = toISODate(now);
    if (startDate === today && endDate === today) return "today";
    const weekEnd = new Date(now);
    weekEnd.setDate(weekEnd.getDate() + 6);
    if (startDate === today && endDate === toISODate(weekEnd)) return "week";
    const monthEnd = new Date(now.getFullYear(), now.getMonth() + 1, 0);
    if (startDate === today && endDate === toISODate(monthEnd)) return "month";
    return "";
  }, [dateOverride, startDate, endDate]);

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
        <span className="filter-count">
          {isLoadingSchedule && filtered.length === 0
            ? `Loading ${expectedGameCount} games`
            : `${filtered.length} games`}
        </span>
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
          onChange={(e) => setDateOverride({ start: e.target.value, end: endDate })}
          className="schedule-date-input"
        />
        <span className="schedule-date-sep">to</span>
        <input
          type="date"
          value={endDate}
          onChange={(e) => setDateOverride({ start: startDate, end: e.target.value })}
          className="schedule-date-input"
        />
        {[
          { key: "auto", label: "Available" },
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

      {(isShowingFallbackRange || scheduleCoverage?.first_date || scheduleCoverage?.last_date) && (
        <div className={`schedule-coverage-note${isShowingFallbackRange ? " stale" : ""}`}>
          <strong>
            {isShowingFallbackRange ? "Showing available schedule data" : "Schedule coverage"}
          </strong>
          {scheduleCoverage?.first_date && scheduleCoverage?.last_date && (
            <span>{scheduleCoverage.first_date} to {scheduleCoverage.last_date}</span>
          )}
        </div>
      )}

      {showMap && <ScheduleMap games={visibleFiltered} data={data} />}

      {scheduleError && (
        <div className="empty-state">
          Could not load schedule data ({scheduleError}).
        </div>
      )}

      {isLoadingSchedule && filtered.length === 0 && !scheduleError && (
        <div className="empty-state">Loading schedule...</div>
      )}

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

      {hiddenCount > 0 && (
        <div className="schedule-show-more">
          <span>
            Showing {visibleFiltered.length.toLocaleString()} of {filtered.length.toLocaleString()} games
          </span>
          <button
            type="button"
            className="toggle-btn"
            onClick={() =>
              setVisibleLimitState({
                key: filterKey,
                limit: visibleLimit + SCHEDULE_PAGE_SIZE,
              })
            }
          >
            Show More
          </button>
        </div>
      )}

      {filtered.length === 0 && !isLoadingSchedule && !scheduleError && (
        <div className="empty-state">
          No games match your filters. Try adjusting the search or filters above.
        </div>
      )}
    </div>
  );
}
