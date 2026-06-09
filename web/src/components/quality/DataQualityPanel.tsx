"use client";

import type { DataQualityIssue, SiteData, SourceMergeGame } from "@/types";
import { formatDate } from "@/lib/baseball";
import LevelBadge from "@/components/shared/LevelBadge";
import PaginationControls from "@/components/shared/PaginationControls";
import { usePagination } from "@/hooks/usePagination";

interface DataQualityPanelProps {
  data: SiteData;
}

function formatSource(value?: string) {
  if (!value) return "Unknown";
  return value.replace(/^ncaa_/, "NCAA ").replace(/_/g, " ").toUpperCase();
}

function formatIssueValue(value: DataQualityIssue["primary_value"]) {
  if (value === undefined || value === null || value === "") return "-";
  return String(value);
}

function issueLabel(issue: DataQualityIssue) {
  const code = issue.code?.replace(/_/g, " ") ?? "source issue";
  const field = issue.field ? `: ${issue.field}` : "";
  return `${code}${field}`;
}

function reviewGameSortKey(game: SourceMergeGame) {
  return `${game.warning_count ? "0" : "1"}-${game.date_yyyymmdd ?? ""}-${game.game_id ?? ""}`;
}

function gameHref(gameId?: string) {
  return gameId ? `#games/${encodeURIComponent(gameId)}` : "#games";
}

function SourceLinks({ item }: { item: SourceMergeGame | DataQualityIssue }) {
  const detailPath = item.detail_path ?? (item.game_id ? `/games/${item.game_id}.json` : "");
  const hasLinks = item.game_id || detailPath || item.api_boxscore_url || item.api_play_by_play_url;
  if (!hasLinks) return <span className="quality-muted">-</span>;

  return (
    <div className="quality-actions" aria-label="Source links">
      {item.game_id && <a className="quality-link" href={gameHref(item.game_id)}>Open</a>}
      {detailPath && (
        <a className="quality-link" href={detailPath} target="_blank" rel="noreferrer">
          JSON
        </a>
      )}
      {item.api_boxscore_url && (
        <a className="quality-link" href={item.api_boxscore_url} target="_blank" rel="noreferrer">
          API
        </a>
      )}
      {item.api_play_by_play_url && (
        <a className="quality-link" href={item.api_play_by_play_url} target="_blank" rel="noreferrer">
          PBP
        </a>
      )}
    </div>
  );
}

