"use client";

import { useState, useMemo, Fragment } from "react";
import { UnifiedPitcher, SiteData } from "@/types";
import LevelBadge from "@/components/shared/LevelBadge";
import TeamLogo from "@/components/shared/TeamLogo";
import PlayerLink from "@/components/shared/PlayerLink";
import LevelLeagueFilter from "@/components/shared/LevelLeagueFilter";
import SortableHeader from "@/components/shared/SortableHeader";
import PaginationControls from "@/components/shared/PaginationControls";
import { useSortableData } from "@/hooks/useSortableData";
import { usePagination } from "@/hooks/usePagination";
import { filterByLevelLeague, groupByPlayer } from "@/lib/filters";
import { ipToInnings } from "@/lib/baseball";
import { getTeamDisplayName } from "@/lib/data";

interface UnifiedPitchersTableProps {
  pitchers: UnifiedPitcher[];
  onPlayerClick?: (player: UnifiedPitcher, type: "pitcher") => void;
  data: SiteData;
}

// Extend UnifiedPitcher with combined-row fields that come from groupByPlayer
interface CombinedPitcher extends UnifiedPitcher {
  isCombined?: boolean;
  subRows?: CombinedPitcher[];
  levels?: string[];
  teams?: { team: string; team_id?: number; level: string }[];
}

export default function UnifiedPitchersTable({
  pitchers,
  onPlayerClick,
  data,
}: UnifiedPitchersTableProps) {
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
    if (!pitchers) return [];
    let result = filterByLevelLeague(pitchers, levelFilter, leagueFilter);
    if (searchTerm) {
      const s = searchTerm.toLowerCase();
      result = result.filter(
        (p) =>
          p.name?.toLowerCase().includes(s) ||
          p.team?.toLowerCase().includes(s)
      );
    }
    return groupByPlayer(
      result,
      levelFilter,
      ["g", "ip", "h", "r", "er", "bb", "k", "hr"],
      (c) => {
        const inn = ipToInnings(c.ip);
        c.era = inn > 0 ? ((c.er * 9) / inn).toFixed(2) : "0.00";
      },
      "ip"
    );
  }, [pitchers, levelFilter, leagueFilter, searchTerm]);

  const { items, sortConfig, requestSort } = useSortableData(
    filtered,
    { key: "g", direction: "desc" },
    "ip"
  );
  const sortedPitchers = items as CombinedPitcher[];
  const pagination = usePagination(sortedPitchers, 100);

  const renderPitcherRow = (
    p: CombinedPitcher,
    key: string | number,
    isSubRow: boolean
  ) => {
    return (
      <tr
        key={key}
        style={{
          ...(isSubRow ? { background: "#f8f9fa" } : {}),
          ...(p.isCombined ? { cursor: "pointer" } : {}),
        }}
        onClick={
          p.isCombined && p.bref_id
            ? () => toggleExpand(p.bref_id!)
            : undefined
        }
      >
        <td>
          <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
            {p.isCombined ? (
              <>
                <span
                  style={{ fontSize: "10px", color: "#666", width: "12px" }}
                >
                  {expandedPlayers.has(p.bref_id!) ? "\u25BC" : "\u25B6"}
                </span>
                {(p.levels ?? []).map((l, j) => (
                  <span key={j}>
                    <LevelBadge level={l} levelColors={levelColors} />
                  </span>
                ))}
              </>
            ) : (
              <>
                {isSubRow && <span style={{ width: "12px" }}></span>}
                <LevelBadge level={p.level} levelColors={levelColors} />
              </>
            )}
          </div>
        </td>
        <td>
          <PlayerLink
            name={p.name}
            brefId={p.bref_id}
            onClick={(e) => {
              e.stopPropagation();
              onPlayerClick?.(p, "pitcher");
            }}
          />
        </td>
        <td>
          {p.teams ? (
            <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
              {p.teams.map((t, j) => (
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
                team={p.team}
                teamId={p.team_id}
                level={p.level}
                size={20}
                data={data}
              />
              {getTeamDisplayName(p.team, data)}
            </div>
          )}
        </td>
        <td className="text-center">{p.g}</td>
        <td className="text-center">{p.ip}</td>
        <td className="text-center">{p.h}</td>
        <td className="text-center">{p.r}</td>
        <td className="text-center">{p.er}</td>
        <td className="text-center">{p.bb}</td>
        <td className="text-center">{p.k}</td>
        <td className="text-center">{p.hr}</td>
        <td className="text-center">{p.era}</td>
      </tr>
    );
  };

  if (!pitchers || pitchers.length === 0) {
    return (
      <div className="panel">
        <div className="panel-header">
          <h2>All Pitchers</h2>
        </div>
        <div style={{ padding: "20px", textAlign: "center", color: "#666" }}>
          No pitching data available.
        </div>
      </div>
    );
  }

  return (
    <div className="panel">
      <div className="panel-header">
        <h2>All Pitchers ({sortedPitchers.length})</h2>
      </div>
      <LevelLeagueFilter
        levelFilter={levelFilter}
        setLevelFilter={setLevelFilter}
        leagueFilter={leagueFilter}
        setLeagueFilter={setLeagueFilter}
        data={pitchers}
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
                label="IP"
                sortKey="ip"
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
                label="R"
                sortKey="r"
                sortConfig={sortConfig}
                onSort={requestSort}
              />
              <SortableHeader
                label="ER"
                sortKey="er"
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
                label="HR"
                sortKey="hr"
                sortConfig={sortConfig}
                onSort={requestSort}
              />
              <SortableHeader
                label="ERA"
                sortKey="era"
                sortConfig={sortConfig}
                onSort={requestSort}
              />
            </tr>
          </thead>
          <tbody>
            {pagination.pageItems.map((p, i) => {
              const rowKey = p.bref_id || `${p.name}-${p.team}-${pagination.start + i}`;
              return (
                <Fragment key={rowKey}>
                  {renderPitcherRow(p, rowKey, false)}
                  {p.isCombined &&
                    p.bref_id &&
                    expandedPlayers.has(p.bref_id) &&
                    (p.subRows ?? []).map((sub, j) =>
                      renderPitcherRow(sub, `${rowKey}-${j}`, true)
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
