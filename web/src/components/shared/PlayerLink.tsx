"use client";

import { BREF_BASE } from "@/lib/constants";

interface PlayerLinkProps {
  name: string;
  brefId?: string;
  onClick?: (e: React.MouseEvent) => void;
}

export default function PlayerLink({ name, brefId, onClick }: PlayerLinkProps) {
  return (
    <span className="clickable-name" onClick={onClick}>
      {name}
      {brefId && (
        <a
          href={BREF_BASE + brefId}
          target="_blank"
          onClick={(e) => e.stopPropagation()}
          style={{ marginLeft: "4px", fontSize: "10px" }}
        >
          ↗
        </a>
      )}
    </span>
  );
}
