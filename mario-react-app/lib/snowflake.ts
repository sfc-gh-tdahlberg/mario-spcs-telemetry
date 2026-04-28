import snowflake from "snowflake-sdk";
import fs from "fs";

snowflake.configure({ logLevel: "ERROR" });

let connection: snowflake.Connection | null = null;
let cachedToken: string | null = null;

function getOAuthToken(): string | null {
  const tokenPath = "/snowflake/session/token";
  try {
    if (fs.existsSync(tokenPath)) {
      return fs.readFileSync(tokenPath, "utf8");
    }
  } catch {
  }
  return null;
}

function getConfig(): snowflake.ConnectionOptions {
  const base = {
    account: process.env.SNOWFLAKE_ACCOUNT || "sfseeurope-eu_demo200",
    warehouse: process.env.SNOWFLAKE_WAREHOUSE || "DIS_MARIO_WH",
    database: process.env.SNOWFLAKE_DATABASE || "DIS_MARIO",
    schema: process.env.SNOWFLAKE_SCHEMA || "PUBLIC",
    role: process.env.SNOWFLAKE_ROLE || "ACCOUNTADMIN",
  };

  const token = getOAuthToken();
  if (token) {
    return {
      ...base,
      host: process.env.SNOWFLAKE_HOST,
      token,
      authenticator: "oauth",
    };
  }

  const keyPath = process.env.SNOWFLAKE_PRIVATE_KEY_PATH || `${process.env.HOME}/.snowflake/keys/cloetta/rsa_key.p8`;
  if (fs.existsSync(keyPath)) {
    return {
      ...base,
      username: process.env.SNOWFLAKE_USER || "thomas",
      authenticator: "SNOWFLAKE_JWT",
      privateKeyPath: keyPath,
    };
  }

  return {
    ...base,
    username: process.env.SNOWFLAKE_USER || "thomas",
    authenticator: "EXTERNALBROWSER",
  };
}

async function getConnection(): Promise<snowflake.Connection> {
  const token = getOAuthToken();
  if (connection && (!token || token === cachedToken)) {
    return connection;
  }
  if (connection) {
    connection.destroy(() => {});
  }
  const conn = snowflake.createConnection(getConfig());
  return new Promise<snowflake.Connection>((resolve, reject) => {
    conn.connect((err) => {
      if (err) {
        console.error("Snowflake connect error:", err.message);
        reject(err);
      } else {
        connection = conn;
        cachedToken = token;
        resolve(conn);
      }
    });
  });
}

function isRetryableError(err: unknown): boolean {
  const error = err as { message?: string; code?: number };
  return !!(
    error.message?.includes("OAuth access token expired") ||
    error.message?.includes("terminated connection") ||
    error.code === 407002
  );
}

export async function query<T>(sql: string, retries = 1): Promise<T[]> {
  try {
    const conn = await getConnection();
    return await new Promise<T[]>((resolve, reject) => {
      conn.execute({
        sqlText: sql,
        complete: (err, _stmt, rows) => {
          if (err) reject(err);
          else resolve((rows || []) as T[]);
        },
      });
    });
  } catch (err) {
    if (retries > 0 && isRetryableError(err)) {
      connection = null;
      return query(sql, retries - 1);
    }
    throw err;
  }
}
