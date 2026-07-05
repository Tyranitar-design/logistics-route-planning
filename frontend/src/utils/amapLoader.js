/**
 * 高德地图 JS API 2.0 统一加载器（案例模块专用）
 *
 * 设计目标：
 * 1. 单例加载 —— 多页面复用同一 AMap 实例，避免重复 <script> 注入
 * 2. 安全密钥 —— 自动注入 securityJsCode（2021-12-02 后申请的 key 必需）
 * 3. 插件按需 —— 一次性加载 Marker/Polyline/InfoWindow/Driving/MoveAnimation 等
 * 4. 优雅降级 —— key 缺失/网络失败时 reject，调用方降级到 Leaflet
 *
 * 真实性边界：
 * - 浏览器侧只读 VITE_AMAP_KEY / VITE_AMAP_SECURITY_KEY（前端 JS key）
 * - 服务端鉴权 key（AMAP_SERVICE_KEY）只在后端使用，绝不进入前端
 * - 当 securityJsCode 缺失或非 32 位 hex 时，仍尝试加载（兼容 2021-12 前申请的老 key）
 */

// 标准插件清单：覆盖案例模块所需的 Marker / Polyline / 信息窗 / 地理编码 / 驾车导航 / 轨迹动画
const AMAP_PLUGINS = [
  'AMap.Scale',
  'AMap.ToolBar',
  'AMap.ControlBar',
  'AMap.MapType',
  'AMap.Geocoder',
  'AMap.Driving',
  'AMap.MoveAnimation',
  'AMap.PolylineEditor',
  'AMap.AdvancedInfoWindow',
]

let amapPromise = null

/**
 * 判断 securityJsCode 是否像真实的安全密钥（32 位 hex）。
 * 桌面 key 文件被破坏时（值为 "可使用服务：" 之类），返回 false。
 */
function isValidSecurityCode(sec) {
  return typeof sec === 'string' && /^[0-9a-fA-F]{32}$/.test(sec.trim())
}

/**
 * 判断 web key 是否像真实的高德 key（32 位 hex）。
 */
function isValidWebKey(key) {
  return typeof key === 'string' && /^[0-9a-fA-F]{32}$/.test(key.trim())
}

/**
 * 同步返回 window.AMap（如已加载完成）。未加载返回 null。
 * 用于不想 await 的快速判断场景。
 */
export function getAmapIfReady() {
  if (typeof window === 'undefined') return null
  const AMap = window.AMap
  if (AMap && typeof AMap.Map === 'function') return AMap
  return null
}

/**
 * 异步加载高德 JS API + 插件。单例模式。
 *
 * 成功 resolve(AMap)；失败 reject(Error)，调用方应降级到 Leaflet。
 *
 * 失败原因：
 *   - AMAP_KEY_MISSING：VITE_AMAP_KEY 缺失或格式错误
 *   - AMAP_LOADER_SCRIPT_FAILED：网络无法访问 webapi.amap.com
 *   - AMAP_LOAD_TIMEOUT：15s 内未加载完成
 *   - AMAP_INVALID_USER_SCODE：key 需要 securityJsCode 但未配置（2021-12 后申请的 key）
 */
