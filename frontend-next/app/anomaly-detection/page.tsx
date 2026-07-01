import { ConsoleShell } from "@/components/console-shell";
import { DataState } from "@/components/data-state";
import { MetricCard } from "@/components/metric-card";
import { Panel } from "@/components/panel";
import { StatusPill, TruthStrip } from "@/components/status-pill";
import { getAnomalyPageData } from "@/lib/api";
import { compactText, formatNumber, percent } from "@/lib/format";
import { truthFromResult } from "@/lib/truth";

export const dynamic = "force-dynamic";

function countLevels(levels?: Record<string, number>) {
  return Number(levels?.critical || 0) + Number(levels?.high || 0);
}

export default async function AnomalyDetectionPage() {
  const data = await getAnomalyPageData();
  const health = data.anomalyHealth.data;
  const detect = data.anomalyDetect.data;
  const scorecard = data.anomalyScorecard.data;
  const ml = detect?.diagnostics?.ml_detector;
  const highRiskCount = countLevels(detect?.summary?.by_level);

  return (
    <ConsoleShell
      activePath="/anomaly-detection"
      apiBaseUrl={data.apiBaseUrl}
      generatedAt={data.generatedAt}
      eyebrow="AI 异常检测"
      title="订单、路线、成本与时效异常解释"
    >
      <section className="metric-grid" aria-label="异常检测关键指标">
        <MetricCard label="治理评分" value={formatNumber(scorecard?.summary?.readiness_score, 1)} helper={scorecard?.summary?.status || "scorecard"} tone={(scorecard?.summary?.readiness_score || 0) >= 85 ? "good" : "warn"} />
        <MetricCard label="扫描记录" value={formatNumber(detect?.summary?.records_scanned)} helper="shipment_facts" tone="good" />
        <MetricCard label="异常信号" value={formatNumber(detect?.summary?.anomaly_count)} helper={percent(detect?.summary?.anomaly_rate)} tone={detect?.summary?.anomaly_count ? "warn" : "good"} />
        <MetricCard label="高风险" value={formatNumber(highRiskCount)} helper="critical / high" tone={highRiskCount ? "bad" : "good"} />
        <MetricCard label="ML 检测器" value={ml?.used ? "已启用" : "未启用"} helper={ml?.detector || ml?.fallback_reason || "IsolationForest optional"} />
      </section>

      <section className="dashboard-grid">
        <Panel title="Anomaly Readiness Scorecard" action={<DataState result={data.anomalyScorecard} />}>
          <div className="summary-strip">
            <div>
              <span>Score</span>
              <strong>{formatNumber(scorecard?.summary?.readiness_score, 1)}</strong>
            </div>
            <div>
              <span>Status</span>
              <strong>{scorecard?.summary?.status || "not_ready"}</strong>
            </div>
            <div>
              <span>High Risk</span>
              <strong>{formatNumber(scorecard?.summary?.high_risk_count)}</strong>
            </div>
            <div>
              <span>Anomaly Rate</span>
              <strong>{percent(scorecard?.summary?.anomaly_rate)}</strong>
            </div>
          </div>
          <div className="solver-table" role="table" aria-label="异常检测readiness组件">
            <div className="solver-head metric-head" role="row">
              <span>component</span>
              <span>score</span>
              <span>status</span>
              <span>detail</span>
            </div>
            {(scorecard?.components || []).map((component) => (
              <div className="solver-row metric-row" role="row" key={component.id}>
                <span>{component.label || component.id || "component"}</span>
                <span>{formatNumber(component.score, 1)}</span>
                <StatusPill status={component.status || "unknown"} />
                <span>{compactText(component.details?.fallback_reason as string | undefined, compactText(component.details?.detector as string | undefined, "-"))}</span>
              </div>
            ))}
            {!scorecard?.components?.length ? (
              <p className="empty-note">{data.anomalyScorecard.error || scorecard?.fallback_reason || "暂无异常检测评分卡。"}</p>
            ) : null}
          </div>
          <div className="data-list">
            {(scorecard?.gates || []).map((gate) => (
              <article className="data-row" key={gate.id}>
                <span>{gate.id || "gate"}</span>
                <strong>{gate.passed ? "passed" : "watch"}</strong>
                <p>{gate.detail || "readiness gate"}</p>
              </article>
            ))}
            {(scorecard?.recommendations || []).slice(0, 3).map((item) => (
              <article className="data-row" key={item}>
                <span>scorecard recommendation</span>
                <strong>{item}</strong>
              </article>
            ))}
          </div>
          <p className="panel-note">
            {compactText(scorecard?.truth_contract?.deployment_boundary as string | undefined, "Scorecard 只用于异常治理 readiness 验收，不写异常事件表。")}
          </p>
          <TruthStrip truth={truthFromResult(data.anomalyScorecard)} />
        </Panel>

        <Panel title="Dataset Health" action={<DataState result={data.anomalyHealth} />}>
          <div className="readiness-grid">
            <article className="mini-metric">
              <span>总记录</span>
              <strong>{formatNumber(health?.summary?.total_records)}</strong>
              <StatusPill status={health?.summary?.total_records ? "ok" : "degraded"} />
            </article>
            <article className="mini-metric">
              <span>费用样本</span>
              <strong>{formatNumber(health?.summary?.cost_records)}</strong>
              <StatusPill status={health?.summary?.cost_records ? "ok" : "degraded"} />
            </article>
            <article className="mini-metric">
              <span>坐标准备</span>
              <strong>{formatNumber(health?.summary?.geo_ready_records)}</strong>
              <StatusPill status={health?.summary?.geo_ready_records ? "ok" : "degraded"} />
            </article>
            <article className="mini-metric">
              <span>延误样本</span>
              <strong>{formatNumber(health?.summary?.delay_records)}</strong>
              <StatusPill status={health?.summary?.delay_records ? "ok" : "degraded"} />
            </article>
          </div>
          <TruthStrip truth={truthFromResult(data.anomalyHealth)} />
        </Panel>

        <Panel title="Signal Distribution" action={<DataState result={data.anomalyDetect} />}>
          <div className="distribution-grid">
            <div>
              <h3>按类型</h3>
              {Object.entries(detect?.summary?.by_type || {}).map(([key, value]) => (
                <article className="timeline-row" key={key}>
                  <span>{key}</span>
                  <strong>{formatNumber(value)}</strong>
                </article>
              ))}
            </div>
            <div>
              <h3>按等级</h3>
              {Object.entries(detect?.summary?.by_level || {}).map(([key, value]) => (
                <article className="timeline-row" key={key}>
                  <span>{key}</span>
                  <strong>{formatNumber(value)}</strong>
                </article>
              ))}
            </div>
          </div>
          {!detect?.summary ? <p className="empty-note">{data.anomalyDetect.error || "等待异常检测接口返回。"}</p> : null}
        </Panel>

        <Panel title="Top Anomalies" action={<DataState result={data.anomalyDetect} />}>
          <div className="anomaly-list expanded-list">
            {(detect?.anomalies || []).slice(0, 12).map((item) => (
              <article className="anomaly-row" key={item.anomaly_id}>
                <div>
                  <span>{item.anomaly_type || "unknown"} · {compactText(item.method)}</span>
                  <strong>{compactText(item.origin_city)} → {compactText(item.destination_city)}</strong>
                  <p>{item.explanation || "No explanation reported."}</p>
                </div>
                <StatusPill status={item.level || "unknown"} label={`${item.level || "unknown"} ${formatNumber(item.score, 1)}`} />
              </article>
            ))}
            {!detect?.anomalies?.length ? <p className="empty-note">暂无异常明细或后端未连接。</p> : null}
          </div>
          <TruthStrip truth={truthFromResult(data.anomalyDetect)} />
        </Panel>

        <Panel title="ML Detector Status" action={<StatusPill status={ml?.used ? "ok" : "degraded"} label={ml?.used ? "shadow ready" : "fallback"} />}>
          <div className="summary-strip">
            <div>
              <span>启用配置</span>
              <strong>{ml?.enabled ? "true" : "false"}</strong>
            </div>
            <div>
              <span>实际使用</span>
              <strong>{ml?.used ? "true" : "false"}</strong>
            </div>
            <div>
              <span>检测器</span>
              <strong>{ml?.detector || "not_available"}</strong>
            </div>
          </div>
          <p className="panel-note">
            {ml?.fallback_reason || "规则检测与可选 IsolationForest 会共同输出异常解释，当前仍以可解释规则作为生产底座。"}
          </p>
        </Panel>
      </section>
    </ConsoleShell>
  );
}
