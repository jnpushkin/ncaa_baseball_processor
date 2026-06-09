"use client";

import { useState, useMemo, Fragment } from "react";
import { UnifiedBatter, SiteData } from "@/types";
import LevelBadge from "@/components/shared/LevelBadge";
import TeamLogo from "@/components/shared/TeamLogo";
import PlayerLink from "@/components/shared/PlayerLink";
import LevelLeagueFilter from "@/components/shared/LevelLeagueFilter";
import SortableHeader from "@/components/shared/SortableHeader";
import PaginationControls from "@/components/shared/PaginationControls";
import { useSortableData } from "@/hooks/useSortableData";
import { usePagination } from "@/hooks/usePagination";
import { filterByLevelLeague, groupByPlayer } from "@/lib/filters";
import { getTeamDisplayName } from "@/lib/data";

interface UnifiedBattersTableProps {
  batters: UnifiedBatter[];
  onPlayerClick?: (player: UnifiedBatter, type: "batter") => void;
  data: SiteData;
}

// Extend UnifiedBatter with combined-row fields that come from groupByPlayer
interface CombinedBatter extends UnifiedBatter {
  isCombined?: boolean;
  subRows?: CombinedBatter[];
  levels?: string[];
  teams?: { team: string; team_id?: number; level: string }[];
}

