"use client";

import { useState, useMemo, useRef, useEffect } from "react";
import type { SiteData } from "@/types";

interface HeaderProps {
  subtitle: string;
  data?: SiteData;
  onPlayerClick?: (player: { name: string; bref_id?: string; team: string; level: string; levels: { level: string }[] }, type: "batter" | "pitcher") => void;
}

export default function Header({ subtitle, data, onPlayerClick }: HeaderProps) {
  const [query, setQuery] = useState("");
  const [showResults, setShowResults] = useState(false);
  const searchRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) {
        setShowResults(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const results = useMemo(() => {
    if (!query || query.length < 2 || !data) return [];
    const q = query.toLowerCase();
    const matches: { name: string; team: string; level: string; type: "batter" | "pitcher"; bref_id?: string }[] = [];
    for (const b of data.unifiedBatters ?? []) {
      if (b.name?.toLowerCase().includes(q)) {
        matches.push({ name: b.name, team: b.team, level: b.level, type: "batter", bref_id: b.bref_id });
      }
      if (matches.length >= 10) break;
    }
    if (matches.length < 10) {
      for (const p of data.unifiedPitchers ?? []) {
        if (p.name?.toLowerCase().includes(q)) {
          matches.push({ name: p.name, team: p.team, level: p.level, type: "pitcher", bref_id: p.bref_id });
        }
        if (matches.length >= 10) break;
      }
    }
    return matches;
  }, [query, data]);

  return (
    <div className="header">
      <div className="header-inner">
        <div className="header-brand">
          <span className="header-icon" aria-hidden="true">&#9918;</span>
          <div>
            <h1>Baseball Statistics</h1>
            <p>{subtitle}</p>
          </div>
        </div>
        <div className="header-meta">
          <div ref={searchRef} className="header-search-wrap">
            <input
              className="header-search"
              type="text"
              placeholder="Search players..."
              value={query}
              onChange={(e) => { setQuery(e.target.value); setShowResults(true); }}
              onFocus={() => setShowResults(true)}
            />
            {showResults && results.length > 0 && (
              <div className="header-search-results">
                {results.map((r, i) => (
                  <div
                    key={i}
                    className="header-search-item"
                    onClick={() => {
                      if (onPlayerClick) {
                        onPlayerClick(
                          { name: r.name, bref_id: r.bref_id, team: r.team, level: r.level, levels: [{ level: r.level }] },
                          r.type
                        );
                      }
                      setShowResults(false);
                      setQuery("");
                    }}
                  >
                    <span>{r.name}</span>
                    <span className="search-team">{r.team} ({r.level})</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
