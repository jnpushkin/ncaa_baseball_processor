"use client";

import { useMemo } from "react";
import { MilestoneEntry, SiteData } from "@/types";
import { filterByLevelLeague } from "@/lib/filters";
import { formatDate } from "@/lib/baseball";
import LevelBadge from "@/components/shared/LevelBadge";
import SortableHeader from "@/components/shared/SortableHeader";
import { getTeamDisplayName } from "@/lib/teams";
import { useSortableData } from "@/hooks/useSortableData";
import TeamLogo from "@/components/shared/TeamLogo";

export interface MilestonesTableProps {
  title: string;
  data: MilestoneEntry[];
  columns: string[];
  levelFilter: string;
  leagueFilter: string;
  searchTerm?: string;
  onPlayerClick?: (row: MilestoneEntry, type: "batter" | "pitcher") => void;
  siteData: SiteData;
}

export default function MilestonesTable({
  title,
  data,
  columns,
  levelFilter,
  leagueFilter,
  searchTerm = "",
  onPlayerClick,
  siteData,
}: MilestonesTableProps) {
  const levelColors = siteData.levelColors ?? {};

  const filtered = useMemo(() => {
    const base = filterByLevelLeague(data ?? [], levelFilter, leagueFilter);
    const tokens = searchTerm.trim().toLowerCase().split(/\s+/).filter(Boolean);
    if (!tokens.length) return base;
    return base.filter((row) => {
      const haystack = [
        row.Player,
        row.Team,
        row.Opponent,
        row.Level,
        row.level,
        row.League,
        row.league,
      ]
        .filter((value) => value !== undefined)
        .join(" ")
        .toLowerCase();
      return tokens.every((token) => haystack.includes(token));
    });
  }, [data, levelFilter, leagueFilter, searchTerm]);

  const { items, sortConfig, requestSort } = useSortableData(filtered, {
    key: "Date",
    direction: "desc",
  });

  if (!filtered || filtered.length === 0) return null;

  const allColumns = ["Level", ...columns];
  const textCols = ["Player", "Team", "Opponent", "Date", "Level"];

  return (
    <div className="panel milestone-table-panel">
      <div className="panel-header milestone-table-header">
        <h2>{title}</h2>
        <span>{filtered.length.toLocaleString()}</span>
      </div>
      <div className="table-container">
        <table className="data-table milestones-table">
          <thead>
            <tr>
              {allColumns.map((col) => (
                <SortableHeader
                  key={col}
                  label={col}
                  sortKey={col}
                  sortConfig={sortConfig}
                  onSort={requestSort}
                />
              ))}
            </tr>
          </thead>
          <tbody>
            {items.slice(0, 50).map((row, i) => {
              const isPitcher = row["IP"] !== undefined;
              return (
                <tr key={i}>
                  {allColumns.map((col) => (
                    <td
                      key={col}
                      className={textCols.includes(col) ? "" : "text-center"}
                    >
                      {col === "Level" ? (
                        <LevelBadge
                          level={String(row[col] ?? "")}
                          levelColors={levelColors}
                        />
                      ) : col === "Player" ? (
                        <button
                          type="button"
                          className="clickable-name milestone-player-button"
                          onClick={() =>
                            onPlayerClick?.(row, isPitcher ? "pitcher" : "batter")
                          }
                        >
                          {row[col]}
                        </button>
                      ) : col === "Date" ? (
                        formatDate(String(row[col] ?? ""))
                      ) : col === "Team" || col === "Opponent" ? (
                        <span className="milestone-team-cell">
                          <TeamLogo
                            team={String(row[col] ?? "")}
                            level={String(row.Level ?? row.level ?? "")}
                            size={20}
                            data={siteData}
                          />
                          <span>
                            {getTeamDisplayName(
                              String(row[col] ?? ""),
                              siteData.ncaaTeamNicknames ?? {},
                              siteData.ncaaTeamLogos ?? {}
                            )}
                          </span>
                        </span>
                      ) : (
                        row[col]
                      )}
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
