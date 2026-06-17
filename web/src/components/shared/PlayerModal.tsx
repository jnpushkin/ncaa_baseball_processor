"use client";

import { useMemo } from "react";
import { NormalizedPlayer, PlayerGame, MilestoneEntry, SiteData, UnifiedBatter, UnifiedPitcher } from "@/types";
import { addIP, ipToInnings, formatDate } from "@/lib/baseball";
import { getTeamDisplayName } from "@/lib/data";
import { BREF_BASE } from "@/lib/constants";
import { milestoneStatChips } from "@/lib/milestones";
import LevelBadge from "./LevelBadge";

interface PlayerModalProps {
  player: NormalizedPlayer;
  games: PlayerGame[];
  type: "batter" | "pitcher";
  milestones?: (MilestoneEntry & { milestoneType?: string })[];
  onClose: () => void;
  data: SiteData;
  unifiedStats?: UnifiedBatter | UnifiedPitcher | null;
  onGameClick?: (game: PlayerGame) => void;
}

type BatterSummary = {
  kind: "batter";
  g: number;
  ab: number;
  h: number;
  hr: number;
  rbi: number;
  bb: number;
  k: number;
  avg: string;
};

type PitcherSummary = {
  kind: "pitcher";
  g: number;
  ip: number;
  h: number;
  er: number;
  bb: number;
  k: number;
  era: string;
};

type PlayerSummary = BatterSummary | PitcherSummary;

