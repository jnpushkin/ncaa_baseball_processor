"use client";

import { useMemo } from "react";

const DEFAULT_LEVEL_ORDER = [
  "NCAA",
  "Triple-A",
  "Double-A",
  "High-A",
  "Single-A",
  "Independent",
];

interface LevelLeagueFilterProps {
  levelFilter: string;
  setLevelFilter: (level: string) => void;
  leagueFilter: string;
  setLeagueFilter?: (league: string) => void;
  data: any[];
  levelOrder?: string[];
  showSearch?: boolean;
  searchTerm?: string;
  setSearchTerm?: (term: string) => void;
  searchPlaceholder?: string;
}

export default function LevelLeagueFilter({
  levelFilter,
  setLevelFilter,
  leagueFilter,
  setLeagueFilter,
  data,
  levelOrder = DEFAULT_LEVEL_ORDER,
  showSearch = false,
  searchTerm = "",
  setSearchTerm,
  searchPlaceholder = "Search...",
}: LevelLeagueFilterProps) {
  const availableLevels = useMemo(() => {
    if (!data) return [];
    const levels = new Set<string>();
    data.forEach((d) => {
      const l = d.level ?? d.Level;
      if (l) levels.add(l);
    });
    return levelOrder.filter((l) => levels.has(l));
  }, [data, levelOrder]);

  const availableLeagues = useMemo(() => {
    if (!data || levelFilter === "All") return [];
    const leagues = new Set<string>();
    data.forEach((d) => {
      const itemLevel = d.level ?? d.Level ?? "";
      const itemLeague =
        d.league ?? d.League ?? d.conference ?? d.Conference ?? "";
      if (itemLevel === levelFilter && itemLeague) leagues.add(itemLeague);
    });
    return Array.from(leagues).sort();
  }, [data, levelFilter]);

  const handleLevelChange = (newLevel: string) => {
    setLevelFilter(newLevel);
    if (setLeagueFilter) setLeagueFilter("All");
  };

  return (
    <div className="filter-bar">
      <select
        className="filter-select"
        value={levelFilter}
        onChange={(e) => handleLevelChange(e.target.value)}
      >
        <option value="All">All Levels</option>
        {availableLevels.map((l) => (
          <option key={l} value={l}>
            {l}
          </option>
        ))}
      </select>

      {levelFilter !== "All" &&
        availableLeagues.length > 1 &&
        setLeagueFilter && (
          <select
            className="filter-select"
            style={{ minWidth: 150 }}
            value={leagueFilter ?? "All"}
            onChange={(e) => setLeagueFilter(e.target.value)}
          >
            <option value="All">All Leagues</option>
            {availableLeagues.map((l) => (
              <option key={l} value={l}>
                {l}
              </option>
            ))}
          </select>
        )}

      {showSearch && (
        <input
          type="text"
          className="filter-input"
          placeholder={searchPlaceholder}
          value={searchTerm}
          onChange={(e) => setSearchTerm?.(e.target.value)}
        />
      )}
    </div>
  );
}
