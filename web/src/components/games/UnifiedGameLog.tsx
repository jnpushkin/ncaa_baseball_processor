"use client";

import { useState, useMemo } from "react";
import { UnifiedGame, SiteData } from "@/types";
import LevelLeagueFilter from "@/components/shared/LevelLeagueFilter";
import LevelBadge from "@/components/shared/LevelBadge";
import TeamLogo from "@/components/shared/TeamLogo";
import SortableHeader from "@/components/shared/SortableHeader";
import PaginationControls from "@/components/shared/PaginationControls";
import { useSortableData } from "@/hooks/useSortableData";
import { usePagination } from "@/hooks/usePagination";
import { filterByLevelLeague } from "@/lib/filters";
import { formatDate } from "@/lib/baseball";
import { getTeamDisplayName } from "@/lib/data";

interface UnifiedGameLogProps {
  games: UnifiedGame[];
  data: SiteData;
  onGameClick?: (game: UnifiedGame) => void;
}

interface TeamCellProps {
  team: string;
  teamId: number | undefined;
  level: string;
  data: SiteData;
}

type SortableGame = UnifiedGame & {
  total_runs: number;
};

function TeamCell({ team, teamId, level, data }: TeamCellProps) {
  const displayName = getTeamDisplayName(team, data);

  return (
    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
      <TeamLogo team={team} teamId={teamId} level={level} size={20} data={data} />
      <span>{displayName}</span>
    </div>
  );
}

export default function UnifiedGameLog({ games, data, onGameClick }: UnifiedGameLogProps) {
  const [levelFilter, setLevelFilter] = useState("All");
  const [leagueFilter, setLeagueFilter] = useState("All");
  const [searchTerm, setSearchTerm] = useState("");

  const levelColors = data.levelColors ?? {};

  const filtered = useMemo(() => {
    let result = filterByLevelLeague(games, levelFilter, leagueFilter);
    if (searchTerm) {
      const s = searchTerm.toLowerCase();
      result = result.filter(
        (g) =>
          g.away_team?.toLowerCase().includes(s) ||
          g.home_team?.toLowerCase().includes(s) ||
          g.venue?.toLowerCase().includes(s)
      );
    }
    return result.map((game) => ({
      ...game,
      total_runs: Number(game.away_score ?? 0) + Number(game.home_score ?? 0),
    }));
  }, [games, levelFilter, leagueFilter, searchTerm]);

  const { items, sortConfig, requestSort } = useSortableData<SortableGame>(
    filtered,
    { key: "date_sort", direction: "desc" },
    "total_runs"
  );
  const pagination = usePagination(items, 100);

  const openClickableGame = (game: SortableGame) => {
    if (onGameClick && game.game_id) onGameClick(game);
  };

  return (
    <div className="panel">
      <div className="panel-header">
        <h2>All Games ({items.length})</h2>
      </div>
      <LevelLeagueFilter
        levelFilter={levelFilter}
        setLevelFilter={setLevelFilter}
        leagueFilter={leagueFilter}
        setLeagueFilter={setLeagueFilter}
        data={games}
        showSearch={true}
        searchTerm={searchTerm}
        setSearchTerm={setSearchTerm}
        searchPlaceholder="Search teams or venues..."
      />
      <div className="table-container">
        <table className="data-table">
          <thead>
            <tr>
              <SortableHeader
                label="Date"
                sortKey="date_sort"
                sortConfig={sortConfig}
                onSort={requestSort}
              />
              <SortableHeader
                label="Level"
                sortKey="level"
                sortConfig={sortConfig}
                onSort={requestSort}
              />
              <SortableHeader
                label="Away"
                sortKey="away_team"
                sortConfig={sortConfig}
                onSort={requestSort}
              />
              <SortableHeader
                label="Score"
                sortKey="total_runs"
                sortConfig={sortConfig}
                onSort={requestSort}
              />
              <SortableHeader
                label="Home"
                sortKey="home_team"
                sortConfig={sortConfig}
                onSort={requestSort}
              />
              <SortableHeader
                label="Venue"
                sortKey="venue"
                sortConfig={sortConfig}
                onSort={requestSort}
              />
            </tr>
          </thead>
          <tbody>
            {pagination.pageItems.map((g) => (
              <tr
                key={g.game_id ?? `${g.date_sort}-${g.away_team}-${g.home_team}`}
                className={onGameClick && g.game_id ? "clickable-row" : ""}
                tabIndex={onGameClick && g.game_id ? 0 : undefined}
                onClick={() => openClickableGame(g)}
                onKeyDown={(event) => {
                  if ((event.key === "Enter" || event.key === " ") && g.game_id) {
                    event.preventDefault();
                    openClickableGame(g);
                  }
                }}
                style={{
                  borderLeft: `4px solid ${levelColors[g.level] ?? "#ccc"}`,
                }}
              >
                <td>{formatDate(g.date)}</td>
                <td>
                  <LevelBadge level={g.level} levelColors={levelColors} />
                </td>
                <td>
                  <TeamCell
                    team={g.away_team ?? ""}
                    teamId={g.away_team_id}
                    level={g.level}
                    data={data}
                  />
                </td>
                <td className="text-center">
                  {onGameClick && g.game_id ? (
                    <button
                      type="button"
                      className="score-clickable"
                      onClick={(event) => {
                        event.stopPropagation();
                        onGameClick(g);
                      }}
                      title="View game details"
                      style={{ background: "none", border: "none", padding: 0, font: "inherit" }}
                    >
                      {g.away_score} - {g.home_score}
                    </button>
                  ) : (
                    <>
                      {g.away_score} - {g.home_score}
                    </>
                  )}
                </td>
                <td>
                  <TeamCell
                    team={g.home_team ?? ""}
                    teamId={g.home_team_id}
                    level={g.level}
                    data={data}
                  />
                </td>
                <td>{g.venue}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <PaginationControls {...pagination} />
    </div>
  );
}
