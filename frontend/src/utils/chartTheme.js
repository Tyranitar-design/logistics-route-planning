import * as echarts from 'echarts'

const palette = {
  cyan: '#00d4ff',
  teal: '#11e0b7',
  amber: '#ffbf47',
  danger: '#ff5b6e',
  blue: '#4da3ff',
  violet: '#7c8cff',
  textPrimary: '#ecf7ff',
  textSecondary: 'rgba(236, 247, 255, 0.72)',
  textMuted: 'rgba(236, 247, 255, 0.46)',
  axis: 'rgba(255, 255, 255, 0.14)',
  split: 'rgba(0, 212, 255, 0.08)',
  panel: 'rgba(255, 255, 255, 0.03)'
}

export function getChartPalette() {
  return palette
}

export function buildTooltip(extra = {}) {
  return {
    trigger: 'axis',
    backgroundColor: 'rgba(6, 14, 28, 0.94)',
    borderColor: 'rgba(0, 212, 255, 0.22)',
    borderWidth: 1,
    textStyle: {
      color: palette.textPrimary,
      fontSize: 12
    },
    extraCssText: 'box-shadow: 0 16px 48px rgba(0,0,0,0.35); border-radius: 12px;',
    ...extra
  }
}

export function buildGrid(extra = {}) {
  return {
    left: '4%',
    right: '4%',
    top: '14%',
    bottom: '12%',
    containLabel: true,
    ...extra
  }
}

export function buildLegend(extra = {}) {
  return {
    textStyle: {
      color: palette.textSecondary,
      fontSize: 11
    },
    itemWidth: 12,
    itemHeight: 12,
    ...extra
  }
}

export function buildAxisLabel(extra = {}) {
  return {
    color: palette.textSecondary,
    fontSize: 11,
    ...extra
  }
}

export function buildAxisLine(extra = {}) {
  return {
    lineStyle: {
      color: palette.axis,
      width: 1,
      ...(extra.lineStyle || {})
    },
    ...extra
  }
}

export function buildSplitLine(extra = {}) {
  return {
    lineStyle: {
      color: palette.split,
      width: 1,
      type: 'dashed',
      ...(extra.lineStyle || {})
    },
    ...extra
  }
}

export function buildEmptyStateOption(title, subtitle, accent = palette.cyan) {
  return {
    animation: false,
    title: {
      text: title,
      subtext: subtitle,
      left: 'center',
      top: 'center',
      textStyle: {
        color: palette.textPrimary,
        fontSize: 18,
        fontWeight: 600
      },
      subtextStyle: {
        color: palette.textMuted,
        fontSize: 12,
        lineHeight: 18
      }
    },
    graphic: [
      {
        type: 'circle',
        left: 'center',
        top: '38%',
        shape: { r: 32 },
        style: {
          fill: 'rgba(255,255,255,0.03)',
          stroke: accent,
          lineWidth: 1.5,
          shadowBlur: 18,
          shadowColor: accent
        }
      },
      {
        type: 'circle',
        left: 'center',
        top: '38%',
        shape: { r: 16 },
        style: {
          fill: accent,
          opacity: 0.24
        }
      }
    ]
  }
}

export function buildLineChartTheme({
  categories = [],
  series = [],
  title,
  subtitle,
  emptyReason
} = {}) {
  if (!series.length || series.every((item) => !item.data || item.data.length === 0 || item.data.every((v) => Number(v) === 0))) {
    return buildEmptyStateOption(title || '等待真实订单趋势数据', emptyReason || subtitle || '当前数据时间覆盖不足，暂不绘制趋势线。')
  }

  return {
    animationDuration: 800,
    color: [palette.cyan, palette.teal, palette.amber, palette.violet],
    tooltip: buildTooltip(),
    legend: buildLegend({ top: 0 }),
    grid: buildGrid(),
    xAxis: {
      type: 'category',
      data: categories,
      boundaryGap: false,
      axisLabel: buildAxisLabel(),
      axisLine: buildAxisLine(),
      axisTick: { show: false }
    },
    yAxis: {
      type: 'value',
      axisLabel: buildAxisLabel(),
      axisLine: { show: false },
      splitLine: buildSplitLine()
    },
    series: series.map((item, index) => ({
      smooth: true,
      showSymbol: false,
      symbolSize: 8,
      animationEasing: 'cubicOut',
      lineStyle: {
        width: 3
      },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          {
            offset: 0,
            color: [palette.cyan, palette.teal, palette.amber, palette.violet][index % 4]
              .replace(')', ', 0.28)')
              .replace('rgb', 'rgba')
          },
          {
            offset: 1,
            color: 'rgba(0, 212, 255, 0.02)'
          }
        ])
      },
      emphasis: {
        focus: 'series'
      },
      ...item
    }))
  }
}

