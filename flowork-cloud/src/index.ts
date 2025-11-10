// FILE: src/index.ts

export interface Env {
  DB_ETL: D1Database;
  DB_IDEM: D1Database;
  // Secret ini harus di-set via dashboard CF atau 'wrangler secret put'
  ETL_API_KEY: string;
  IDEM_API_KEY: string;
}

export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const url = new URL(request.url);

    // --- ROUTE 1: ETL INGEST (Menerima data dari Gateway Outbox) ---
    if (request.method === "POST" && url.pathname === "/api/etl_ingest") {
      return handleEtlIngest(request, env);
    }

    // --- ROUTE 2: GLOBAL IDEMPOTENCY (Wasit anti-duplikasi) ---
    if (request.method === "POST" && url.pathname === "/api/idem/claim") {
      return handleIdemClaim(request, env);
    }

    return new Response("Flowork Cloud Brain: Active but route not found.", { status: 404 });
  },
};

// === LOGIC 1: ETL Handler ===
async function handleEtlIngest(req: Request, env: Env): Promise<Response> {
  // 1. Cek Auth Sederhana (Bearer Token)
  const auth = req.headers.get("Authorization") || "";
  // NOTE: Di production, gunakan timing-safe comparison jika memungkinkan, tapi ini cukup untuk MVP.
  if (!env.ETL_API_KEY || !auth.includes(env.ETL_API_KEY)) {
      return new Response(JSON.stringify({error: "Unauthorized ETL access"}), { status: 401, headers: {'Content-Type': 'application/json'} });
  }

  try {
    const body = await req.json() as any;
    const events = body.events;

    if (!events || !Array.isArray(events) || events.length === 0) {
        return new Response(JSON.stringify({ stored: 0, message: "No events received" }), { status: 200, headers: {'Content-Type': 'application/json'} });
    }

    // 2. Lazy Migration: Pastikan tabel ada sebelum insert.
    //    D1 cukup cepat untuk melakukan ini.
    await env.DB_ETL.exec(`
      CREATE TABLE IF NOT EXISTS etl_events (
        id TEXT PRIMARY KEY,
        topic TEXT,
        payload TEXT,
        ts INTEGER
      )
    `);

    // 3. Batch Insert (Pakai OR IGNORE biar kalau ada retry dari Gateway gak error)
    const stmt = env.DB_ETL.prepare("INSERT OR IGNORE INTO etl_events (id, topic, payload, ts) VALUES (?, ?, ?, ?)");
    const batch = events.map((e: any) => stmt.bind(e.id, e.topic, e.payload, Date.now()));
    await env.DB_ETL.batch(batch);

    return new Response(JSON.stringify({ ok: true, stored: events.length }), { status: 200, headers: {'Content-Type': 'application/json'} });
  } catch (e) {
    return new Response(JSON.stringify({ error: (e as Error).message }), { status: 500, headers: {'Content-Type': 'application/json'} });
  }
}

// === LOGIC 2: Global Idempotency Handler (Atomic) ===
async function handleIdemClaim(req: Request, env: Env): Promise<Response> {
  // 1. Cek Auth
  const auth = req.headers.get("X-API-Key") || ""; // Gateway mengirim via header X-API-Key untuk idem
  if (!env.IDEM_API_KEY || auth !== env.IDEM_API_KEY) {
       return new Response(JSON.stringify({error: "Unauthorized Idem access"}), { status: 401, headers: {'Content-Type': 'application/json'} });
  }

  try {
    const body = await req.json() as any;
    const { key, job_id, ttl } = body;
    if (!key || !job_id) return new Response("Missing key or job_id", { status: 400 });

    // 2. Lazy Migration
    await env.DB_IDEM.exec(`
      CREATE TABLE IF NOT EXISTS global_locks (
        key TEXT PRIMARY KEY,
        job_id TEXT,
        created_at INTEGER,
        ttl INTEGER
      )
    `);

    const now = Math.floor(Date.now() / 1000);

    // 3. ATOMIC Claim attempt
    // Trik: Gunakan UPSERT (ON CONFLICT DO UPDATE) agar kita bisa menggunakan RETURNING
    // untuk melihat siapa pemenang sebenarnya dari race condition.
    // Jika key sudah ada, kita "update" key-nya dengan nilai yang sama (no-op),
    // tapi ini memicu RETURNING untuk mengembalikan data yang sudah ada di DB.
    const stmt = env.DB_IDEM.prepare(`
      INSERT INTO global_locks (key, job_id, created_at, ttl)
      VALUES (?1, ?2, ?3, ?4)
      ON CONFLICT(key) DO UPDATE SET key=key
      RETURNING job_id
    `).bind(key, job_id, now, ttl);

    const res = await stmt.first();

    // Jika job_id yang dikembalikan DB sama dengan job_id request kita,
    // berarti kita yang berhasil insert (menang).
    // Jika beda, berarti sudah ada job lain yang pegang key itu (kalah).
    const winnerJobId = (res as any)?.job_id;
    const isWinner = winnerJobId === job_id;

    return new Response(JSON.stringify({
      claimed: isWinner,
      winner_job_id: winnerJobId,
      status: isWinner ? "granted" : "rejected_duplicate"
    }), {
        status: isWinner ? 200 : 200, // Gateway kita handle 200 untuk keduanya, dibedakan dari properti 'claimed'
        headers: {'Content-Type': 'application/json'}
    });

  } catch (e) {
    return new Response(JSON.stringify({ error: (e as Error).message }), { status: 500, headers: {'Content-Type': 'application/json'} });
  }
}