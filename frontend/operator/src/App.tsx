import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  getOverview,
  getRun,
  getRunEvents,
  getThreadCommands,
  getThreadDiagnostics,
  listSandboxes,
  listThreadRuns,
  search,
} from "./api";
import { CodeBlock, ErrorBox, Spinner } from "./components";

type Tab = "overview" | "search" | "sandboxes" | "thread";

function useHashTab(): [Tab, (t: Tab) => void] {
  const read = (): Tab => {
    const h = window.location.hash.replace("#", "");
    if (h === "search" || h === "sandboxes" || h === "thread") return h;
    return "overview";
  };
  const [tab, setTab] = useState<Tab>(read);
  useEffect(() => {
    const on = () => setTab(read());
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);
  const set = (t: Tab) => {
    window.location.hash = t === "overview" ? "" : `#${t}`;
    setTab(t);
  };
  return [tab, set];
}

export default function App() {
  const [tab, setTab] = useHashTab();
  return (
    <div className="root">
      <header className="header">
        <div className="brand">Leon Operator</div>
        <nav className="nav">
          <button className={tab === "overview" ? "active" : ""} onClick={() => setTab("overview")}>
            Overview
          </button>
          <button className={tab === "search" ? "active" : ""} onClick={() => setTab("search")}>
            Search
          </button>
          <button className={tab === "sandboxes" ? "active" : ""} onClick={() => setTab("sandboxes")}>
            Sandboxes
          </button>
          <button className={tab === "thread" ? "active" : ""} onClick={() => setTab("thread")}>
            Thread
          </button>
        </nav>
      </header>
      <main className="main">
        {tab === "overview" ? <Overview /> : null}
        {tab === "search" ? <Search /> : null}
        {tab === "sandboxes" ? <Sandboxes /> : null}
        {tab === "thread" ? <Thread /> : null}
      </main>
      <footer className="footer">
        <div>Backend: proxied at /api</div>
      </footer>
    </div>
  );
}

function Overview() {
  const [data, setData] = useState<any | null>(null);
  const [err, setErr] = useState<unknown>(null);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    setErr(null);
    try {
      setData(await getOverview());
    } catch (e) {
      setErr(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  return (
    <section className="card">
      <div className="cardHeader">
        <h2>Overview</h2>
        <button onClick={() => void load()} disabled={loading}>
          Refresh
        </button>
      </div>
      {loading ? <Spinner label="Loading" /> : null}
      {err ? <ErrorBox error={err} /> : null}
      {data ? <CodeBlock value={data} /> : null}
    </section>
  );
}

function Search() {
  const [q, setQ] = useState("");
  const [data, setData] = useState<any | null>(null);
  const [err, setErr] = useState<unknown>(null);
  const [loading, setLoading] = useState(false);

  const onSearch = async () => {
    const query = q.trim();
    if (!query) return;
    setLoading(true);
    setErr(null);
    try {
      setData(await search(query));
    } catch (e) {
      setErr(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="card">
      <div className="cardHeader">
        <h2>Search</h2>
      </div>
      <div className="row">
        <input
          className="input"
          placeholder="thread_id / run_id / sandbox_id / text"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") void onSearch();
          }}
        />
        <button onClick={() => void onSearch()} disabled={loading}>
          Search
        </button>
      </div>
      {loading ? <Spinner label="Searching" /> : null}
      {err ? <ErrorBox error={err} /> : null}
      {data ? <CodeBlock value={data} /> : null}
    </section>
  );
}

function Sandboxes() {
  const [data, setData] = useState<any | null>(null);
  const [err, setErr] = useState<unknown>(null);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    setErr(null);
    try {
      setData(await listSandboxes());
    } catch (e) {
      setErr(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  return (
    <section className="card">
      <div className="cardHeader">
        <h2>Sandboxes</h2>
        <button onClick={() => void load()} disabled={loading}>
          Refresh
        </button>
      </div>
      {loading ? <Spinner label="Loading" /> : null}
      {err ? <ErrorBox error={err} /> : null}
      {data ? <CodeBlock value={data} /> : null}
    </section>
  );
}

function Thread() {
  const [threadId, setThreadId] = useState("");
  const [runs, setRuns] = useState<any | null>(null);
  const [runId, setRunId] = useState<string>("");
  const [run, setRun] = useState<any | null>(null);
  const [events, setEvents] = useState<any[]>([]);
  const [afterId, setAfterId] = useState<number | undefined>(undefined);

  const [diag, setDiag] = useState<any | null>(null);
  const [cmds, setCmds] = useState<any | null>(null);

  const [err, setErr] = useState<unknown>(null);
  const [loading, setLoading] = useState(false);
  const [tailing, setTailing] = useState(false);

  const tailTimer = useRef<number | null>(null);

  const stopTail = () => {
    setTailing(false);
    if (tailTimer.current) {
      window.clearInterval(tailTimer.current);
      tailTimer.current = null;
    }
  };

  useEffect(() => {
    return () => stopTail();
  }, []);

  const loadRuns = async () => {
    const id = threadId.trim();
    if (!id) return;
    stopTail();
    setLoading(true);
    setErr(null);
    try {
      const rs = await listThreadRuns(id);
      setRuns(rs);
    } catch (e) {
      setErr(e);
    } finally {
      setLoading(false);
    }
  };

  const loadRun = async (rid: string) => {
    if (!rid) return;
    setLoading(true);
    setErr(null);
    try {
      setRun(await getRun(rid));
      const ev = await getRunEvents(rid);
      const items = Array.isArray(ev?.items) ? ev.items : ev;
      const arr = Array.isArray(items) ? items : [];
      setEvents(arr);
      const lastId = arr.length ? arr[arr.length - 1].id : undefined;
      setAfterId(typeof lastId === "number" ? lastId : undefined);
    } catch (e) {
      setErr(e);
    } finally {
      setLoading(false);
    }
  };

  const loadDiagnostics = async () => {
    const id = threadId.trim();
    if (!id) return;
    setLoading(true);
    setErr(null);
    try {
      const [d, c] = await Promise.all([getThreadDiagnostics(id), getThreadCommands(id)]);
      setDiag(d);
      setCmds(c);
    } catch (e) {
      setErr(e);
    } finally {
      setLoading(false);
    }
  };

  const startTail = () => {
    if (!runId) return;
    if (tailTimer.current) window.clearInterval(tailTimer.current);
    setTailing(true);
    tailTimer.current = window.setInterval(async () => {
      try {
        const ev = await getRunEvents(runId, afterId);
        const items = Array.isArray(ev?.items) ? ev.items : ev;
        const arr = Array.isArray(items) ? items : [];
        if (arr.length) {
          setEvents((prev) => [...prev, ...arr]);
          const lastId = arr[arr.length - 1]?.id;
          if (typeof lastId === "number") setAfterId(lastId);
        }
      } catch (e) {
        stopTail();
        setErr(e);
      }
    }, 1000);
  };

  const runOptions = useMemo(() => {
    const items = Array.isArray(runs?.items) ? runs.items : Array.isArray(runs) ? runs : [];
    return items;
  }, [runs]);

  return (
    <section className="card">
      <div className="cardHeader">
        <h2>Thread</h2>
      </div>
      <div className="row">
        <input
          className="input"
          placeholder="thread_id"
          value={threadId}
          onChange={(e) => setThreadId(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") void loadRuns();
          }}
        />
        <button onClick={() => void loadRuns()} disabled={loading}>
          Load Runs
        </button>
        <button onClick={() => void loadDiagnostics()} disabled={loading}>
          Diagnostics
        </button>
      </div>

      <div className="row">
        <select
          className="select"
          value={runId}
          onChange={(e) => {
            const rid = e.target.value;
            setRunId(rid);
            setRun(null);
            setEvents([]);
            setAfterId(undefined);
            stopTail();
            if (rid) void loadRun(rid);
          }}
        >
          <option value="">select run</option>
          {runOptions.map((r: any) => (
            <option key={String(r.id)} value={String(r.id)}>
              {String(r.id)} {r.status ? `(${r.status})` : ""}
            </option>
          ))}
        </select>
        <button onClick={() => (tailing ? stopTail() : startTail())} disabled={!runId}>
          {tailing ? "Stop Tail" : "Tail Events"}
        </button>
      </div>

      {loading ? <Spinner label="Loading" /> : null}
      {err ? <ErrorBox error={err} /> : null}

      {run ? (
        <div className="split">
          <div>
            <div className="subTitle">Run</div>
            <CodeBlock value={run} />
          </div>
          <div>
            <div className="subTitle">Events ({events.length})</div>
            <CodeBlock value={events} />
          </div>
        </div>
      ) : null}

      {diag ? (
        <div className="split">
          <div>
            <div className="subTitle">Diagnostics</div>
            <CodeBlock value={diag} />
          </div>
          <div>
            <div className="subTitle">Commands</div>
            <CodeBlock value={cmds} />
          </div>
        </div>
      ) : null}
    </section>
  );
}

