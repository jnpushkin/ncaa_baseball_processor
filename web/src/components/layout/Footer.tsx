"use client";

import type { SiteData } from "@/types";

interface FooterProps {
  generatedTime?: string;
  data?: SiteData;
}

function formatGeneratedTime(value?: string) {
  if (!value) return "unknown";
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

export default function Footer({ generatedTime, data }: FooterProps) {
  const schedule = data?.dataMetadata?.schedule;
  const scheduleCoverage =
    schedule?.first_date && schedule?.last_date
      ? `Schedule ${schedule.first_date} to ${schedule.last_date}`
      : null;

  return (
    <div className="footer">
      <div className="footer-content">
        <div className="footer-sources">
          Data from NCAA, MLB Stats API, Chadwick Bureau
        </div>
        <div>Generated {formatGeneratedTime(generatedTime)}</div>
        {scheduleCoverage && <div>{scheduleCoverage}</div>}
      </div>
    </div>
  );
}
