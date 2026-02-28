"use client";

import { useState, useMemo } from "react";
import { UnifiedGame, SiteData } from "@/types";
import LevelLeagueFilter from "@/components/shared/LevelLeagueFilter";
import LevelBadge from "@/components/shared/LevelBadge";
import TeamLogo from "@/components/shared/TeamLogo";
import { filterByLevelLeague } from "@/lib/filters";
import { formatDate } from "@/lib/baseball";
import { getTeamDisplayName } from "@/lib/data";

interface UnifiedGameLogProps {
  games: UnifiedGame[];
  data: SiteData;
}

interface TeamCellProps {
  team: string;
  teamId: number | undefined;
  level: string;
  data: SiteData;
}

function TeamCell({ team, teamId, level, data }: TeamCellProps) {
  const displayName = getTeamDisplayName(team, data);

  return (
    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
      <TeamLogo team={team} teamId={teamId} level={level} size={20} data={data} />
      <span>{displayName}</span>
    </div>
  );
}

export default function UnifiedGameLog({ games, data }: UnifiedGameLogProps) {
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
    return result;
  }, [games, levelFilter, leagueFilter, searchTerm]);

  return (
    <div className="panel">
      <div className="panel-header">
        <h2>All Games ({filtered.length})</h2>
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
              <th>Date</th>
              <th>Level</th>
              <th>Away</th>
              <th className="text-center">Score</th>
              <th>Home</th>
              <th>Venue</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((g, i) => (
              <tr
                key={i}
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
                  {g.away_score} - {g.home_score}
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
    </div>
  );
}
