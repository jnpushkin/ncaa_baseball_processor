/**
 * Convert Eastern time string to local time.
 * Input: timeStr like "7:00 PM", dateStr like "2025-03-15"
 */
export function convertEasternToLocal(
  timeStr: string | undefined,
  dateStr: string | undefined
): string {
  if (!timeStr || !dateStr) return timeStr || "";

  const match = timeStr.match(/^(\d{1,2}):(\d{2})\s*(AM|PM)$/i);
  if (!match) return timeStr;

  let hours = parseInt(match[1]);
  const mins = parseInt(match[2]);
  const ampm = match[3].toUpperCase();
  if (ampm === "PM" && hours !== 12) hours += 12;
  if (ampm === "AM" && hours === 12) hours = 0;

  let dateParts: Date;
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return timeStr;
    dateParts = d;
  } catch {
    return timeStr;
  }

  const year = dateParts.getFullYear();
  const month = dateParts.getMonth();
  const day = dateParts.getDate();

  try {
    const utcDate = new Date(
      `${year}-${String(month + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}T${String(hours).padStart(2, "0")}:${String(mins).padStart(2, "0")}:00Z`
    );

    const etTzName =
      new Intl.DateTimeFormat("en-US", {
        timeZone: "America/New_York",
        timeZoneName: "short",
      })
        .formatToParts(utcDate)
        .find((p) => p.type === "timeZoneName")?.value || "ET";

    const localTzName =
      new Intl.DateTimeFormat("en-US", { timeZoneName: "short" })
        .formatToParts(utcDate)
        .find((p) => p.type === "timeZoneName")?.value || "";

    if (etTzName === localTzName) {
      return `${timeStr} ${etTzName}`;
    }

    // Convert: figure out the ET→UTC offset, then show in local
    const isDST = month >= 2 && month <= 10; // rough DST check
    const etOffset = isDST ? -4 : -5; // ET offset in hours
    const utcMs = Date.UTC(year, month, day, hours - etOffset, mins);
    const localTime = new Date(utcMs);
    const localHours = localTime.getHours();
    const localMins = localTime.getMinutes();
    const localAmPm = localHours >= 12 ? "PM" : "AM";
    const displayHours = localHours % 12 || 12;
    const displayMins = String(localMins).padStart(2, "0");
    return `${displayHours}:${displayMins} ${localAmPm} ${localTzName}`;
  } catch {
    return timeStr;
  }
}