export default function DataQualityPanel({ data }: DataQualityPanelProps) {
  const quality = data.dataQuality;
  const summary = quality?.summary;
  const metadata = data.dataMetadata;
  const schedule = metadata?.schedule;
  const reviewGames = [...(quality?.sourceMerge.games ?? [])].sort((a, b) =>
    reviewGameSortKey(a).localeCompare(reviewGameSortKey(b))
  );
  const issues = quality?.sourceMerge.issues ?? [];
  const warnings = issues.filter((issue) => issue.severity === "warning");
  const unmerged = quality?.sourceMerge.unmergedCandidates ?? [];
  const reviewPagination = usePagination(reviewGames, 100);
  const issuePagination = usePagination(issues, 100);

  return (
    <div className="quality-page">
      <div className="quality-grid">
        <div className="quality-card">
          <span className="quality-label">Generated</span>
          <strong>{metadata?.generated_at ? formatGenerated(metadata.generated_at) : "Unknown"}</strong>
        </div>
        <div className="quality-card">
          <span className="quality-label">Detail Files</span>
          <strong>{(metadata?.game_details_count ?? data.unifiedGameLog.length).toLocaleString()}</strong>
        </div>
        <div className="quality-card">
          <span className="quality-label">Source Merges</span>
          <strong>{(summary?.mergedSourceGames ?? 0).toLocaleString()}</strong>
        </div>
        <div className={`quality-card ${(summary?.sourceMergeWarnings ?? 0) > 0 ? "needs-review" : ""}`}>
          <span className="quality-label">Needs Review</span>
          <strong>{(summary?.sourceMergeReviewGames ?? 0).toLocaleString()}</strong>
        </div>
      </div>

      {schedule?.first_date && schedule?.last_date && (
        <div className="quality-note">
          <strong>Schedule coverage</strong>
          <span>
            {schedule.first_date} to {schedule.last_date}; {(schedule.total_games ?? 0).toLocaleString()} games in {(schedule.chunk_count ?? 0).toLocaleString()} daily chunks.
          </span>
        </div>
      )}

      {unmerged.length > 0 && (
        <div className="quality-note warning">
          <strong>{unmerged.length.toLocaleString()} same-date/team source candidate{unmerged.length === 1 ? "" : "s"} kept separate</strong>
          <span>These were not merged because scores or game identity did not line up cleanly.</span>
        </div>
      )}

      <div className="panel">
        <div className="panel-header">
          <h2>Source Review Games ({reviewGames.filter((game) => game.warning_count).length})</h2>
        </div>
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Game</th>
                <th>Level</th>
                <th>Stats</th>
                <th>Identity</th>
                <th className="text-center">Warnings</th>
                <th className="text-center">Info</th>
                <th>Sources</th>
              </tr>
            </thead>
            <tbody>
              {reviewPagination.pageItems.map((game) => (
                <tr key={game.game_id ?? `${game.date}-${game.away_team}-${game.home_team}`}>
                  <td>{formatDate(game.date ?? "")}</td>
                  <td>
                    <a className="quality-game-link" href={gameHref(game.game_id)}>
                      <strong>{game.away_team ?? "Unknown"}</strong>
                      <span className="quality-game-separator"> @ </span>
                      <strong>{game.home_team ?? "Unknown"}</strong>
                    </a>
                  </td>
                  <td>
                    <LevelBadge level={game.level ?? ""} levelColors={data.levelColors ?? {}} />
                  </td>
                  <td>{formatSource(game.stats_source)}</td>
                  <td>{formatSource(game.identity_source)}</td>
                  <td className="text-center">
                    <span className={game.warning_count ? "quality-pill warning" : "quality-pill"}>
                      {game.warning_count ?? 0}
                    </span>
                  </td>
                  <td className="text-center">{game.info_count ?? 0}</td>
                  <td><SourceLinks item={game} /></td>
                </tr>
              ))}
              {reviewGames.length === 0 && (
                <tr>
                  <td colSpan={8} className="text-center">No source merge records found.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <PaginationControls {...reviewPagination} />
      </div>

      <div className="panel">
        <div className="panel-header">
          <h2>Source Issues ({warnings.length} warnings, {issues.length} total)</h2>
        </div>
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Game</th>
                <th>Issue</th>
                <th>Primary</th>
                <th>Secondary</th>
                <th>Sources</th>
              </tr>
            </thead>
            <tbody>
              {issuePagination.pageItems.map((issue, index) => (
                <tr key={`${issue.game_id ?? "issue"}-${index}`}>
                  <td>{formatDate(issue.date ?? "")}</td>
                  <td>
                    <a className="quality-game-link" href={gameHref(issue.game_id)}>
                      {issue.away_team ?? "Unknown"} @ {issue.home_team ?? "Unknown"}
                    </a>
                  </td>
                  <td>
                    <span className={`quality-severity ${issue.severity === "warning" ? "warning" : ""}`}>
                      {issue.severity ?? "info"}
                    </span>
                    {issueLabel(issue)}
                  </td>
                  <td>{formatIssueValue(issue.primary_value)}</td>
                  <td>{formatIssueValue(issue.secondary_value)}</td>
                  <td><SourceLinks item={issue} /></td>
                </tr>
              ))}
              {issues.length === 0 && (
                <tr>
                  <td colSpan={6} className="text-center">No source issues reported.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <PaginationControls {...issuePagination} />
      </div>
    </div>
  );
}

function formatGenerated(value: string) {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value.replace("T", " ").slice(0, 19);
  return parsed.toLocaleString(undefined, {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}
