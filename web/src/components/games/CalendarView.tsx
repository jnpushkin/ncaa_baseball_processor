"use client";

import { useMemo, useState } from "react";
import { UnifiedGame, SiteData } from "@/types";
import { filterByLevelLeague } from "@/lib/filters";
import LevelBadge from "@/components/shared/LevelBadge";
import LevelLeagueFilter from "@/components/shared/LevelLeagueFilter";
import { getTeamDisplayName, getTeamLogoSrc } from "@/lib/teams";

const MONTHS = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

const DAYS_IN_MONTH = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];

function getColorIntensity(count: number): string {
  if (count === 0) return "#f0f2f5";
  if (count === 1) return "#c6e5c6";
  if (count === 2) return "#8fce8f";
  return "#4caf50";
}

export interface CalendarViewProps {
  games: UnifiedGame[];
  data: SiteData;
}

export default function CalendarView({ games, data }: CalendarViewProps) {
  const [selectedDay, setSelectedDay] = useState<string | null>(null);
  const [levelFilter, setLevelFilter] = useState("All");
  const [leagueFilter, setLeagueFilter] = useState("All");

  const levelColors = data.levelColors ?? {};
  const levelOrder = data.levelOrder ?? [
    "NCAA", "Triple-A", "Double-A", "High-A", "Single-A", "Independent",
  ];

  const filteredGames = useMemo(
    () => filterByLevelLeague(games ?? [], levelFilter, leagueFilter),
    [games, levelFilter, leagueFilter]
  );

  const gamesByDay = useMemo(() => {
    const map: Record<string, UnifiedGame[]> = {};
    filteredGames.forEach((game) => {
      const date = game.date;
      if (!date) return;
      const parts = date.split("/");
      if (parts.length >= 2) {
        const month = parseInt(parts[0], 10);
        const day = parseInt(parts[1], 10);
        if (month >= 1 && month <= 12 && day >= 1 && day <= 31) {
          const key = `${month}-${day}`;
          if (!map[key]) map[key] = [];
          map[key].push(game);
        }
      }
    });
    return map;
  }, [filteredGames]);

  const selectedGames = useMemo(() => {
    if (!selectedDay) return [];
    return gamesByDay[selectedDay] ?? [];
  }, [selectedDay, gamesByDay]);

  const handleLevelFilter = (v: string) => {
    setLevelFilter(v);
    setSelectedDay(null);
  };

  return (
    <div className="panel">
      <div className="panel-header">
        <h2>Games by Date (All Years)</h2>
      </div>
      <div className="panel-body">
        <div className="filter-bar" style={{ padding: 0, marginBottom: 16 }}>
          <LevelLeagueFilter
            levelFilter={levelFilter}
            setLevelFilter={handleLevelFilter}
            leagueFilter={leagueFilter}
            setLeagueFilter={setLeagueFilter}
            data={games ?? []}
            levelOrder={levelOrder}
          />
          <span className="filter-count">{filteredGames.length} games</span>
        </div>

        <div className="calendar-grid">
          {MONTHS.map((month, monthIdx) => (
            <div key={month} className="calendar-month">
              <div className="calendar-month-label">{month}</div>
              <div className="calendar-days">
                {Array.from({ length: DAYS_IN_MONTH[monthIdx] }, (_, i) => i + 1).map((day) => {
                  const key = `${monthIdx + 1}-${day}`;
                  const count = (gamesByDay[key] ?? []).length;
                  const isSelected = selectedDay === key;
                  return (
                    <div
                      key={day}
                      onClick={() => count > 0 && setSelectedDay(isSelected ? null : key)}
                      className={`calendar-day${count > 0 ? " calendar-day--active" : ""}${isSelected ? " calendar-day--selected" : ""}`}
                      style={{ background: getColorIntensity(count) }}
                      title={count > 0 ? `${month} ${day}: ${count} game(s)` : `${month} ${day}`}
                    >
                      {day}
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>

        {/* Legend */}
        <div className="legend" style={{ marginTop: 0, marginBottom: 16 }}>
          <span className="legend-item">Games:</span>
          {[
            { bg: "#f0f2f5", label: "0" },
            { bg: "#c6e5c6", label: "1" },
            { bg: "#8fce8f", label: "2" },
            { bg: "#4caf50", label: "3+" },
          ].map(({ bg, label }) => (
            <span key={label} className="legend-item">
              <span className="legend-swatch" style={{ background: bg }} />
              {label}
            </span>
          ))}
          <span style={{ marginLeft: "auto", display: "flex", gap: 10, flexWrap: "wrap" }}>
            {levelOrder.map((l) => (
              <span key={l} className="legend-item">
                <span className="legend-swatch" style={{ background: levelColors[l] ?? "#666", width: 10, height: 10, borderRadius: 2 }} />
                <span style={{ fontSize: "0.75rem" }}>{l}</span>
              </span>
            ))}
          </span>
        </div>

        {/* Selected day detail */}
        {selectedDay && selectedGames.length > 0 && (
          <div style={{ marginTop: 16 }}>
            <h4 className="calendar-detail-title">
              Games on {MONTHS[parseInt(selectedDay.split("-")[0], 10) - 1]}{" "}
              {selectedDay.split("-")[1]} ({selectedGames.length})
            </h4>
            <div className="table-container" style={{ maxHeight: 400 }}>
              <table>
                <thead>
                  <tr>
                    <th>Year</th>
                    <th>Level</th>
                    <th>Away</th>
                    <th className="text-center">Score</th>
                    <th>Home</th>
                    <th>Venue</th>
                  </tr>
                </thead>
                <tbody>
                  {[...selectedGames]
                    .sort((a, b) => {
                      const yearA = a.date?.split("/")[2] ?? "0";
                      const yearB = b.date?.split("/")[2] ?? "0";
                      return yearB.localeCompare(yearA);
                    })
                    .map((g, i) => {
                      const awayLogoSrc = getTeamLogoSrc(
                        g.away_team, g.away_team_id, g.level,
                        data.localLogos ?? {}, data.historicalTeamLogos ?? {},
                        data.ncaaTeamLogos ?? {}, data.partnerLogos ?? {}
                      );
                      const homeLogoSrc = getTeamLogoSrc(
                        g.home_team, g.home_team_id, g.level,
                        data.localLogos ?? {}, data.historicalTeamLogos ?? {},
                        data.ncaaTeamLogos ?? {}, data.partnerLogos ?? {}
                      );
                      return (
                        <tr
                          key={i}
                          style={{ borderLeft: `3px solid ${levelColors[g.level] ?? "#ccc"}` }}
                        >
                          <td>{g.date?.split("/")[2]}</td>
                          <td><LevelBadge level={g.level} levelColors={levelColors} /></td>
                          <td>
                            <div style={{ display: "flex", alignItems: "center" }}>
                              {awayLogoSrc && (
                                // eslint-disable-next-line @next/next/no-img-element
                                <img
                                  src={awayLogoSrc} alt=""
                                  style={{ width: 16, height: 16, objectFit: "contain", marginRight: 6 }}
                                  onError={(e) => ((e.target as HTMLImageElement).style.display = "none")}
                                />
                              )}
                              <span>{getTeamDisplayName(g.away_team ?? "", data.ncaaTeamNicknames ?? {}, data.ncaaTeamLogos ?? {})}</span>
                            </div>
                          </td>
                          <td className="text-center">{g.away_score} - {g.home_score}</td>
                          <td>
                            <div style={{ display: "flex", alignItems: "center" }}>
                              {homeLogoSrc && (
                                // eslint-disable-next-line @next/next/no-img-element
                                <img
                                  src={homeLogoSrc} alt=""
                                  style={{ width: 16, height: 16, objectFit: "contain", marginRight: 6 }}
                                  onError={(e) => ((e.target as HTMLImageElement).style.display = "none")}
                                />
                              )}
                              <span>{getTeamDisplayName(g.home_team ?? "", data.ncaaTeamNicknames ?? {}, data.ncaaTeamLogos ?? {})}</span>
                            </div>
                          </td>
                          <td>{g.venue}</td>
                        </tr>
                      );
                    })}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
