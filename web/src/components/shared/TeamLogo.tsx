"use client";

/* eslint-disable @next/next/no-img-element */

import { useState } from "react";
import { SiteData } from "@/types";
import { getTeamLogoUrl } from "@/lib/logos";

interface TeamLogoProps {
  team: string;
  teamId?: number;
  level?: string;
  size?: number;
  data: SiteData;
}

export default function TeamLogo({
  team,
  teamId,
  level,
  size = 20,
  data,
}: TeamLogoProps) {
  const logoUrl = getTeamLogoUrl(team, data, { teamId, level });
  const [imgError, setImgError] = useState(false);

  if (!logoUrl || imgError) {
    const initials = team
      .split(/[\s-]+/)
      .map((w) => w[0])
      .filter(Boolean)
      .slice(0, 2)
      .join("")
      .toUpperCase();

    return (
      <span
        className="team-logo-fallback"
        style={{ width: size, height: size }}
        title={team}
      >
        {initials}
      </span>
    );
  }

  return (
    <img
      src={logoUrl}
      alt={team}
      style={{ width: size, height: size, objectFit: "contain" }}
      onError={() => setImgError(true)}
    />
  );
}
