"use client";

import { Summary } from "@/types";

interface StatsGridProps {
  data: Summary;
}

export default function StatsGrid({ data }: StatsGridProps) {
  const totalGames = data.allGames ?? data.totalGames;
  const ncaaGames = data.totalGames ?? 0;
  const milbGames = data.milbGames ?? 0;

  return (
    <div className="stats-grid">
      <div className="stat-card featured">
        <div className="stat-card-icon">&#9918;</div>
        <div className="value">{totalGames}</div>
        <div className="label">Total Games</div>
        {ncaaGames > 0 && milbGames > 0 && (
          <div className="sub-label">{ncaaGames} NCAA / {milbGames} MiLB</div>
        )}
      </div>
      <div className="stat-card">
        <div className="stat-card-icon">&#128100;</div>
        <div className="value">
          {data.unifiedBatters ?? data.totalBatters + (data.milbBatters ?? 0)}
        </div>
        <div className="label">Batters</div>
      </div>
      <div className="stat-card">
        <div className="stat-card-icon">&#128170;</div>
        <div className="value">
          {data.unifiedPitchers ??
            data.totalPitchers + (data.milbPitchers ?? 0)}
        </div>
        <div className="label">Pitchers</div>
      </div>
      <div className="stat-card">
        <div className="stat-card-icon">&#127969;</div>
        <div className="value">{data.totalTeams}</div>
        <div className="label">Teams</div>
      </div>
      {data.crossoverPlayers > 0 && (
        <div className="stat-card">
          <div className="stat-card-icon">&#128256;</div>
          <div className="value">{data.crossoverPlayers}</div>
          <div className="label">Crossover Players</div>
        </div>
      )}
      <div className="stat-card">
        <div className="stat-card-icon">&#127942;</div>
        <div className="value">{data.totalMilestones ?? 0}</div>
        <div className="label">Milestones</div>
      </div>
    </div>
  );
}