export default function PlayerModal({
  player,
  games,
  type,
  milestones,
  onClose,
  data,
  unifiedStats,
  onGameClick,
}: PlayerModalProps) {
  const isBatter = type === "batter";
  const levelColors = data.levelColors ?? {};

  const summary = useMemo<PlayerSummary | null>(() => {
    if (games && games.length > 0) {
      if (isBatter) {
        const g = games.length;
        const ab = games.reduce((s, x) => s + (parseInt(String(x.ab ?? 0)) || 0), 0);
        const h = games.reduce((s, x) => s + (parseInt(String(x.h ?? 0)) || 0), 0);
        const hr = games.reduce((s, x) => s + (parseInt(String(x.hr ?? 0)) || 0), 0);
        const rbi = games.reduce((s, x) => s + (parseInt(String(x.rbi ?? 0)) || 0), 0);
        const bb = games.reduce((s, x) => s + (parseInt(String(x.bb ?? 0)) || 0), 0);
        const k = games.reduce((s, x) => s + (parseInt(String(x.k ?? 0)) || 0), 0);
        const avg = ab > 0 ? (h / ab).toFixed(3) : ".000";
        return { kind: "batter", g, ab, h, hr, rbi, bb, k, avg };
      } else {
        const g = games.length;
        const ip = addIP(games.map((x) => x.ip ?? 0));
        const h = games.reduce((s, x) => s + (parseInt(String(x.h ?? 0)) || 0), 0);
        const er = games.reduce((s, x) => s + (parseInt(String(x.er ?? 0)) || 0), 0);
        const bb = games.reduce((s, x) => s + (parseInt(String(x.bb ?? 0)) || 0), 0);
        const k = games.reduce((s, x) => s + (parseInt(String(x.k ?? 0)) || 0), 0);
        const inn = ipToInnings(ip);
        const era = inn > 0 ? ((er * 9) / inn).toFixed(2) : "0.00";
        return { kind: "pitcher", g, ip, h, er, bb, k, era };
      }
    }
    // Fallback to unified season stats when no game log available
    if (unifiedStats) {
      if (isBatter) {
        const b = unifiedStats as UnifiedBatter;
        return { kind: "batter", g: b.g, ab: b.ab, h: b.h, hr: b.hr, rbi: b.rbi, bb: b.bb, k: b.k, avg: b.avg };
      } else {
        const p = unifiedStats as UnifiedPitcher;
        return { kind: "pitcher", g: p.g, ip: p.ip, h: p.h, er: p.er, bb: p.bb, k: p.k, era: p.era };
      }
    }
    return null;
  }, [games, isBatter, unifiedStats]);

  const isFromUnifiedStats = (!games || games.length === 0) && !!unifiedStats;

  const levelBadges = (player.levels ?? []).map((l, i) => {
    const lvl = l.level;
    return (
      <span key={i} style={{ marginRight: "4px" }}>
        <LevelBadge level={lvl} levelColors={levelColors} />
      </span>
    );
  });

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div>
            <h3 style={{ margin: 0 }}>{player.name}</h3>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                marginTop: "4px",
              }}
            >
              {levelBadges}
              <span style={{ opacity: 0.8, fontSize: "0.85rem" }}>
                {getTeamDisplayName(player.team, data)}
              </span>
              {player.bref_id && (
                <a
                  href={BREF_BASE + player.bref_id}
                  target="_blank"
                  rel="noreferrer"
                  style={{ color: "white", fontSize: "11px", opacity: 0.8 }}
                >
                  BBRef ↗
                </a>
              )}
            </div>
          </div>
          <button className="modal-close" onClick={onClose}>
            &times;
          </button>
        </div>

        <div className="modal-body">
          {summary && (
            <div className="player-summary">
              {summary.kind === "batter" ? (
                <>
                  <div className="player-summary-stat">
                    <div className="value">{summary.g}</div>
                    <div className="label">Games</div>
                  </div>
                  <div className="player-summary-stat">
                    <div className="value">{summary.avg}</div>
                    <div className="label">AVG</div>
                  </div>
                  <div className="player-summary-stat">
                    <div className="value">{summary.h}</div>
                    <div className="label">Hits</div>
                  </div>
                  <div className="player-summary-stat">
                    <div className="value">{summary.hr}</div>
                    <div className="label">HR</div>
                  </div>
                  <div className="player-summary-stat">
                    <div className="value">{summary.rbi}</div>
                    <div className="label">RBI</div>
                  </div>
                  <div className="player-summary-stat">
                    <div className="value">{summary.bb}</div>
                    <div className="label">BB</div>
                  </div>
                </>
              ) : (
                <>
                  <div className="player-summary-stat">
                    <div className="value">{summary.g}</div>
                    <div className="label">Games</div>
                  </div>
                  <div className="player-summary-stat">
                    <div className="value">{summary.ip}</div>
                    <div className="label">IP</div>
                  </div>
                  <div className="player-summary-stat">
                    <div className="value">{summary.era}</div>
                    <div className="label">ERA</div>
                  </div>
                  <div className="player-summary-stat">
                    <div className="value">{summary.k}</div>
                    <div className="label">K</div>
                  </div>
                  <div className="player-summary-stat">
                    <div className="value">{summary.bb}</div>
                    <div className="label">BB</div>
                  </div>
                </>
              )}
            </div>
          )}

          {milestones && milestones.length > 0 && (
            <div style={{ marginBottom: "16px" }}>
              <h4 style={{ marginBottom: "8px" }}>Major milestones</h4>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                {milestones.map((m, i) => (
                  <span key={i} className="milestone-chip">
                    <span className="chip-type">{m.milestoneType}</span>
                    {milestoneStatChips(m, 3).map((chip) => (
                      <span key={chip.key} className="chip-stat">
                        {chip.key} {chip.value}
                      </span>
                    ))}
                    {m.Date && <span>{formatDate(m.Date)}</span>}
                    {m.Opponent && <span>vs {m.Opponent}</span>}
                  </span>
                ))}
              </div>
            </div>
          )}

          {isFromUnifiedStats && (
            <div style={{ padding: "8px 12px", background: "#e8f0fe", borderRadius: "6px", marginBottom: "12px", fontSize: "0.85rem", color: "#1e3a5f" }}>
              Showing season totals. Game-by-game data not yet available for this player.
            </div>
          )}

          <h4 style={{ marginBottom: "12px" }}>Game Log ({games.length})</h4>
          <div className="table-container" style={{ maxHeight: "400px" }}>
            <table className="data-table player-game-log-table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Level</th>
                  <th>Opp</th>
                  {isBatter ? (
                    <>
                      <th>AB</th>
                      <th>R</th>
                      <th>H</th>
                      <th>2B</th>
                      <th>3B</th>
                      <th>HR</th>
                      <th>RBI</th>
                      <th>BB</th>
                      <th>K</th>
                      <th>SB</th>
                    </>
                  ) : (
                    <>
                      <th>IP</th>
                      <th>H</th>
                      <th>R</th>
                      <th>ER</th>
                      <th>BB</th>
                      <th>K</th>
                    </>
                  )}
                </tr>
              </thead>
              <tbody>
                {games.map((g, i) => {
                  const canOpenGame = Boolean(
                    onGameClick &&
                      (g.game_id || ((g.date || g.Date) && (g.opponent || g.Opponent)))
                  );
                  return (
                    <tr
                      key={`${g.game_id ?? g.date ?? g.Date ?? "game"}-${i}`}
                      className={canOpenGame ? "clickable-row" : ""}
                      tabIndex={canOpenGame ? 0 : undefined}
                      title={canOpenGame ? "Open game details" : undefined}
                      onClick={() => {
                        if (canOpenGame) onGameClick?.(g);
                      }}
                      onKeyDown={(event) => {
                        if (canOpenGame && (event.key === "Enter" || event.key === " ")) {
                          event.preventDefault();
                          onGameClick?.(g);
                        }
                      }}
                    >
                      <td>{formatDate(g.date ?? g.Date ?? "")}</td>
                      <td>
                        <LevelBadge
                          level={g.level ?? g.Level ?? ""}
                          levelColors={levelColors}
                        />
                      </td>
                      <td>
                        {getTeamDisplayName(g.opponent ?? g.Opponent ?? "", data)}
                      </td>
                      {isBatter ? (
                        <>
                          <td className="text-center">{g.ab}</td>
                          <td className="text-center">{g.r}</td>
                          <td className="text-center">{g.h}</td>
                          <td className="text-center">{g.doubles ?? 0}</td>
                          <td className="text-center">{g.triples ?? 0}</td>
                          <td className="text-center">{g.hr ?? 0}</td>
                          <td className="text-center">{g.rbi}</td>
                          <td className="text-center">{g.bb}</td>
                          <td className="text-center">{g.k}</td>
                          <td className="text-center">{g.sb ?? 0}</td>
                        </>
                      ) : (
                        <>
                          <td className="text-center">{g.ip}</td>
                          <td className="text-center">{g.h}</td>
                          <td className="text-center">{g.r}</td>
                          <td className="text-center">{g.er}</td>
                          <td className="text-center">{g.bb}</td>
                          <td className="text-center">{g.k}</td>
                        </>
                      )}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