export default function UnifiedBattersTable({
  batters,
  onPlayerClick,
  data,
}: UnifiedBattersTableProps) {
  const [levelFilter, setLevelFilter] = useState("All");
  const [leagueFilter, setLeagueFilter] = useState("All");
  const [searchTerm, setSearchTerm] = useState("");
  const [expandedPlayers, setExpandedPlayers] = useState<Set<string>>(new Set());

  const levelColors = data.levelColors ?? {};

  const toggleExpand = (brefId: string) => {
    setExpandedPlayers((prev) => {
      const next = new Set(prev);
      if (next.has(brefId)) next.delete(brefId);
      else next.add(brefId);
      return next;
    });
  };

  const filtered = useMemo(() => {
    if (!batters) return [];
    let result = filterByLevelLeague(batters, levelFilter, leagueFilter);
    if (searchTerm) {
      const s = searchTerm.toLowerCase();
      result = result.filter(
        (b) =>
          b.name?.toLowerCase().includes(s) ||
          b.team?.toLowerCase().includes(s)
      );
    }
    return groupByPlayer(
      result,
      levelFilter,
      ["g", "ab", "r", "h", "doubles", "triples", "hr", "rbi", "bb", "k", "sb"],
      (c) => {
        c.avg = c.ab > 0 ? (c.h / c.ab).toFixed(3) : ".000";
      }
    );
  }, [batters, levelFilter, leagueFilter, searchTerm]);

  const { items, sortConfig, requestSort } = useSortableData(
    filtered,
    { key: "g", direction: "desc" },
    "ab"
  );
  const sortedBatters = items as CombinedBatter[];
  const pagination = usePagination(sortedBatters, 100);

  const renderBatterRow = (
    b: CombinedBatter,
    key: string | number,
    isSubRow: boolean
  ) => {
    return (
      <tr
        key={key}
        style={{
          ...(isSubRow ? { background: "#f8f9fa" } : {}),
          ...(b.isCombined ? { cursor: "pointer" } : {}),
        }}
        onClick={
          b.isCombined && b.bref_id
            ? () => toggleExpand(b.bref_id!)
            : undefined
        }
      >
        <td>
          <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
            {b.isCombined ? (
              <>
                <span
                  style={{ fontSize: "10px", color: "#666", width: "12px" }}
                >
                  {expandedPlayers.has(b.bref_id!) ? "\u25BC" : "\u25B6"}
                </span>
                {(b.levels ?? []).map((l, j) => (
                  <span key={j}>
                    <LevelBadge level={l} levelColors={levelColors} />
                  </span>
                ))}
              </>
            ) : (
              <>
                {isSubRow && <span style={{ width: "12px" }}></span>}
                <LevelBadge level={b.level} levelColors={levelColors} />
              </>
            )}
          </div>
        </td>
        <td>
          <PlayerLink
            name={b.name}
            brefId={b.bref_id}
            onClick={(e) => {
              e.stopPropagation();
              onPlayerClick?.(b, "batter");
            }}
          />
        </td>
        <td>
          {b.teams ? (
            <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
              {b.teams.map((t, j) => (
                <div
                  key={j}
                  style={{ display: "flex", alignItems: "center", gap: "6px" }}
                >
                  <TeamLogo
                    team={t.team}
                    teamId={t.team_id}
                    level={t.level}
                    size={20}
                    data={data}
                  />
                  {getTeamDisplayName(t.team, data)}
                </div>
              ))}
            </div>
          ) : (
            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <TeamLogo
                team={b.team}
                teamId={b.team_id}
                level={b.level}
                size={20}
                data={data}
              />
              {getTeamDisplayName(b.team, data)}
            </div>
          )}
        </td>
        <td className="text-center">{b.g}</td>
        <td className="text-center">{b.ab}</td>
        <td className="text-center">{b.r}</td>
        <td className="text-center">{b.h}</td>
        <td className="text-center">{b.doubles}</td>
        <td className="text-center">{b.triples}</td>
        <td className="text-center">{b.hr}</td>
        <td className="text-center">{b.rbi}</td>
        <td className="text-center">{b.bb}</td>
        <td className="text-center">{b.k}</td>
        <td className="text-center">{b.sb}</td>
        <td className="text-center">{b.avg}</td>
      </tr>
    );
  };

  if (!batters || batters.length === 0) {
    return (
      <div className="panel">
        <div className="panel-header">
          <h2>All Batters</h2>
        </div>
        <div style={{ padding: "20px", textAlign: "center", color: "#666" }}>
          No batting data available.
        </div>
      </div>
    );
  }

  return (
    <div className="panel">
      <div className="panel-header">
        <h2>All Batters ({sortedBatters.length})</h2>
      </div>
      <LevelLeagueFilter
        levelFilter={levelFilter}
        setLevelFilter={setLevelFilter}
        leagueFilter={leagueFilter}
        setLeagueFilter={setLeagueFilter}
        data={batters}
        showSearch={true}
        searchTerm={searchTerm}
        setSearchTerm={setSearchTerm}
        searchPlaceholder="Search by name or team..."
      />
      <div className="table-container">
        <table className="data-table">
          <thead>
            <tr>
              <SortableHeader
                label="Level"
                sortKey="level"
                sortConfig={sortConfig}
                onSort={requestSort}
              />
              <SortableHeader
                label="Name"
                sortKey="name"
                sortConfig={sortConfig}
                onSort={requestSort}
              />
              <SortableHeader
                label="Team"
                sortKey="team"
                sortConfig={sortConfig}
                onSort={requestSort}
              />
              <SortableHeader
                label="G"
                sortKey="g"
                sortConfig={sortConfig}
                onSort={requestSort}
              />
              <SortableHeader
                label="AB"
                sortKey="ab"
                sortConfig={sortConfig}
                onSort={requestSort}
              />
              <SortableHeader
                label="R"
                sortKey="r"
                sortConfig={sortConfig}
                onSort={requestSort}
              />
              <SortableHeader
                label="H"
                sortKey="h"
                sortConfig={sortConfig}
                onSort={requestSort}
              />
              <SortableHeader
                label="2B"
                sortKey="doubles"
                sortConfig={sortConfig}
                onSort={requestSort}
              />
              <SortableHeader
                label="3B"
                sortKey="triples"
                sortConfig={sortConfig}
                onSort={requestSort}
              />
              <SortableHeader
                label="HR"
                sortKey="hr"
                sortConfig={sortConfig}
                onSort={requestSort}
              />
              <SortableHeader
                label="RBI"
                sortKey="rbi"
                sortConfig={sortConfig}
                onSort={requestSort}
              />
              <SortableHeader
                label="BB"
                sortKey="bb"
                sortConfig={sortConfig}
                onSort={requestSort}
              />
              <SortableHeader
                label="K"
                sortKey="k"
                sortConfig={sortConfig}
                onSort={requestSort}
              />
              <SortableHeader
                label="SB"
                sortKey="sb"
                sortConfig={sortConfig}
                onSort={requestSort}
              />
              <SortableHeader
                label="AVG"
                sortKey="avg"
                sortConfig={sortConfig}
                onSort={requestSort}
              />
            </tr>
          </thead>
          <tbody>
            {pagination.pageItems.map((b, i) => {
              const rowKey = b.bref_id || `${b.name}-${b.team}-${pagination.start + i}`;
              return (
                <Fragment key={rowKey}>
                  {renderBatterRow(b, rowKey, false)}
                  {b.isCombined &&
                    b.bref_id &&
                    expandedPlayers.has(b.bref_id) &&
                    (b.subRows ?? []).map((sub, j) =>
                      renderBatterRow(sub, `${rowKey}-${j}`, true)
                    )}
                </Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
      <PaginationControls {...pagination} />
    </div>
  );
}
