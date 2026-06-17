"use client";

import { useEffect, useMemo, useState } from "react";
import type {
  GameDetails,
  SiteData,
  UnifiedGame,
  BoxScoreBatter,
  BoxScorePitcher,
  PlayByPlayInning,
  DataQualityIssue,
} from "@/types";
import { formatDate } from "@/lib/baseball";
import { getTeamDisplayName } from "@/lib/data";
import { fetchJsonWithRetry } from "@/lib/fetchJson";
import LevelBadge from "@/components/shared/LevelBadge";
import TeamLogo from "@/components/shared/TeamLogo";

type Tab = "box" | "plays" | "pbp";

interface Props {
  game: UnifiedGame;
  onClose: () => void;
  onPrev?: () => void;
  onNext?: () => void;
  hasPrev?: boolean;
  hasNext?: boolean;
  data: SiteData;
  onPlayerClick?: (player: BoxScorePlayerClickRow, type: "batter" | "pitcher") => void;
}

type BoxScorePlayerClickRow = {
  name?: string;
  Player?: string;
  Team?: string;
  team?: string;
  bref_id?: string;
  Level?: string;
  level?: string;
  levels?: { level: string }[];
};

const num = (v: unknown) => {
  const n = parseInt(String(v ?? 0));
  return Number.isFinite(n) ? n : 0;
};

const pick = <T,>(...vals: (T | undefined | null)[]): T | undefined => {
  for (const v of vals) if (v !== undefined && v !== null) return v;
  return undefined;
};

const playerName = (row: BoxScoreBatter | BoxScorePitcher) =>
  String(pick(row.full_name, row.name, "") ?? "");

const battingTotal = (rows: BoxScoreBatter[], field: keyof BoxScoreBatter) =>
  rows.reduce((total, row) => total + num(row[field]), 0);

const pitchingTotal = (rows: BoxScorePitcher[], field: keyof BoxScorePitcher) =>
  rows.reduce((total, row) => total + num(row[field]), 0);

function formatBatterPosition(row: BoxScoreBatter) {
  const position = String(row.position ?? "").trim().toUpperCase();
  const order = String(row.batting_order ?? "").trim();
  if (position && order && order !== "0" && order !== "100") return `${order}-${position}`;
  return position || "";
}

function PlayerNameButton({
  name,
  row,
  teamName,
  level,
  type,
  onPlayerClick,
}: {
  name: string;
  row: BoxScoreBatter | BoxScorePitcher;
  teamName: string;
  level: string;
  type: "batter" | "pitcher";
  onPlayerClick?: Props["onPlayerClick"];
}) {
  if (!name) return null;
  return (
    <button
      type="button"
      className="gdm-player-link"
      onClick={() =>
        onPlayerClick?.(
          {
            name,
            Player: name,
            Team: row.team || teamName,
            team: row.team || teamName,
            bref_id: row.bref_id || "",
            Level: level,
            level,
            levels: [{ level }],
          },
          type
        )
      }
    >
      {name}
    </button>
  );
}

const SOURCE_LABELS: Record<string, string> = {
  ncaa_pdf: "NCAA PDF",
  ncaa_api: "NCAA API",
  milb: "MLB Stats API",
  partner: "Partner source",
};

function formatSource(source?: string) {
  if (!source) return "Unknown";
  return SOURCE_LABELS[source] ?? source.replace(/_/g, " ").toUpperCase();
}

function formatIssue(issue: DataQualityIssue) {
  const section = issue.section?.replace(/_/g, " ");
  const player = issue.player;
  const scope = [section, player].filter(Boolean).join(" · ");

  if (issue.code === "source_stat_disagreement") {
    return `${scope || "Stat"}: ${issue.field ?? "value"} ${formatSource(issue.primary_source)} ${issue.primary_value ?? "?"} vs ${formatSource(issue.secondary_source)} ${issue.secondary_value ?? "?"}`;
  }
  if (issue.code === "secondary_stat_field_unavailable") {
    return `${formatSource(issue.secondary_source)} missing ${issue.field ?? "stat"} values for ${section ?? "this section"}`;
  }
  if (issue.code === "api_only_player_row") {
    return `${formatSource(issue.secondary_source)} only row${player ? `: ${player}` : ""}`;
  }

  return [scope, issue.field, issue.code].filter(Boolean).join(" · ") || "Source issue";
}

