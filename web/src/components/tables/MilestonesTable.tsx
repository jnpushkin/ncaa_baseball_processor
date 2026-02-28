"use client";

import { useMemo } from "react";
import { MilestoneEntry, SiteData } from "@/types";
import { filterByLevelLeague } from "@/lib/filters";
import { formatDate } from "@/lib/baseball";
import LevelBadge from "@/components/shared/LevelBadge";
import SortableHeader from "@/components/shared/SortableHeader";
import { getTeamDisplayName } from "@/lib/teams";
import { useSortableData } from "@/hooks/useSortableData";

export interface MilestonesTableProps {
  title: string;
  data: MilestoneEntry[];
  columns: string[];
  levelFilter: string;
  leagueFilter: string;
  onPlayerClick?: (row: MilestoneEntry, type: "batter" | "pitcher") => void;
  siteData: SiteData;
}

export default function MilestonesTable({
  title,
  data,
  columns,
  levelFilter,
  leagueFilter,
  onPlayerClick,
  siteData,
}: MilestonesTableProps) {
  const levelColors = siteData.levelColors ?? {};

  const filtered = useMemo(
    () => filterByLevelLeague(data ?? [], levelFilter, leagueFilter),
    [data, levelFilter, leagueFilter]
  );

  const { items, sortConfig, requestSort } = useSortableData(filtered, {
    key: "Date",
    direction: "desc",
  });

  if (!filtered || filtered.length === 0) return null;

  const allColumns = ["Level", ...columns];
  const textCols = ["Player", "Team", "Opponent", "Date", "Level"];

  return (
    <div className="panel" style={{ marginTop: "16px" }}>
      <div className="panel-header">
        <h2>
          {title} ({filtered.length})
        </h2>
      </div>
      <div className="table-container">
        <table className="data-table">
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
                        <span
                          className="clickable-name"
                          onClick={() =>
                            onPlayerClick?.(row, isPitcher ? "pitcher" : "batter")
                          }
                        >
                          {row[col]}
                        </span>
                      ) : col === "Date" ? (
                        formatDate(String(row[col] ?? ""))
                      ) : col === "Team" || col === "Opponent" ? (
                        getTeamDisplayName(
                          String(row[col] ?? ""),
                          siteData.ncaaTeamNicknames ?? {},
                          siteData.ncaaTeamLogos ?? {}
                        )
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
