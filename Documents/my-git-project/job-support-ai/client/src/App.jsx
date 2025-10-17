import { useState } from "react";

// 後でFastAPIを足すときに使えるようにAPIベースURLは環境変数から
const API_BASE = import.meta.env.VITE_API_BASE; // 例: https://your-api.azurewebsites.net

export default function App() {
  const [msg, setMsg] = useState("");
  const [log, setLog] = useState([]);

  const send = async () => {
    if (!API_BASE) {
      alert("VITE_API_BASE が未設定です（FastAPI連携時に設定）。");
      return;
    }
    const res = await fetch(`${API_BASE}/health`).catch(() => null);
    setLog((x) => [...x, `ping -> ${res?.status ?? "NG"}`]);
  };

  return (
    <div style={{ maxWidth: 720, margin: "40px auto", fontFamily: "sans-serif" }}>
      <h1>React on Azure</h1>
      <p>テスト。</p>
      <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
        <input style={{ flex: 1, padding: 8 }} value={msg} onChange={(e)=>setMsg(e.target.value)} placeholder="入力…" />
        <button onClick={send}>APIにPing</button>
      </div>
      <pre style={{ marginTop: 16, background:"#f7f7f7", padding:12 }}>{log.join("\n")}</pre>
    </div>
  );
}
