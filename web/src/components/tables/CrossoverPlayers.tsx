"use client";

import { useMemo, useState } from "react";
import { CrossoverPlayer, SiteData, SortConfig } from "@/types";
import { BREF_BASE } from "@/lib/constants";

// ---------------------------------------------------------------------------
// useSortableData hook (mirrors generator.py useSortableData)
// ---------------------------------------------------------------------------

function compareValues(
  aVal: unknown,
  bVal: unknown,
  direction: "asc" | "desc"
): number {
  if (typeof aVal === "number" && typeof bVal === "number") {
    return direction === "asc" ? aVal - bVal : bVal - aVal;
  }
  const aNum = parseFloat(String(aVal));
  const bNum = parseFloat(String(bVal));
  if (!isNaN(aNum) && !isNaN(bNum)) {
    return direction === "asc" ? aNum - bNum : bNum - aNum;
  }
  const aStr = String(aVal ?? "").toLowerCase();
  const bStr = String(bVal ?? "").toLowerCase();
  if (aStr < bStr) return direction === "asc" ? -1 : 1;
  if (aStr > bStr) return direction === "asc" ? 1 : -1;
  return 0;
}

function useSortableData(
  items: CrossoverPlayer[],
  defaultSort: SortConfig | null = null
) {
  const [sortConfig, setSortConfig] = useState<SortConfig | null>(defaultSort);

  const sortedItems = useMemo(() => {
    if (!sortConfig || !items) return items;
    return [...items].sort((a, b) =>
      compareValues(
        (a as unknown as Record<string, unknown>)[sortConfig.key],
        (b as unknown as Record<string, unknown>)[sortConfig.key],
        sortConfig.direction
      )
    );
  }, [items, sortConfig]);

  const requestSort = (key: string) => {
    const direction: "asc" | "desc" =
      sortConfig?.key === key && sortConfig.direction === "asc" ? "desc" : "asc";
    setSortConfig({ key, direction });
  };

  return { items: sortedItems, sortConfig, requestSort };
}

// ---------------------------------------------------------------------------
// PlayerTimeline sub-component
// ---------------------------------------------------------------------------

interface LevelDetail {
  level: string;
  games: number;
  teams: string;
}

interface PlayerTimelineProps {
  player: CrossoverPlayer;
  levelColors: Record<string, string>;
}

