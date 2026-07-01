"use client";

export function RefreshButton() {
  return (
    <button className="command-button" type="button" onClick={() => window.location.reload()}>
      刷新数据
    </button>
  );
}
