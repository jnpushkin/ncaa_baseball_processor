"use client";

import { useMemo, useState } from "react";
import {
  SiteData,
  ChecklistConference,
  MilbChecklistLevel,
  MilbChecklistTeam,
} from "@/types";
import LevelBadge from "@/components/shared/LevelBadge";
import TeamLogo from "@/components/shared/TeamLogo";
import { getTeamDisplayName } from "@/lib/teams";

// ---------------------------------------------------------------------------
// ProgressBar helper
// ---------------------------------------------------------------------------

function ProgressBar({
  pct,
  color,
  small = false,
}: {
  pct: number;
  color: string;
  small?: boolean;
}) {
  return (
    <div className={`progress-bar${small ? " progress-bar--sm" : ""}`}>
      <div
        className="progress-bar-fill"
        style={{ width: `${pct}%`, background: color }}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// ProTeamCard – renders a single MiLB/Partner team tile
// ---------------------------------------------------------------------------

interface ProTeamCardProps {
  teamEntry: MilbChecklistTeam;
  status: "home" | "away" | "none";
  localLogos: Record<string, string>;
}

function ProTeamCard({
  teamEntry,
  status,
  localLogos,
}: ProTeamCardProps) {
  const { team, venue, logo } = teamEntry;
  const resolvedLogo = localLogos[team] || logo;

  return (
    <div className={`pro-team-card pro-team-card--${status}`}>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={resolvedLogo}
        alt=""
        className="pro-team-card-logo"
        onError={(e) => {
          (e.target as HTMLImageElement).style.display = "none";
        }}
      />
      <div className="pro-team-card-info">
        <div className="pro-team-card-name">{team}</div>
        <div className="pro-team-card-venue">{venue}</div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// NcaaTeamChip – renders a compact NCAA checklist team with logo
// ---------------------------------------------------------------------------

interface NcaaTeamChipProps {
  team: string;
  status: "home" | "away" | "none";
  data: SiteData;
}

function NcaaTeamChip({ team, status, data }: NcaaTeamChipProps) {
  const displayName = getTeamDisplayName(
    team,
    data.ncaaTeamNicknames ?? {},
    data.ncaaTeamLogos ?? {}
  );

  return (
    <div className={`team-chip team-chip--${status}`}>
      <span className={`team-chip-logo team-chip-logo--${status}`}>
        <TeamLogo team={team} level="NCAA" size={22} data={data} />
      </span>
      <span className="team-chip-name">{displayName}</span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Checklist component
// ---------------------------------------------------------------------------

export interface ChecklistProps {
  checklist: Record<string, ChecklistConference>;
  milbChecklist: Record<string, MilbChecklistLevel>;
  data: SiteData;
}

export default function Checklist({
  checklist,
  milbChecklist,
  data,
}: ChecklistProps) {
  const [expandedSection, setExpandedSection] = useState<string | null>(null);
  const [expandedLeague, setExpandedLeague] = useState<string | null>(null);

  const levelColors = data.levelColors ?? {};
  const levelOrder = data.levelOrder ?? [
    "NCAA",
    "Triple-A",
    "Double-A",
    "High-A",
    "Single-A",
    "Independent",
  ];
  const localLogos = data.localLogos ?? {};

  const ncaaStats = useMemo(() => {
    let totalTeams = 0, totalSeen = 0, totalVisited = 0;
    Object.values(checklist ?? {}).forEach((c) => {
      totalTeams += c.total;
      totalSeen += c.seen;
      totalVisited += c.visited;
    });
    return { total: totalTeams, seen: totalSeen, visited: totalVisited };
  }, [checklist]);

  const proStats = useMemo(() => {
    let totalTeams = 0, totalSeen = 0, totalVisited = 0;
    Object.values(milbChecklist ?? {}).forEach((c) => {
      totalTeams += c.total;
      totalSeen += c.seen;
      totalVisited += c.visited;
    });
    return { total: totalTeams, seen: totalSeen, visited: totalVisited };
  }, [milbChecklist]);

  const grandTotal = {
    total: ncaaStats.total + proStats.total,
    seen: ncaaStats.seen + proStats.seen,
    visited: ncaaStats.visited + proStats.visited,
  };

  const toggleSection = (key: string) => {
    setExpandedSection(expandedSection === key ? null : key);
    setExpandedLeague(null);
  };

  const toggleLeague = (key: string) => {
    setExpandedLeague(expandedLeague === key ? null : key);
  };

  const ncaaConferences = useMemo(
    () => Object.keys(checklist ?? {}).sort(),
    [checklist]
  );

  const proLevels = levelOrder.filter(
    (l) => l !== "NCAA" && milbChecklist && milbChecklist[l]
  );

  return (
    <div className="panel">
      <div className="panel-header">
        <h2>Team Checklist</h2>
      </div>
      <div className="panel-body">
        {/* Grand total stat boxes */}
        <div className="checklist-stats">
          <div className="checklist-stat-box">
            <div className="checklist-stat-value" style={{ color: "#1e3a5f" }}>
              {grandTotal.seen}/{grandTotal.total}
            </div>
            <div className="checklist-stat-label">Teams Seen</div>
          </div>
          <div className="checklist-stat-box">
            <div className="checklist-stat-value" style={{ color: "#28a745" }}>
              {grandTotal.visited}
            </div>
            <div className="checklist-stat-label">Stadiums Visited</div>
          </div>
          <div className="checklist-stat-box">
            <div className="checklist-stat-value">
              {grandTotal.total > 0
                ? Math.round((grandTotal.seen / grandTotal.total) * 100)
                : 0}%
            </div>
            <div className="checklist-stat-label">Progress</div>
          </div>
        </div>

        {/* Per-level summary pills */}
        <div className="checklist-level-pills">
          <span
            className="checklist-level-pill"
            style={{ background: levelColors["NCAA"] ?? "#28a745" }}
          >
            NCAA: {ncaaStats.seen}/{ncaaStats.total}
          </span>
          {proLevels.map((level) => {
            const lvlData = milbChecklist[level] ?? { total: 0, seen: 0 };
            return (
              <span
                key={level}
                className="checklist-level-pill"
                style={{ background: levelColors[level] ?? "#666" }}
              >
                {level}: {lvlData.seen}/{lvlData.total}
              </span>
            );
          })}
        </div>

        {/* Accordion sections */}
        <div className="accordion">
          {/* NCAA section */}
          <div className="accordion-item accordion-item--level" style={{ borderLeftColor: levelColors["NCAA"] ?? "#28a745" }}>
            <button
              className="accordion-trigger"
              onClick={() => toggleSection("NCAA")}
            >
              <div className="accordion-trigger-left">
                <span className={`accordion-chevron${expandedSection === "NCAA" ? " open" : ""}`}>&#9654;</span>
                <LevelBadge level="NCAA" levelColors={levelColors} />
                <span className="accordion-title">NCAA</span>
              </div>
              <div className="accordion-trigger-right">
                <span className="accordion-meta">
                  {ncaaStats.seen}/{ncaaStats.total} seen
                </span>
                <ProgressBar
                  pct={ncaaStats.total > 0 ? Math.round((ncaaStats.seen / ncaaStats.total) * 100) : 0}
                  color={levelColors["NCAA"] ?? "#28a745"}
                />
                <span className="accordion-pct">
                  {ncaaStats.total > 0 ? Math.round((ncaaStats.seen / ncaaStats.total) * 100) : 0}%
                </span>
              </div>
            </button>

            {expandedSection === "NCAA" && (
              <div className="accordion-body">
                <div className="sub-accordion">
                  {ncaaConferences.map((conf) => {
                    const confData: ChecklistConference = checklist[conf] ?? {
                      teams: [], total: 0, seen: 0, visited: 0, teamStatus: {},
                    };
                    const isLeagueExpanded = expandedLeague === "ncaa-" + conf;
                    const pct = confData.total > 0
                      ? Math.round((confData.seen / confData.total) * 100) : 0;
                    return (
                      <div key={conf}>
                        <button
                          className="sub-accordion-trigger"
                          onClick={() => toggleLeague("ncaa-" + conf)}
                        >
                          <div className="accordion-trigger-left">
                            <span className={`accordion-chevron${isLeagueExpanded ? " open" : ""}`}>&#9654;</span>
                            <span className="sub-accordion-title">{conf}</span>
                          </div>
                          <div className="accordion-trigger-right">
                            <span className="accordion-meta">
                              {confData.seen}/{confData.total}
                            </span>
                            <ProgressBar pct={pct} color="#28a745" small />
                          </div>
                        </button>

                        {isLeagueExpanded && (
                          <div className="sub-accordion-body">
                            <div className="team-grid">
                              {[...confData.teams].sort().map((team) => {
                                const status = confData.teamStatus[team] ?? "none";
                                return (
                                  <NcaaTeamChip
                                    key={team}
                                    team={team}
                                    status={status}
                                    data={data}
                                  />
                                );
                              })}
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>

          {/* Pro level sections */}
          {proLevels.map((level) => {
            const levelData: MilbChecklistLevel = milbChecklist[level] ?? {
              teams: [], total: 0, seen: 0, visited: 0, teamStatus: {}, leagues: {},
            };
            const isExpanded = expandedSection === level;
            const levelPct = levelData.total > 0
              ? Math.round((levelData.seen / levelData.total) * 100) : 0;
            const leagues = levelData.leagues ? Object.keys(levelData.leagues).sort() : [];
            const levelColor = levelColors[level] ?? "#666";

            return (
              <div key={level} className="accordion-item accordion-item--level" style={{ borderLeftColor: levelColor }}>
                <button
                  className="accordion-trigger"
                  onClick={() => toggleSection(level)}
                >
                  <div className="accordion-trigger-left">
                    <span className={`accordion-chevron${isExpanded ? " open" : ""}`}>&#9654;</span>
                    <LevelBadge level={level} levelColors={levelColors} />
                    <span className="accordion-title">{level}</span>
                  </div>
                  <div className="accordion-trigger-right">
                    <span className="accordion-meta">
                      {levelData.seen}/{levelData.total} seen
                    </span>
                    <ProgressBar pct={levelPct} color={levelColor} />
                    <span className="accordion-pct">{levelPct}%</span>
                  </div>
                </button>

                {isExpanded && (
                  <div className="accordion-body">
                    {leagues.length > 1 ? (
                      <div className="sub-accordion">
                        {leagues.map((league) => {
                          const lgData = levelData.leagues[league] ?? {
                            teams: [], total: 0, seen: 0, visited: 0, teamStatus: {},
                          };
                          const isLgExpanded = expandedLeague === level + "-" + league;
                          const lgPct = lgData.total > 0
                            ? Math.round((lgData.seen / lgData.total) * 100) : 0;
                          return (
                            <div key={league}>
                              <button
                                className="sub-accordion-trigger"
                                onClick={() => toggleLeague(level + "-" + league)}
                              >
                                <div className="accordion-trigger-left">
                                  <span className={`accordion-chevron${isLgExpanded ? " open" : ""}`}>&#9654;</span>
                                  <span className="sub-accordion-title">{league}</span>
                                </div>
                                <div className="accordion-trigger-right">
                                  <span className="accordion-meta">
                                    {lgData.seen}/{lgData.total}
                                  </span>
                                  <ProgressBar pct={lgPct} color={levelColor} small />
                                </div>
                              </button>

                              {isLgExpanded && (
                                <div className="sub-accordion-body">
                                  <div className="team-grid team-grid--wide">
                                    {[...lgData.teams]
                                      .sort((a, b) => a.team.localeCompare(b.team))
                                      .map((teamEntry) => (
                                        <ProTeamCard
                                          key={teamEntry.team}
                                          teamEntry={teamEntry}
                                          status={lgData.teamStatus[teamEntry.team] ?? "none"}
                                          localLogos={localLogos}
                                        />
                                      ))}
                                  </div>
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    ) : (
                      <div style={{ padding: "10px 12px" }}>
                        <div className="team-grid team-grid--wide">
                          {[...levelData.teams]
                            .sort((a, b) => a.team.localeCompare(b.team))
                            .map((teamEntry) => (
                              <ProTeamCard
                                key={teamEntry.team}
                                teamEntry={teamEntry}
                                status={levelData.teamStatus[teamEntry.team] ?? "none"}
                                localLogos={localLogos}
                              />
                            ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Legend */}
        <div className="legend">
          {[
            { color: "#28a745", label: "Visited (Home)" },
            { color: "#1976d2", label: "Seen (Away)" },
            { color: "#ccc", label: "Not Seen" },
          ].map(({ color, label }) => (
            <span key={label} className="legend-item">
              <span className="legend-dot" style={{ background: color }} />
              {label}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
