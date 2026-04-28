import { NextResponse } from "next/server";
import { query } from "@/lib/snowflake";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const minutes = searchParams.get("minutes") || "360";
    const timeFilter = minutes === "all"
      ? "AND timestamp > '2020-01-01'"
      : `AND timestamp >= DATEADD('MINUTE', -${parseInt(minutes)}, CURRENT_TIMESTAMP())`;

    const rows = await query(`
      SELECT
        TO_CHAR(CONVERT_TIMEZONE('UTC', 'Europe/Stockholm', TIME_SLICE(timestamp, 1, 'MINUTE')::TIMESTAMP_NTZ), 'YYYY-MM-DD"T"HH24:MI:SS') AS MINUTE,
        ROUND(AVG(value::FLOAT) / 1048576, 1) AS AVG_MEMORY_MB,
        ROUND(MAX(value::FLOAT) / 1048576, 1) AS MAX_MEMORY_MB
      FROM event_db.event_sh.my_events
      WHERE resource_attributes:"snow.service.name"::STRING = 'MARIO_SERVICE'
        AND record_type = 'METRIC'
        AND record:metric.name::STRING = 'container.memory.usage'
        ${timeFilter}
      GROUP BY 1 ORDER BY 1
    `);
    return NextResponse.json(rows);
  } catch (error) {
    console.error("Memory metrics error:", error);
    return NextResponse.json({ error: "Failed to fetch memory metrics" }, { status: 500 });
  }
}