function PlayerTimeline({ player, levelColors }: PlayerTimelineProps) {
  // Build level details, supporting old data format as fallback
  const levels: LevelDetail[] = useMemo(() => {
    const details = player["Level Details"];
    if (details && details.length > 0) return details;
    const fallback: LevelDetail[] = [];
    if ((player["NCAA Games"] ?? 0) > 0) {
      fallback.push({
        level: "NCAA",
        games: player["NCAA Games"]!,
        teams: player["NCAA Teams"] ?? "",
      });
    }
    if ((player["MiLB Games"] ?? 0) > 0) {
      fallback.push({
        level: "MiLB",
        games: player["MiLB Games"]!,
        teams: player["MiLB Teams"] ?? "",
      });
    }
    return fallback;
  }, [player]);

  return (
    <div
      style={{
        padding: "16px",
        background: "#f8f9fa",
        borderRadius: "8px",
        marginTop: "8px",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          marginBottom: "16px",
        }}
      >
        <div style={{ fontSize: "18px", fontWeight: 600 }}>{player.Name}</div>
        {player["BBRef ID"] && (
          <a
            href={BREF_BASE + player["BBRef ID"]}
            target="_blank"
            rel="noopener noreferrer"
            style={{ marginLeft: "8px", fontSize: "12px", color: "#007bff" }}
          >
            View on Baseball Reference ↗
          </a>
        )}
      </div>

      <div style={{ display: "flex", alignItems: "stretch", gap: "0" }}>
        {levels.map((l, idx) => (
          <div key={l.level} style={{ display: "flex", alignItems: "stretch" }}>
            <div
              style={{
                flex: 1,
                padding: "16px",
                background: "white",
                borderRadius:
                  idx === 0
                    ? "8px 0 0 8px"
                    : idx === levels.length - 1
                    ? "0 8px 8px 0"
                    : "0",
                borderTop: `4px solid ${levelColors[l.level] ?? "#666"}`,
                textAlign: "center",
                minWidth: "120px",
              }}
            >
              <div
                style={{
                  display: "inline-block",
                  padding: "4px 12px",
                  background: levelColors[l.level] ?? "#666",
                  color: "white",
                  borderRadius: "4px",
                  fontWeight: 600,
                  marginBottom: "8px",
                }}
              >
                {l.level}
              </div>
              <div
                style={{
                  fontSize: "24px",
                  fontWeight: "bold",
                  marginBottom: "4px",
                }}
              >
                {l.games}
              </div>
              <div
                style={{
                  fontSize: "12px",
                  color: "#666",
                  marginBottom: "8px",
                }}
              >
                {l.games !== 1 ? "games" : "game"}
              </div>
              <div style={{ fontSize: "13px", color: "#333" }}>{l.teams}</div>
            </div>
            {idx < levels.length - 1 && (
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  padding: "0 8px",
                  background: "white",
                }}
              >
                <span style={{ fontSize: "24px", color: "#ccc" }}>→</span>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// CrossoverPlayers component
// ---------------------------------------------------------------------------

export interface CrossoverPlayersProps {
  players: CrossoverPlayer[];
  onPlayerClick?: (player: CrossoverPlayer, type: "batter" | "pitcher") => void;
  data: SiteData;
}

export default function CrossoverPlayers({
  players,
  onPlayerClick,
  data,
}: CrossoverPlayersProps) {
  const [expandedPlayer, setExpandedPlayer] = useState<number | null>(null);
  const [searchTerm, setSearchTerm] = useState("");

  const levelColors = data.levelColors ?? {};

  const { items } = useSortableData(players, {
    key: "Total Games",
    direction: "desc",
  });

  const filtered = useMemo(() => {
    if (!searchTerm) return items;
    const s = searchTerm.toLowerCase();
    return items.filter(
      (p) =>
        p.Name?.toLowerCase().includes(s) ||
        p["NCAA Teams"]?.toLowerCase().includes(s) ||
        p["MiLB Teams"]?.toLowerCase().includes(s)
    );
  }, [items, searchTerm]);

  if (!players || players.length === 0) {
    return (
      <div className="panel">
        <div className="panel-header">
          <h2>Crossover Players</h2>
        </div>
        <div style={{ padding: "20px", textAlign: "center", color: "#666" }}>
          No crossover players found. Crossover players are those seen at
          multiple levels (NCAA, MiLB, Partner).
        </div>
      </div>
    );
  }

  return (
    <div className="panel">
      <div className="panel-header">
        <h2>Crossover Players - Seen at Multiple Levels ({filtered.length})</h2>
      </div>
      <div style={{ padding: "16px" }}>
        <input
          type="text"
          className="search-box"
          placeholder="Search players or teams..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          style={{ marginBottom: "16px", maxWidth: "300px" }}
        />
      </div>
      <div style={{ padding: "0 16px 16px" }}>
        {filtered.map((p, i) => (
          <div key={i} style={{ marginBottom: "8px" }}>
            <div
              onClick={() =>
                setExpandedPlayer(expandedPlayer === i ? null : i)
              }
              style={{
                padding: "12px 16px",
                background: "white",
                borderRadius: expandedPlayer === i ? "8px 8px 0 0" : "8px",
                border: "1px solid #dee2e6",
                borderBottom:
                  expandedPlayer === i ? "none" : "1px solid #dee2e6",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "16px",
                }}
              >
                <span style={{ fontSize: "16px" }}>
                  {expandedPlayer === i ? "▼" : "▶"}
                </span>
                <span
                  className="clickable-name"
                  style={{ fontWeight: 600 }}
                  onClick={(e) => {
                    e.stopPropagation();
                    onPlayerClick?.(p, "batter");
                  }}
                >
                  {p.Name}
                </span>
                <div
                  style={{ display: "flex", gap: "4px", flexWrap: "wrap" }}
                >
                  {(p["Level Details"] ?? []).map((ld, li) => (
                    <span
                      key={li}
                      style={{
                        background: levelColors[ld.level] ?? "#666",
                        color: "white",
                        padding: "2px 8px",
                        borderRadius: "4px",
                        fontSize: "11px",
                      }}
                    >
                      {ld.level}
                    </span>
                  ))}
                </div>
              </div>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "24px",
                  color: "#666",
                }}
              >
                <span>{p["Total Games"]} total games</span>
              </div>
            </div>
            {expandedPlayer === i && (
              <div
                style={{
                  border: "1px solid #dee2e6",
                  borderTop: "none",
                  borderRadius: "0 0 8px 8px",
                  padding: "16px",
                  background: "#fafafa",
                }}
              >
                <PlayerTimeline player={p} levelColors={levelColors} />
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
