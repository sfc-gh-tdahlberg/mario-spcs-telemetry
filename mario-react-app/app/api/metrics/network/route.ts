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
        MAX(CASE WHEN record:metric.name::STRING = 'network.ingress.connections.active' THEN value::FLOAT END) AS ACTIVE_CONNECTIONS,
        MAX(CASE WHEN record:metric.name::STRING = 'network.ingress.cps' THEN value::FLOAT END) AS CONNECTIONS_PER_SEC
      FROM event_db.event_sh.my_events
      WHERE resource_attributes:"snow.service.name"::STRING = 'MARIO_SERVICE'
        AND record_type = 'METRIC'
        AND record:metric.name::STRING IN ('network.ingress.connections.active', 'network.ingress.cps')
        ${timeFilter}
      GROUP BY 1 ORDER BY 1
    `);
    return NextResponse.json(rows);
  } catch (error) {
    console.error("Network metrics error:", error);
    return NextResponse.json({ error: "Failed to fetch network metrics" }, { status: 500 });
  }
}
