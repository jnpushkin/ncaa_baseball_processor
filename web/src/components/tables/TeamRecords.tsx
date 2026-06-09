"use client";

import { useState, useMemo } from "react";
import { TeamRecord, SiteData } from "@/types";
import LevelBadge from "@/components/shared/LevelBadge";
import LevelLeagueFilter from "@/components/shared/LevelLeagueFilter";
import SortableHeader from "@/components/shared/SortableHeader";
import PaginationControls from "@/components/shared/PaginationControls";
import { useSortableData } from "@/hooks/useSortableData";
import { usePagination } from "@/hooks/usePagination";
import { filterByLevelLeague } from "@/lib/filters";
import { getTeamDisplayName } from "@/lib/data";

interface TeamRecordsProps {
  teams: TeamRecord[];
  data: SiteData;
}

export default function TeamRecords({ teams, data }: TeamRecordsProps) {
  const [levelFilter, setLevelFilter] = useState("All");
  const [leagueFilter, setLeagueFilter] = useState("All");
  const [searchTerm, setSearchTerm] = useState("");

  const levelColors = data.levelColors ?? {};

  const filtered = useMemo(() => {
    if (!teams) return [];
    let result = filterByLevelLeague(teams, levelFilter, leagueFilter);
    if (searchTerm) {
      const s = searchTerm.toLowerCase();
      result = result.filter(
        (team) =>
          team.Team?.toLowerCase().includes(s) ||
          team.League?.toLowerCase().includes(s)
      );
    }
    return result;
  }, [teams, levelFilter, leagueFilter, searchTerm]);

  const { items, sortConfig, requestSort } = useSortableData(filtered, {
    key: "W",
    direction: "desc",
  });
  const pagination = usePagination(items, 100);

  return (
    <div className="panel">
      <div className="panel-header">
        <h2>Team Records ({filtered.length})</h2>
      </div>
      <LevelLeagueFilter
        levelFilter={levelFilter}
        setLevelFilter={setLevelFilter}
        leagueFilter={leagueFilter}
        setLeagueFilter={setLeagueFilter}
        data={teams}
        showSearch
        searchTerm={searchTerm}
        setSearchTerm={setSearchTerm}
        searchPlaceholder="Search teams or leagues..."
      />
      <div className="table-container">
        <table className="data-table">
          <thead>
            <tr>
              <SortableHeader
                label="Level"
                sortKey="Level"
                sortConfig={sortConfig}
                onSort={requestSort}
              />
              <SortableHeader
                label="Team"
                sortKey="Team"
                sortConfig={sortConfig}
                onSort={requestSort}
              />
              <SortableHeader
                label="League"
                sortKey="League"
                sortConfig={sortConfig}
                onSort={requestSort}
              />
              <SortableHeader
                label="W"
                sortKey="W"
                sortConfig={sortConfig}
                onSort={requestSort}
              />
              <SortableHeader
                label="L"
                sortKey="L"
                sortConfig={sortConfig}
                onSort={requestSort}
              />
              <SortableHeader
                label="Win%"
                sortKey="Win%"
                sortConfig={sortConfig}
                onSort={requestSort}
              />
              <SortableHeader
                label="RS"
                sortKey="RS"
                sortConfig={sortConfig}
                onSort={requestSort}
              />
              <SortableHeader
                label="RA"
                sortKey="RA"
                sortConfig={sortConfig}
                onSort={requestSort}
              />
              <SortableHeader
                label="Diff"
                sortKey="Diff"
                sortConfig={sortConfig}
                onSort={requestSort}
              />
            </tr>
          </thead>
          <tbody>
            {pagination.pageItems.map((t, i) => (
              <tr key={`${t.Team}-${t.Level}-${pagination.start + i}`}>
                <td>
                  <LevelBadge level={t.Level} levelColors={levelColors} />
                </td>
                <td>{getTeamDisplayName(t.Team, data)}</td>
                <td>{t.League}</td>
                <td className="text-center">{t.W}</td>
                <td className="text-center">{t.L}</td>
                <td className="text-center">{t["Win%"]}</td>
                <td className="text-center">{t.RS}</td>
                <td className="text-center">{t.RA}</td>
                <td className="text-center">
                  {t.Diff > 0 ? "+" : ""}
                  {t.Diff}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <PaginationControls {...pagination} />
    </div>
  );
}
