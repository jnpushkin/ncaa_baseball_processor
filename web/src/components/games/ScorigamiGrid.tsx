"use client";

import { useMemo, useState } from "react";
import { ScorigamiEntry, UnifiedGame, SiteData } from "@/types";

interface FilteredScorigamiEntry {
  count: number;
  games: ScorigamiEntry["games"];
}

export interface ScorigamiGridProps {
  scorigami: Record<string, ScorigamiEntry>;
  games: UnifiedGame[];
  data: SiteData;
}

export default function ScorigamiGrid({
  scorigami,
  games: _games,
  data,
}: ScorigamiGridProps) {
  const [levelFilter, setLevelFilter] = useState("All");
  const [selectedCell, setSelectedCell] = useState<string | null>(null);

  const levelColors = data.levelColors ?? {};

  const filteredScorigami = useMemo<Record<string, FilteredScorigamiEntry>>(
    () => {
      if (levelFilter === "All") return scorigami;
      const filtered: Record<string, FilteredScorigamiEntry> = {};
      Object.entries(scorigami).forEach(([key, val]) => {
        const fg = val.games.filter((g) => {
          if (levelFilter === "NCAA") return g.level === "NCAA";
          return g.level === "MiLB" || g.level === "Partner";
        });
        if (fg.length > 0) filtered[key] = { count: fg.length, games: fg };
      });
      return filtered;
    },
    [scorigami, levelFilter]
  );

  const { maxWinner, maxLoser, maxCount, totalGames, totalCombos, mostCommon } =
    useMemo(() => {
      let mw = 0, ml = 0, mc = 0, tg = 0, best = "";
      Object.entries(filteredScorigami).forEach(([key, val]) => {
        const [lo, hi] = key.split("-").map(Number);
        if (hi > mw) mw = hi;
        if (lo > ml) ml = lo;
        if (val.count > mc) { mc = val.count; best = key; }
        tg += val.count;
      });
      return {
        maxWinner: Math.min(mw, 30),
        maxLoser: Math.min(ml, 25),
        maxCount: mc,
        totalGames: tg,
        totalCombos: Object.keys(filteredScorigami).length,
        mostCommon: best,
      };
    }, [filteredScorigami]);

  const getColor = (count: number): string => {
    if (!count) return "#f0f2f5";
    if (count === 1) return "#ffd700";
    const intensity = Math.min(count / Math.max(maxCount * 0.6, 1), 1);
    const r = Math.round(66 - intensity * 36);
    const g = Math.round(133 - intensity * 50);
    const b = Math.round(244 - intensity * 30);
    return `rgb(${r},${g},${b})`;
  };

  const handleFilterClick = (level: string) => {
    setLevelFilter(level);
    setSelectedCell(null);
  };

  const selectedEntry = selectedCell ? filteredScorigami[selectedCell] : null;

  return (
    <div>
      {/* Filter buttons + stats */}
      <div className="filter-bar" style={{ padding: 0, marginBottom: 16 }}>
        {["All", "NCAA", "MiLB/Pro"].map((level) => (
          <button
            key={level}
            onClick={() => handleFilterClick(level)}
            className={`pill-btn${levelFilter === level ? " active" : ""}`}
          >
            {level}
          </button>
        ))}
        <span className="filter-count" style={{ marginLeft: "auto" }}>
          {totalCombos} unique scores across {totalGames} games
          {mostCommon &&
            ` | Most common: ${mostCommon.replace("-", " to ")} (${filteredScorigami[mostCommon]?.count}x)`}
        </span>
      </div>

      {/* Legend */}
      <div className="legend" style={{ marginTop: 0, marginBottom: 16 }}>
        {[
          { bg: "#ffd700", label: "Scorigami (1x)" },
          { bg: "rgb(50,100,230)", label: "Multiple" },
          { bg: "#f0f2f5", label: "Never" },
        ].map(({ bg, label }) => (
          <span key={label} className="legend-item">
            <span className="legend-swatch" style={{ background: bg }} />
            {label}
          </span>
        ))}
      </div>

      {/* Grid */}
      <div style={{ overflowX: "auto", marginBottom: 16 }}>
        <div style={{ display: "inline-block", minWidth: "fit-content" }}>
          <div className="scorigami-axis-label" style={{ marginBottom: 4 }}>
            Winner Score &rarr;
          </div>
          <div style={{ display: "flex" }}>
            <div style={{ width: 26, display: "flex", alignItems: "center", justifyContent: "center" }}>
              <span style={{ writingMode: "vertical-rl", transform: "rotate(180deg)" }} className="scorigami-axis-label">
                &larr; Loser Score
              </span>
            </div>

            <div>
              <div style={{ display: "flex" }}>
                <div style={{ width: 26, height: 26 }} />
                {Array.from({ length: maxWinner }, (_, i) => i + 1).map((w) => (
                  <div key={w} className="scorigami-header-cell">{w}</div>
                ))}
              </div>

              {Array.from({ length: maxLoser + 1 }, (_, i) => i).map((loser) => (
                <div key={loser} style={{ display: "flex" }}>
                  <div className="scorigami-header-cell">{loser}</div>
                  {Array.from({ length: maxWinner }, (_, i) => i + 1).map((winner) => {
                    if (winner <= loser) {
                      return <div key={winner} style={{ width: 26, height: 26, background: "#eaeaea" }} />;
                    }
                    const key = `${loser}-${winner}`;
                    const entry = filteredScorigami[key];
                    const count = entry?.count ?? 0;
                    const isSelected = selectedCell === key;
                    return (
                      <div
                        key={winner}
                        onClick={() => count > 0 && setSelectedCell(isSelected ? null : key)}
                        className={`scorigami-cell${count > 0 ? " scorigami-cell--active" : ""}${isSelected ? " scorigami-cell--selected" : ""}`}
                        style={{
                          background: getColor(count),
                          color: count > 1 ? "white" : count === 1 ? "#333" : "#ccc",
                        }}
                      >
                        {count > 0 ? count : ""}
                      </div>
                    );
                  })}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Selected cell detail */}
      {selectedCell && selectedEntry && (
        <div className="scorigami-detail">
          <div className="scorigami-detail-header">
            <h3>
              Score: {selectedCell.replace("-", " to ")} ({selectedEntry.count} game
              {selectedEntry.count > 1 ? "s" : ""})
            </h3>
            <button className="close-btn" onClick={() => setSelectedCell(null)}>&#10005;</button>
          </div>
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Away</th>
                <th className="text-center">Score</th>
                <th>Home</th>
                <th>Level</th>
              </tr>
            </thead>
            <tbody>
              {selectedEntry.games.map((g, i) => (
                <tr key={i}>
                  <td>{g.date}</td>
                  <td style={{ fontWeight: g.away_score > g.home_score ? 700 : 400 }}>{g.away}</td>
                  <td className="text-center" style={{ fontWeight: 600 }}>
                    {g.away_score} - {g.home_score}
                  </td>
                  <td style={{ fontWeight: g.home_score > g.away_score ? 700 : 400 }}>{g.home}</td>
                  <td>
                    <span
                      className="level-badge level-badge--filled"
                      style={{
                        background:
                          g.level === "NCAA" ? "#e8f5e9" :
                          g.level === "Partner" ? "#f3e5f5" : "#fff3e0",
                        color: levelColors[g.level] ??
                          (g.level === "NCAA" ? "#28a745" :
                          g.level === "Partner" ? "#9c27b0" : "#ff6b35"),
                      }}
                    >
                      {g.level}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
