"use client";

import { SiteData } from "@/types";
import { getTeamDisplayName } from "@/lib/data";

interface TeamNameProps {
  team: string;
  data: SiteData;
}

export default function TeamName({ team, data }: TeamNameProps) {
  return <>{getTeamDisplayName(team, data)}</>;
}