export function buildBarChartTheme({
  categories = [],
  series = [],
  title,
  subtitle,
  emptyReason
} = {}) {
  if (!series.length || series.every((item) => !item.data || item.data.length === 0)) {
    return buildEmptyStateOption(title || '等待真实分析数据', emptyReason || subtitle || '当前未获得可用成本结构数据。', palette.amber)
  }

  return {
    animationDuration: 700,
    tooltip: buildTooltip({ trigger: 'axis', axisPointer: { type: 'shadow' } }),
    legend: buildLegend({ top: 0 }),
    grid: buildGrid(),
    xAxis: {
      type: 'category',
      data: categories,
      axisLabel: buildAxisLabel(),
      axisLine: buildAxisLine(),
      axisTick: { show: false }
    },
    yAxis: {
      type: 'value',
      axisLabel: buildAxisLabel(),
      axisLine: { show: false },
      splitLine: buildSplitLine()
    },
    series: series.map((item, index) => ({
      type: 'bar',
      barWidth: item.barWidth || '42%',
      itemStyle: {
        borderRadius: [10, 10, 0, 0],
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: [palette.cyan, palette.teal, palette.amber, palette.violet][index % 4] },
          { offset: 1, color: 'rgba(255,255,255,0.1)' }
        ])
      },
      emphasis: {
        itemStyle: {
          shadowBlur: 20,
          shadowColor: [palette.cyan, palette.teal, palette.amber, palette.violet][index % 4]
        }
      },
      ...item
    }))
  }
}

export function buildScatterChartTheme({
  xName,
  yName,
  legendData = [],
  series = [],
  title,
  subtitle,
  emptyReason
} = {}) {
  if (!series.length || series.every((item) => !item.data || item.data.length === 0)) {
    return buildEmptyStateOption(title || '等待 Pareto 数据', emptyReason || subtitle || '当前尚未生成可用解集。', palette.violet)
  }

  return {
    animationDuration: 700,
    tooltip: buildTooltip({ trigger: 'item' }),
    legend: buildLegend({ bottom: 0, data: legendData }),
    grid: {
      left: 54,
      right: 24,
      top: 20,
      bottom: 56
    },
    xAxis: {
      type: 'value',
      name: xName,
      nameLocation: 'middle',
      nameGap: 30,
      axisLabel: buildAxisLabel(),
      axisLine: buildAxisLine(),
      splitLine: buildSplitLine()
    },
    yAxis: {
      type: 'value',
      name: yName,
      nameLocation: 'middle',
      nameGap: 44,
      axisLabel: buildAxisLabel(),
      axisLine: buildAxisLine(),
      splitLine: buildSplitLine()
    },
    series
  }
}

export function buildRadarChartTheme({
  indicators = [],
  series = [],
  title,
  subtitle,
  emptyReason
} = {}) {
  if (!series.length || series.every((item) => !item.data || item.data.length === 0)) {
    return buildEmptyStateOption(title || '等待方案对比数据', emptyReason || subtitle || '当前尚未获得可读的方案评分。', palette.teal)
  }

  return {
    animationDuration: 700,
    tooltip: buildTooltip({ trigger: 'item' }),
    legend: buildLegend({ bottom: 0 }),
    radar: {
      shape: 'polygon',
      splitNumber: 5,
      axisName: {
        color: palette.textSecondary,
        fontSize: 11
      },
      splitLine: {
        lineStyle: {
          color: palette.split
        }
      },
      splitArea: {
        areaStyle: {
          color: [palette.panel, 'rgba(255,255,255,0.01)']
        }
      },
      axisLine: {
        lineStyle: {
          color: palette.axis
        }
      },
      indicator: indicators
    },
    series
  }
}