export function loadAmap() {
  const cached = getAmapIfReady()
  if (cached) return Promise.resolve(cached)
  if (amapPromise) return amapPromise

  const key = (import.meta.env.VITE_AMAP_KEY || '').trim()
  const security = (import.meta.env.VITE_AMAP_SECURITY_KEY || '').trim()

  if (!isValidWebKey(key)) {
    amapPromise = Promise.reject(new Error('AMAP_KEY_MISSING'))
    return amapPromise
  }

  amapPromise = new Promise((resolve, reject) => {
    // 1) 加载前注入 securityJsCode（必须在 AMap 脚本加载前设置）
    if (isValidSecurityCode(security)) {
      window._AMapSecurityConfig = { securityJsCode: security }
    }

    // 2) 通过官方 AMapLoader 异步加载（兼容性最好，避免 index.html 同步 script 阻塞）
    const loaderScript = document.createElement('script')
    loaderScript.src = 'https://webapi.amap.com/loader.js'

    const timeoutId = setTimeout(() => {
      reject(new Error('AMAP_LOAD_TIMEOUT'))
      amapPromise = null
    }, 15000)

    loaderScript.onload = () => {
      clearTimeout(timeoutId)
      const AMapLoader = window.AMapLoader
      if (!AMapLoader || typeof AMapLoader.load !== 'function') {
        // 降级：直接用 window.AMap（index.html 可能已经同步加载）
        const fallback = getAmapIfReady()
        if (fallback) {
          resolve(fallback)
        } else {
          reject(new Error('AMAP_LOADER_NOT_FOUND'))
          amapPromise = null
        }
        return
      }
      AMapLoader.load({
        key,
        version: '2.0',
        plugins: AMAP_PLUGINS,
        AMapUI: { loadUI: false },
      })
        .then((AMap) => {
          resolve(AMap)
        })
        .catch((e) => {
          const msg = (e && (e.message || e.toString())) || 'AMAP_LOAD_FAILED'
          // 检测是否 SCODE 错误，给出可读 reason
          const enriched = /INVALID_USER_SCODE|USERN_AUTH_FAIL|securityJsCode/i.test(msg)
            ? new Error('AMAP_INVALID_USER_SCODE')
            : new Error(msg)
          reject(enriched)
          amapPromise = null
        })
    }

    loaderScript.onerror = () => {
      clearTimeout(timeoutId)
      reject(new Error('AMAP_LOADER_SCRIPT_FAILED'))
      amapPromise = null
    }

    document.head.appendChild(loaderScript)
  })

  return amapPromise
}

/**
 * 懒加载 Leaflet 作为降级方案。案例模块的 GIS/Dispatch 页共用。
 * 成功 resolve(L)，失败 reject(Error)。
 */
export function loadLeafletFallback() {
  if (window.L && window.L.map) return Promise.resolve(window.L)
  const loadFromBundle = async () => {
    await import('leaflet/dist/leaflet.css')
    const mod = await import('leaflet')
    const L = mod.default || mod
    window.L = L
    return L
  }
  return loadFromBundle().catch((bundleErr) => new Promise((resolve, reject) => {
    const timeoutId = setTimeout(() => {
      reject(new Error(`LEAFLET_LOAD_TIMEOUT:${bundleErr.message || bundleErr}`))
    }, 8000)

    const finish = (fn, value) => {
      clearTimeout(timeoutId)
      fn(value)
    }

    // 最后兜底才走 CDN；正常 Vite 构建会直接使用本地 leaflet 依赖。
    const link = document.createElement('link')
    link.rel = 'stylesheet'
    link.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css'
    document.head.appendChild(link)
    const s = document.createElement('script')
    s.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'
    s.onload = () => finish(resolve, window.L)
    s.onerror = () => finish(reject, new Error(`LEAFLET_LOAD_FAILED:${bundleErr.message || bundleErr}`))
    document.head.appendChild(s)
  }))
}

/**
 * 统一地图加载：优先高德，失败降级 Leaflet。
 * 返回 { engine: 'amap' | 'leaflet', AMap, L, errorMessage? }
 */
export async function loadMapEngine() {
  try {
    const AMap = await loadAmap()
    return { engine: 'amap', AMap, L: null }
  } catch (amapErr) {
    try {
      const L = await loadLeafletFallback()
      return { engine: 'leaflet', AMap: null, L, amapError: amapErr.message }
    } catch (lfErr) {
      throw new Error(`地图引擎均不可用：AMap(${amapErr.message}) / Leaflet(${lfErr.message})`)
    }
  }
}

export default { loadAmap, loadLeafletFallback, loadMapEngine, getAmapIfReady }