function SourceQualityNote({ quality }: { quality: GameDetails["data_quality"] }) {
  const merge = quality?.source_merge;
  const candidate = quality?.source_candidate;
  if (!merge && !candidate) return null;

  const warnings = merge?.warning_count ?? 0;
  const infos = merge?.info_count ?? 0;
  const isWarning = warnings > 0 || merge?.confidence === "review";
  const issues = (merge?.issues ?? [])
    .filter((issue) => (isWarning ? issue.severity === "warning" : true))
    .slice(0, 3);

  return (
    <div className={`gdm-source-note${isWarning ? " warning" : ""}`}>
      <div className="gdm-source-summary">
        <strong>{isWarning ? "Source Review" : "Source Check"}</strong>
        {merge && (
          <>
            <span>Stats: {formatSource(merge.stats_source)}</span>
            <span>Identities: {formatSource(merge.identity_source)}</span>
            {merge.confidence && <span>Confidence: {merge.confidence}</span>}
          </>
        )}
        {warnings > 0 && <span className="quality-pill warning">{warnings} warnings</span>}
        {infos > 0 && <span className="quality-pill">{infos} info</span>}
      </div>
      {candidate && (
        <div className="gdm-source-candidate">
          Same-date/team source candidate kept separate
          {candidate.reason ? `: ${candidate.reason}` : ""}.
        </div>
      )}
      {issues.length > 0 && (
        <ul className="gdm-source-issues">
          {issues.map((issue, index) => (
            <li key={`${issue.code ?? "issue"}-${index}`}>{formatIssue(issue)}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

function BatterTable({
  rows,
  teamName,
  level,
  onPlayerClick,
}: {
  rows: BoxScoreBatter[];
  teamName: string;
  level: string;
  onPlayerClick?: Props["onPlayerClick"];
}) {
  if (!rows || rows.length === 0)
    return <div className="gdm-empty">No batting data</div>;
  const totals = {
    ab: battingTotal(rows, "ab") || battingTotal(rows, "at_bats"),
    r: battingTotal(rows, "r") || battingTotal(rows, "runs"),
    h: battingTotal(rows, "h") || battingTotal(rows, "hits"),
    rbi: battingTotal(rows, "rbi"),
    bb: battingTotal(rows, "bb") || battingTotal(rows, "walks"),
    k: battingTotal(rows, "k") || battingTotal(rows, "strikeouts"),
    doubles: battingTotal(rows, "doubles"),
    triples: battingTotal(rows, "triples"),
    hr: battingTotal(rows, "hr"),
    sb: battingTotal(rows, "sb"),
    lob: battingTotal(rows, "lob"),
  };
  return (
    <div className="table-container gdm-table-container">
      <table className="data-table gdm-box-table">
        <thead>
          <tr>
            <th className="gdm-name-col">Hitters</th>
            <th>Pos</th>
            <th>AB</th>
            <th>R</th>
            <th>H</th>
            <th>RBI</th>
            <th>BB</th>
            <th>K</th>
            <th>2B</th>
            <th>3B</th>
            <th>HR</th>
            <th>SB</th>
            <th>LOB</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => {
            const name = playerName(r);
            return (
              <tr key={`${name}-${i}`}>
                <td className="gdm-name-col">
                  <PlayerNameButton
                    name={name}
                    row={r}
                    teamName={teamName}
                    level={level}
                    type="batter"
                    onPlayerClick={onPlayerClick}
                  />
                </td>
                <td>{formatBatterPosition(r)}</td>
                <td>{num(pick(r.ab, r.at_bats))}</td>
                <td className="gdm-score-stat">{num(pick(r.r, r.runs))}</td>
                <td className="gdm-score-stat">{num(pick(r.h, r.hits))}</td>
                <td className="gdm-score-stat">{num(r.rbi)}</td>
                <td>{num(pick(r.bb, r.walks))}</td>
                <td>{num(pick(r.k, r.strikeouts))}</td>
                <td>{num(r.doubles)}</td>
                <td>{num(r.triples)}</td>
                <td className={num(r.hr) > 0 ? "gdm-score-stat" : ""}>{num(r.hr)}</td>
                <td>{num(r.sb)}</td>
                <td>{num(r.lob)}</td>
              </tr>
            );
          })}
        </tbody>
        <tfoot>
          <tr>
            <td className="gdm-name-col">Totals</td>
            <td></td>
            <td>{totals.ab}</td>
            <td className="gdm-score-stat">{totals.r}</td>
            <td className="gdm-score-stat">{totals.h}</td>
            <td className="gdm-score-stat">{totals.rbi}</td>
            <td>{totals.bb}</td>
            <td>{totals.k}</td>
            <td>{totals.doubles}</td>
            <td>{totals.triples}</td>
            <td className={totals.hr > 0 ? "gdm-score-stat" : ""}>{totals.hr}</td>
            <td>{totals.sb}</td>
            <td>{totals.lob}</td>
          </tr>
        </tfoot>
      </table>
    </div>
  );
}

function PitcherTable({
  rows,
  teamName,
  level,
  onPlayerClick,
}: {
  rows: BoxScorePitcher[];
  teamName: string;
  level: string;
  onPlayerClick?: Props["onPlayerClick"];
}) {
  if (!rows || rows.length === 0)
    return <div className="gdm-empty">No pitching data</div>;
  const totals = {
    h: pitchingTotal(rows, "h"),
    r: pitchingTotal(rows, "r"),
    er: pitchingTotal(rows, "er"),
    bb: pitchingTotal(rows, "bb"),
    k: pitchingTotal(rows, "k"),
    hr: pitchingTotal(rows, "hr"),
    np: pitchingTotal(rows, "np"),
  };
  return (
    <div className="table-container gdm-table-container">
      <table className="data-table gdm-box-table gdm-pitching-table">
        <thead>
          <tr>
            <th className="gdm-name-col">Pitchers</th>
            <th>IP</th>
            <th>H</th>
            <th>R</th>
            <th>ER</th>
            <th>BB</th>
            <th>K</th>
            <th>HR</th>
            <th>NP</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => {
            const name = playerName(r);
            return (
              <tr key={`${name}-${i}`}>
                <td className="gdm-name-col">
                  <PlayerNameButton
                    name={name}
                    row={r}
                    teamName={teamName}
                    level={level}
                    type="pitcher"
                    onPlayerClick={onPlayerClick}
                  />
                </td>
                <td className="gdm-score-stat">{String(r.ip ?? "")}</td>
                <td>{num(r.h)}</td>
                <td>{num(r.r)}</td>
                <td>{num(r.er)}</td>
                <td>{num(r.bb)}</td>
                <td className="gdm-score-stat">{num(r.k)}</td>
                <td>{num(r.hr)}</td>
                <td>{num(r.np)}</td>
              </tr>
            );
          })}
        </tbody>
        <tfoot>
          <tr>
            <td className="gdm-name-col">Totals</td>
            <td></td>
            <td>{totals.h}</td>
            <td>{totals.r}</td>
            <td>{totals.er}</td>
            <td>{totals.bb}</td>
            <td className="gdm-score-stat">{totals.k}</td>
            <td>{totals.hr}</td>
            <td>{totals.np}</td>
          </tr>
        </tfoot>
      </table>
    </div>
  );
}

function TeamBlock({
  label,
  teamName,
  teamId,
  level,
  batters,
  pitchers,
  data,
  onPlayerClick,
}: {
  label: string;
  teamName: string;
  teamId?: number;
  level: string;
  batters: BoxScoreBatter[];
  pitchers: BoxScorePitcher[];
  data: SiteData;
  onPlayerClick?: Props["onPlayerClick"];
}) {
  return (
    <div className="gdm-team-block">
      <div className="gdm-team-header">
        <TeamLogo team={teamName} teamId={teamId} level={level} size={22} data={data} />
        <span className="gdm-team-label">{label}</span>
        <strong>{getTeamDisplayName(teamName, data)}</strong>
      </div>
      <div className="gdm-subhead">Batting</div>
      <BatterTable
        rows={batters}
        teamName={teamName}
        level={level}
        onPlayerClick={onPlayerClick}
      />
      <div className="gdm-subhead">Pitching</div>
      <PitcherTable
        rows={pitchers}
        teamName={teamName}
        level={level}
        onPlayerClick={onPlayerClick}
      />
    </div>
  );
}

function KeyPlays({ notes }: { notes: GameDetails["game_notes"] }) {
  if (!notes)
    return <div className="gdm-empty">No key plays available for this game.</div>;

  const sections: { label: string; rows: { player?: string; season_total?: number; game_count?: number }[] }[] = [
    { label: "Home Runs", rows: notes.home_runs ?? [] },
    { label: "Doubles", rows: notes.doubles ?? [] },
    { label: "Triples", rows: notes.triples ?? [] },
    { label: "Stolen Bases", rows: notes.stolen_bases ?? [] },
  ].filter((s) => s.rows.length > 0);

  if (sections.length === 0)
    return <div className="gdm-empty">No key plays recorded for this game.</div>;

  return (
    <div>
      {sections.map((s) => (
        <div key={s.label} className="gdm-plays-section">
          <h4>{s.label}</h4>
          <ul className="gdm-play-list">
            {s.rows.map((r, i) => (
              <li key={i}>
                <strong>{r.player}</strong>
                {r.game_count && r.game_count > 1 ? ` (${r.game_count}x)` : ""}
                {r.season_total ? ` — season total: ${r.season_total}` : ""}
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}

function PlayByPlay({ pbp }: { pbp: Record<string, PlayByPlayInning> | undefined }) {
  if (!pbp || Object.keys(pbp).length === 0)
    return <div className="gdm-empty">Play-by-play not available for this game.</div>;

  const innings = Object.keys(pbp)
    .map((k) => parseInt(k, 10))
    .filter((n) => !Number.isNaN(n))
    .sort((a, b) => a - b);

  return (
    <div className="gdm-pbp">
      {innings.map((n) => {
        const inning = pbp[String(n)] ?? {};
        const top = inning.top ?? [];
        const bot = inning.bottom ?? [];
        if (top.length === 0 && bot.length === 0) return null;
        return (
          <div key={n} className="gdm-inning">
            <div className="gdm-inning-header">Inning {n}</div>
            {top.length > 0 && (
              <div className="gdm-half">
                <div className="gdm-half-label">Top</div>
                <ul className="gdm-pbp-list">
                  {top.map((ev, i) => (
                    <li key={i}>{ev.description}</li>
                  ))}
                </ul>
              </div>
            )}
            {bot.length > 0 && (
              <div className="gdm-half">
                <div className="gdm-half-label">Bottom</div>
                <ul className="gdm-pbp-list">
                  {bot.map((ev, i) => (
                    <li key={i}>{ev.description}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

export default function GameDetailsModal({
  game,
  onClose,
  onPrev,
  onNext,
  hasPrev,
  hasNext,
  data,
  onPlayerClick,
}: Props) {
  const levelColors = data.levelColors ?? {};
  const [fetchedDetails, setFetchedDetails] = useState<{
    gameId: string;
    details: GameDetails | null;
    error: string | null;
  }>({ gameId: "", details: null, error: null });
  const [tab, setTab] = useState<Tab>("box");
  const gameId = game.game_id ?? "";
  const embeddedDetails = gameId ? data.gameDetails?.[gameId] : undefined;
  const fetchedForGame = fetchedDetails.gameId === gameId ? fetchedDetails : null;
  const details = embeddedDetails ?? fetchedForGame?.details ?? null;
  const error = fetchedForGame?.error ?? null;
  const loading = Boolean(gameId && !embeddedDetails && !fetchedForGame);

  useEffect(() => {
    if (!gameId || embeddedDetails || fetchedDetails.gameId === gameId) return;
    let cancelled = false;
    fetchJsonWithRetry<GameDetails>(`/games/${gameId}.json`)
      .then((d: GameDetails) => {
        if (!cancelled) {
          setFetchedDetails({ gameId, details: d, error: null });
        }
      })
      .catch((e) => {
        if (!cancelled) {
          setFetchedDetails({ gameId, details: null, error: String(e) });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [gameId, embeddedDetails, fetchedDetails.gameId]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      else if (e.key === "ArrowLeft" && hasPrev) onPrev?.();
      else if (e.key === "ArrowRight" && hasNext) onNext?.();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose, onPrev, onNext, hasPrev, hasNext]);

  const box = details?.box_score;
  const notes = details?.game_notes;
  const pbp = details?.play_by_play;

  const hasBox = useMemo(
    () =>
      (box?.away_batting?.length || 0) +
        (box?.home_batting?.length || 0) +
        (box?.away_pitching?.length || 0) +
        (box?.home_pitching?.length || 0) >
      0,
    [box]
  );

  const hasKeyPlays = useMemo(() => {
    if (!notes) return false;
    return (
      (notes.home_runs?.length || 0) +
        (notes.doubles?.length || 0) +
        (notes.triples?.length || 0) +
        (notes.stolen_bases?.length || 0) >
        0
    );
  }, [notes]);

  const hasPbp = useMemo(() => {
    if (!pbp) return false;
    return Object.values(pbp).some(
      (i) => (i.top?.length || 0) + (i.bottom?.length || 0) > 0
    );
  }, [pbp]);

  const activeTab: Tab =
    (tab === "plays" && !hasKeyPlays) || (tab === "pbp" && !hasPbp)
      ? "box"
      : tab;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className="modal-content gdm-modal"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal-header">
          <div style={{ flex: 1 }}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "12px",
                flexWrap: "wrap",
              }}
            >
              <LevelBadge level={game.level} levelColors={levelColors} />
              <span style={{ opacity: 0.85 }}>{formatDate(game.date)}</span>
              {game.venue && (
                <span style={{ opacity: 0.7, fontSize: "0.85rem" }}>
                  · {game.venue}
                </span>
              )}
            </div>
            <h3 style={{ margin: "6px 0 0 0", fontSize: "1.1rem" }}>
              <span>
                <TeamLogo
                  team={game.away_team}
                  teamId={game.away_team_id}
                  level={game.level}
                  size={18}
                  data={data}
                />{" "}
                {getTeamDisplayName(game.away_team, data)}{" "}
                <strong>{game.away_score}</strong>
              </span>
              <span style={{ margin: "0 8px", opacity: 0.6 }}>@</span>
              <span>
                <TeamLogo
                  team={game.home_team}
                  teamId={game.home_team_id}
                  level={game.level}
                  size={18}
                  data={data}
                />{" "}
                {getTeamDisplayName(game.home_team, data)}{" "}
                <strong>{game.home_score}</strong>
              </span>
            </h3>
          </div>
          <div style={{ display: "flex", gap: "6px", alignItems: "center" }}>
            <button
              className="gdm-nav"
              onClick={onPrev}
              disabled={!hasPrev}
              title="Previous game (←)"
              aria-label="Previous game"
            >
              ‹
            </button>
            <button
              className="gdm-nav"
              onClick={onNext}
              disabled={!hasNext}
              title="Next game (→)"
              aria-label="Next game"
            >
              ›
            </button>
            <button className="modal-close" onClick={onClose} aria-label="Close">
              &times;
            </button>
          </div>
        </div>

        <div className="modal-body">
          {!gameId && (
            <div className="gdm-empty">
              Detailed box score is not available for this game.
            </div>
          )}
          {gameId && loading && (
            <div className="gdm-empty">Loading game details…</div>
          )}
          {gameId && error && (
            <div className="gdm-empty">
              Could not load game details ({error}).
            </div>
          )}

          {details && (
            <>
              {(details.attendance || details.weather || details.duration || details.start_time) && (
                <div className="gdm-meta-row">
                  {details.start_time && <span>Start: {details.start_time}</span>}
                  {details.attendance && <span>Attendance: {details.attendance}</span>}
                  {details.weather && <span>Weather: {details.weather}</span>}
                  {details.duration && <span>Duration: {details.duration}</span>}
                </div>
              )}

              <SourceQualityNote quality={details.data_quality} />

              <div className="gdm-tabs">
                <button
                  className={`gdm-tab ${activeTab === "box" ? "active" : ""}`}
                  onClick={() => setTab("box")}
                  disabled={!hasBox}
                >
                  Box Score
                </button>
                {hasKeyPlays && (
                  <button
                    className={`gdm-tab ${activeTab === "plays" ? "active" : ""}`}
                    onClick={() => setTab("plays")}
                  >
                    Key Plays
                  </button>
                )}
                {hasPbp && (
                  <button
                    className={`gdm-tab ${activeTab === "pbp" ? "active" : ""}`}
                    onClick={() => setTab("pbp")}
                  >
                    Play-by-Play
                  </button>
                )}
              </div>

              <div className="gdm-tab-content">
                {activeTab === "box" && (
                  hasBox ? (
                    <>
                      <TeamBlock
                        label="Away"
                        teamName={game.away_team}
                        teamId={game.away_team_id}
                        level={game.level}
                        batters={box?.away_batting ?? []}
                        pitchers={box?.away_pitching ?? []}
                        data={data}
                        onPlayerClick={onPlayerClick}
                      />
                      <TeamBlock
                        label="Home"
                        teamName={game.home_team}
                        teamId={game.home_team_id}
                        level={game.level}
                        batters={box?.home_batting ?? []}
                        pitchers={box?.home_pitching ?? []}
                        data={data}
                        onPlayerClick={onPlayerClick}
                      />
                    </>
                  ) : (
                    <div className="gdm-empty">No box score available.</div>
                  )
                )}
                {activeTab === "plays" && <KeyPlays notes={notes} />}
                {activeTab === "pbp" && <PlayByPlay pbp={pbp} />}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
