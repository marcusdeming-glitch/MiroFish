<template>
  <div class="portfolio-layout">
    <!-- Sidebar -->
    <aside class="sidebar">
      <div class="sidebar-brand" @click="$router.push('/')">MIROFISH</div>
      <nav class="sidebar-nav">
        <router-link :to="`/portfolio/${portfolioId}`" class="nav-item">
          <span class="nav-icon">◈</span> Portfolio
        </router-link>
        <router-link :to="`/portfolio/${portfolioId}/news`" class="nav-item">
          <span class="nav-icon">◎</span> News Feed
        </router-link>
        <router-link :to="`/portfolio/${portfolioId}/analysis`" class="nav-item active">
          <span class="nav-icon">◐</span> Analysis
        </router-link>
      </nav>
      <!-- Analysis Config -->
      <div class="sidebar-filters">
        <div class="sidebar-section-title">ANALYSIS CONFIG</div>
        <div class="filter-group">
          <label>News Window</label>
          <select v-model="analysisConfig.days_news" class="filter-select">
            <option :value="3">3 days</option>
            <option :value="7">7 days</option>
            <option :value="14">14 days</option>
          </select>
        </div>
        <div class="filter-group">
          <label>Filings Window</label>
          <select v-model="analysisConfig.days_filings" class="filter-select">
            <option :value="14">14 days</option>
            <option :value="30">30 days</option>
            <option :value="60">60 days</option>
            <option :value="90">90 days</option>
          </select>
        </div>
        <button class="btn-run" @click="runAnalysis" :disabled="running || !portfolio">
          {{ running ? '◐ Analysing…' : '◐ Run Analysis' }}
        </button>
        <div v-if="result" class="last-run-info">
          Last run: {{ formatDate(result.analysis?.analysis_date) }}
        </div>
      </div>
    </aside>

    <!-- Main -->
    <main class="main-content">
      <div class="page-header">
        <div>
          <h1 class="page-title">Portfolio Analysis</h1>
          <p class="page-subtitle">{{ portfolio?.name }} — AI-powered impact analysis & recommendations</p>
        </div>
      </div>

      <!-- Running state -->
      <div v-if="running" class="running-state">
        <div class="pipeline-steps">
          <div class="pipeline-step" :class="{ done: runStep > 0, active: runStep === 0 }">
            <span class="step-dot"></span> Fetching news from Reuters, CNBC, MarketWatch, Yahoo Finance…
          </div>
          <div class="pipeline-step" :class="{ done: runStep > 1, active: runStep === 1 }">
            <span class="step-dot"></span> Fetching SEC EDGAR & SGX filings…
          </div>
          <div class="pipeline-step" :class="{ done: runStep > 2, active: runStep === 2 }">
            <span class="step-dot"></span> Running LLM impact analysis across holdings…
          </div>
          <div class="pipeline-step" :class="{ done: runStep > 3, active: runStep === 3 }">
            <span class="step-dot"></span> Generating conservative recommendations…
          </div>
        </div>
      </div>

      <!-- No results yet -->
      <div v-else-if="!result" class="empty-state">
        <div class="empty-icon">◐</div>
        <h2>No analysis yet</h2>
        <p>Run analysis to get AI-powered insights on how recent news and filings affect your portfolio.</p>
        <p class="hint">Sources: Reuters, CNBC, MarketWatch, Yahoo Finance, FT, Bloomberg, SEC EDGAR, SGX</p>
        <button class="btn-primary" @click="runAnalysis" :disabled="!portfolio">Run Analysis</button>
      </div>

      <!-- Results -->
      <template v-else>
        <!-- Overall Sentiment Banner -->
        <div class="sentiment-banner" :class="result.analysis?.overall_sentiment">
          <div class="sentiment-left">
            <span class="sentiment-icon">{{ sentimentIcon(result.analysis?.overall_sentiment) }}</span>
            <div>
              <div class="sentiment-label">MARKET SENTIMENT</div>
              <div class="sentiment-value">{{ (result.analysis?.overall_sentiment || 'neutral').toUpperCase() }}</div>
            </div>
          </div>
          <div class="sentiment-summary">{{ result.analysis?.market_summary }}</div>
          <div class="sentiment-meta">
            <span>{{ result.analysis?.news_count }} news articles</span>
            <span>{{ result.analysis?.filings_count }} filings</span>
          </div>
        </div>

        <!-- Macro Themes -->
        <div v-if="result.analysis?.macro_themes?.length" class="macro-themes">
          <span class="section-label">MACRO THEMES</span>
          <span v-for="theme in result.analysis.macro_themes" :key="theme" class="theme-pill">{{ theme }}</span>
        </div>

        <!-- Main content grid -->
        <div class="analysis-grid">
          <!-- Left: Holdings Impact -->
          <section class="card">
            <div class="card-header"><h2>HOLDING IMPACTS</h2></div>
            <div class="impact-list">
              <div
                v-for="impact in result.analysis?.holding_impacts || []"
                :key="impact.ticker"
                class="impact-row"
                :class="impact.sentiment"
              >
                <div class="impact-header">
                  <div class="impact-ticker">{{ impact.ticker }}</div>
                  <div class="impact-badges">
                    <span class="sentiment-tag" :class="impact.sentiment">{{ impact.sentiment }}</span>
                    <span class="level-tag" :class="impact.impact_level">{{ impact.impact_level }}</span>
                  </div>
                </div>
                <p class="impact-analysis">{{ impact.analysis }}</p>
                <div class="impact-drivers" v-if="impact.key_drivers?.length">
                  <span class="drivers-label">Drivers:</span>
                  <span v-for="d in impact.key_drivers" :key="d" class="driver-tag">{{ d }}</span>
                </div>
              </div>
              <div v-if="!result.analysis?.holding_impacts?.length" class="empty-section">
                No per-holding impacts identified.
              </div>
            </div>
          </section>

          <!-- Right: Risk Flags + Cross-Industry -->
          <div class="right-col">
            <!-- Risk Flags -->
            <section class="card">
              <div class="card-header"><h2>RISK FLAGS</h2></div>
              <div v-if="!result.analysis?.risk_flags?.length" class="empty-section">No material risks flagged.</div>
              <div v-else class="risk-list">
                <div
                  v-for="risk in result.analysis.risk_flags"
                  :key="risk.flag"
                  class="risk-item"
                  :class="risk.severity"
                >
                  <div class="risk-header">
                    <span class="severity-badge" :class="risk.severity">{{ risk.severity.toUpperCase() }}</span>
                    <span class="risk-ticker">{{ risk.ticker }}</span>
                  </div>
                  <div class="risk-flag">{{ risk.flag }}</div>
                  <div class="risk-detail">{{ risk.detail }}</div>
                  <div class="risk-source" v-if="risk.source">Source: {{ risk.source }}</div>
                </div>
              </div>
            </section>

            <!-- Cross-Industry Insights -->
            <section class="card" style="margin-top:16px">
              <div class="card-header"><h2>CROSS-INDUSTRY SIGNALS</h2></div>
              <div v-if="!result.analysis?.cross_industry_insights?.length" class="empty-section">No cross-industry effects detected.</div>
              <div v-else class="ci-list">
                <div v-for="ci in result.analysis.cross_industry_insights" :key="ci.trigger" class="ci-item">
                  <div class="ci-trigger">⟳ {{ ci.trigger }}</div>
                  <div class="ci-tickers">
                    <span v-for="t in ci.affected_tickers" :key="t" class="ci-ticker-tag">{{ t }}</span>
                  </div>
                  <p class="ci-insight">{{ ci.insight }}</p>
                </div>
              </div>
            </section>
          </div>
        </div>

        <!-- Recommendations -->
        <section class="card recommendations-card" style="margin-top:20px">
          <div class="card-header">
            <h2>RECOMMENDATIONS</h2>
            <span class="rec-summary-label">{{ result.recommendations?.summary }}</span>
          </div>

          <!-- Rebalancing Alerts -->
          <div v-if="result.recommendations?.rebalancing_alerts?.length" class="rebalancing-section">
            <div class="sub-section-title">REBALANCING ALERTS</div>
            <div class="rebal-list">
              <div v-for="alert in result.recommendations.rebalancing_alerts" :key="alert.ticker" class="rebal-item">
                <span class="rebal-ticker">{{ alert.ticker }}</span>
                <span class="rebal-direction" :class="alert.direction">{{ alert.direction }}</span>
                <span class="rebal-detail">
                  {{ alert.actual_weight }}% actual vs {{ alert.target_weight }}% target
                  ({{ alert.drift > 0 ? '+' : '' }}{{ alert.drift }}%)
                </span>
              </div>
            </div>
          </div>

          <!-- Action Recommendations -->
          <div class="sub-section-title" style="margin-top:16px">ACTION ITEMS</div>
          <div v-if="!result.recommendations?.recommendations?.length" class="empty-section">No specific actions recommended at this time.</div>
          <div v-else class="rec-list">
            <div
              v-for="rec in result.recommendations.recommendations"
              :key="rec.ticker + rec.action"
              class="rec-item"
              :class="rec.action.toLowerCase()"
            >
              <div class="rec-header">
                <span class="action-badge" :class="rec.action.toLowerCase()">{{ rec.action }}</span>
                <span class="rec-ticker">{{ rec.ticker }}</span>
                <span class="rec-priority" :class="rec.priority">{{ rec.priority }} priority</span>
                <span class="rec-horizon">{{ rec.time_horizon }}</span>
              </div>
              <p class="rec-rationale">{{ rec.rationale }}</p>
              <div class="rec-adjustment" v-if="rec.suggested_adjustment">
                <span class="adj-label">Suggested:</span> {{ rec.suggested_adjustment }}
              </div>
            </div>
          </div>

          <!-- Watchlist -->
          <div class="sub-section-title" style="margin-top:20px">WATCHLIST</div>
          <div v-if="!result.recommendations?.watchlist?.length" class="empty-section">No items to watch at this time.</div>
          <div v-else class="watchlist">
            <div v-for="w in result.recommendations.watchlist" :key="w.ticker" class="watch-item">
              <div class="watch-header">
                <span class="watch-ticker">{{ w.ticker }}</span>
                <span class="watch-reason">{{ w.watch_reason }}</span>
              </div>
              <div class="watch-trigger" v-if="w.trigger">
                <span class="trigger-label">Escalation trigger:</span> {{ w.trigger }}
              </div>
            </div>
          </div>

          <!-- Key risks & catalysts -->
          <div class="risks-catalysts-row">
            <div class="risks-col" v-if="result.recommendations?.key_risks_to_monitor?.length">
              <div class="sub-section-title">KEY RISKS</div>
              <ul class="bullet-list">
                <li v-for="r in result.recommendations.key_risks_to_monitor" :key="r">{{ r }}</li>
              </ul>
            </div>
            <div class="catalysts-col" v-if="result.recommendations?.positive_catalysts?.length">
              <div class="sub-section-title">POSITIVE CATALYSTS</div>
              <ul class="bullet-list positive">
                <li v-for="c in result.recommendations.positive_catalysts" :key="c">{{ c }}</li>
              </ul>
            </div>
          </div>

          <div class="next-review" v-if="result.recommendations?.next_review_suggestion">
            <span class="next-review-icon">◷</span>
            <span><strong>Next Review:</strong> {{ result.recommendations.next_review_suggestion }}</span>
          </div>
        </section>

        <!-- Supporting News -->
        <section class="card" style="margin-top:20px" v-if="result.news?.length">
          <div class="card-header">
            <h2>SUPPORTING NEWS ({{ result.news.length }} articles)</h2>
            <router-link :to="`/portfolio/${portfolioId}/news`" class="btn-secondary btn-sm">View All</router-link>
          </div>
          <div class="news-mini-list">
            <a
              v-for="art in result.news.slice(0, 8)"
              :key="art.id"
              :href="art.link"
              target="_blank"
              class="news-mini-item"
            >
              <span class="news-mini-source">{{ art.source }}</span>
              <span class="news-mini-title">{{ art.title }}</span>
              <span class="news-mini-date">{{ formatDate(art.published_at) }}</span>
            </a>
          </div>
        </section>
      </template>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { getPortfolio, startAnalysis, getAnalysisStatus, getAnalysisResult } from '../api/portfolio'

const route = useRoute()
const portfolioId = computed(() => route.params.portfolioId)

const portfolio = ref(null)
const result    = ref(null)
const running   = ref(false)
const runStep   = ref(0)

const analysisConfig = ref({ days_news: 7, days_filings: 30 })

function sentimentIcon(s) {
  return { bullish: '↑', neutral: '→', cautious: '⚠', bearish: '↓' }[s] || '→'
}

function formatDate(isoStr) {
  if (!isoStr) return '—'
  try {
    return new Date(isoStr).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
  } catch { return isoStr.slice(0, 10) }
}

async function runAnalysis() {
  if (!portfolio.value || running.value) return
  running.value = true
  runStep.value = 0

  try {
    // Start async job
    const startRes = await startAnalysis(portfolioId.value, analysisConfig.value)
    const analysisId = startRes.analysis_id

    // Simulate step progression while polling
    const stepTimer = setInterval(() => {
      if (runStep.value < 3) runStep.value++
    }, 8000)

    // Poll for completion
    let attempts = 0
    while (attempts < 60) {
      await new Promise(r => setTimeout(r, 4000))
      attempts++
      try {
        const statusRes = await getAnalysisStatus(portfolioId.value, analysisId)
        const tasks = statusRes.data
        const task  = Array.isArray(tasks) ? tasks[0] : tasks
        if (task?.status === 'completed') break
        if (task?.status === 'failed') {
          console.error('Analysis failed:', task.error)
          break
        }
      } catch (e) {
        console.warn('Status poll error', e)
      }
    }

    clearInterval(stepTimer)
    runStep.value = 4

    // Load result
    const resultRes = await getAnalysisResult(portfolioId.value)
    result.value = resultRes.data

  } catch (e) {
    console.error('Analysis error', e)
  } finally {
    running.value = false
  }
}

async function loadExistingResult() {
  try {
    const res = await getAnalysisResult(portfolioId.value)
    result.value = res.data
  } catch (e) {
    // No existing result — that's fine
  }
}

onMounted(async () => {
  try {
    const res = await getPortfolio(portfolioId.value)
    portfolio.value = res.data
  } catch (e) { console.error('Portfolio load failed', e) }
  await loadExistingResult()
})
</script>

<style scoped>
.portfolio-layout { display: flex; min-height: 100vh; background: #0a0a0f; color: #e2e8f0; font-family: 'JetBrains Mono', 'Fira Code', monospace; }

.sidebar { width: 240px; min-height: 100vh; background: #0d0d15; border-right: 1px solid #1e1e2e; display: flex; flex-direction: column; flex-shrink: 0; }
.sidebar-brand { padding: 20px 20px 16px; font-size: 13px; font-weight: 700; letter-spacing: 3px; color: #f97316; cursor: pointer; border-bottom: 1px solid #1e1e2e; }
.sidebar-nav { padding: 12px 0; border-bottom: 1px solid #1e1e2e; }
.nav-item { display: flex; align-items: center; gap: 8px; padding: 9px 20px; color: #64748b; text-decoration: none; font-size: 12px; transition: all 0.15s; }
.nav-item:hover, .nav-item.active { color: #e2e8f0; background: #1a1a2e; }
.nav-icon { font-size: 14px; }

.sidebar-filters { padding: 16px; flex: 1; }
.sidebar-section-title { font-size: 9px; letter-spacing: 2px; color: #334155; margin-bottom: 12px; }
.filter-group { margin-bottom: 12px; }
.filter-group label { display: block; font-size: 9px; letter-spacing: 1px; color: #475569; margin-bottom: 4px; }
.filter-select { width: 100%; background: #111827; border: 1px solid #1e2e45; border-radius: 5px; padding: 6px 8px; color: #e2e8f0; font-size: 11px; font-family: inherit; }
.btn-run { width: 100%; margin-top: 8px; background: #f97316; color: #fff; border: none; border-radius: 6px; padding: 10px; font-size: 12px; cursor: pointer; font-family: inherit; transition: background 0.15s; }
.btn-run:hover { background: #ea6a05; }
.btn-run:disabled { opacity: 0.5; cursor: not-allowed; }
.last-run-info { font-size: 9px; color: #334155; margin-top: 8px; text-align: center; }

.main-content { flex: 1; padding: 32px; overflow-y: auto; }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24px; }
.page-title { font-size: 22px; color: #f1f5f9; margin: 0; }
.page-subtitle { font-size: 11px; color: #475569; margin: 4px 0 0; }

/* Running state */
.running-state { padding: 40px; }
.pipeline-steps { display: flex; flex-direction: column; gap: 16px; }
.pipeline-step { display: flex; align-items: center; gap: 10px; font-size: 12px; color: #334155; padding: 12px 16px; background: #0d0d15; border: 1px solid #1e1e2e; border-radius: 8px; transition: all 0.3s; }
.pipeline-step.active { color: #f97316; border-color: #f97316; background: #1a0a00; }
.pipeline-step.done { color: #10b981; border-color: #064e3b; }
.step-dot { width: 8px; height: 8px; border-radius: 50%; background: currentColor; flex-shrink: 0; }
.pipeline-step.active .step-dot { animation: pulse 1s infinite; }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }

/* Empty */
.empty-state { display: flex; flex-direction: column; align-items: center; padding: 60px; gap: 12px; color: #475569; text-align: center; }
.empty-icon { font-size: 40px; color: #334155; }
.empty-state h2 { font-size: 18px; color: #94a3b8; margin: 0; }
.empty-state p { font-size: 12px; margin: 0; }
.hint { color: #334155; font-size: 10px; }

/* Sentiment Banner */
.sentiment-banner {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 20px 24px;
  border-radius: 10px;
  border: 1px solid #1e1e2e;
  margin-bottom: 16px;
  flex-wrap: wrap;
}
.sentiment-banner.bullish { background: #052e16; border-color: #064e3b; }
.sentiment-banner.cautious { background: #1c1400; border-color: #3d2900; }
.sentiment-banner.bearish  { background: #2d0000; border-color: #450a0a; }
.sentiment-banner.neutral  { background: #0d0d15; border-color: #1e1e2e; }
.sentiment-left { display: flex; align-items: center; gap: 12px; flex-shrink: 0; }
.sentiment-icon { font-size: 28px; }
.sentiment-label { font-size: 9px; letter-spacing: 2px; color: #475569; }
.sentiment-value { font-size: 18px; font-weight: 700; color: #f1f5f9; }
.sentiment-summary { flex: 1; font-size: 12px; color: #94a3b8; line-height: 1.5; }
.sentiment-meta { display: flex; gap: 12px; font-size: 10px; color: #334155; flex-shrink: 0; }
.sentiment-meta span { padding: 3px 8px; background: #0a0a0f; border-radius: 10px; border: 1px solid #1e1e2e; }

.macro-themes { display: flex; align-items: center; gap: 8px; margin-bottom: 20px; flex-wrap: wrap; }
.section-label { font-size: 9px; letter-spacing: 2px; color: #334155; }
.theme-pill { padding: 3px 10px; background: #1e1e2e; border-radius: 12px; font-size: 10px; color: #64748b; }

/* Analysis grid */
.analysis-grid { display: grid; grid-template-columns: 1fr 340px; gap: 16px; }
.card { background: #0d0d15; border: 1px solid #1e1e2e; border-radius: 10px; padding: 20px; }
.card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; gap: 12px; }
.card-header h2 { font-size: 10px; letter-spacing: 2px; color: #475569; margin: 0; }

.right-col { display: flex; flex-direction: column; }

/* Impact rows */
.impact-list { display: flex; flex-direction: column; gap: 12px; }
.impact-row { padding: 14px; border-radius: 8px; border: 1px solid #1e1e2e; background: #0a0a0f; }
.impact-row.positive { border-left: 3px solid #10b981; }
.impact-row.negative { border-left: 3px solid #ef4444; }
.impact-row.neutral  { border-left: 3px solid #475569; }
.impact-header { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.impact-ticker { font-size: 14px; font-weight: 700; color: #f97316; }
.impact-badges { display: flex; gap: 6px; margin-left: auto; }
.sentiment-tag, .level-tag { font-size: 9px; padding: 2px 7px; border-radius: 3px; letter-spacing: 0.5px; }
.sentiment-tag.positive { background: #052e16; color: #34d399; }
.sentiment-tag.negative { background: #2d0000; color: #f87171; }
.sentiment-tag.neutral  { background: #1e1e2e; color: #64748b; }
.level-tag.high   { background: #2d0000; color: #fca5a5; }
.level-tag.medium { background: #1c1400; color: #fcd34d; }
.level-tag.low    { background: #1e1e2e; color: #64748b; }
.level-tag.none   { background: #111827; color: #334155; }
.impact-analysis { font-size: 11px; color: #94a3b8; line-height: 1.6; margin: 0 0 8px; }
.impact-drivers { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.drivers-label { font-size: 9px; color: #334155; }
.driver-tag { font-size: 9px; padding: 2px 6px; background: #1e1e2e; border-radius: 3px; color: #64748b; }

/* Risk flags */
.risk-list { display: flex; flex-direction: column; gap: 10px; }
.risk-item { padding: 12px; border-radius: 7px; border: 1px solid #1e1e2e; background: #0a0a0f; }
.risk-item.high   { border-left: 3px solid #ef4444; }
.risk-item.medium { border-left: 3px solid #f59e0b; }
.risk-item.low    { border-left: 3px solid #3b82f6; }
.risk-header { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.severity-badge { font-size: 8px; padding: 1px 5px; border-radius: 3px; }
.severity-badge.high   { background: #450a0a; color: #f87171; }
.severity-badge.medium { background: #451a00; color: #fcd34d; }
.severity-badge.low    { background: #1e3a5f; color: #93c5fd; }
.risk-ticker { font-size: 12px; font-weight: 700; color: #f97316; }
.risk-flag { font-size: 12px; color: #e2e8f0; margin-bottom: 4px; font-weight: 600; }
.risk-detail { font-size: 11px; color: #64748b; line-height: 1.5; }
.risk-source { font-size: 9px; color: #334155; margin-top: 4px; }

/* Cross-industry */
.ci-list { display: flex; flex-direction: column; gap: 10px; }
.ci-item { padding: 10px; background: #0a0a0f; border: 1px solid #2e1a5f; border-radius: 7px; }
.ci-trigger { font-size: 11px; color: #a78bfa; font-weight: 600; margin-bottom: 6px; }
.ci-tickers { display: flex; gap: 4px; flex-wrap: wrap; margin-bottom: 6px; }
.ci-ticker-tag { font-size: 9px; padding: 2px 6px; background: #2e1a5f; color: #c4b5fd; border-radius: 3px; }
.ci-insight { font-size: 11px; color: #64748b; line-height: 1.5; margin: 0; }

/* Recommendations */
.recommendations-card { }
.rec-summary-label { font-size: 11px; color: #94a3b8; font-style: italic; max-width: 500px; text-align: right; }
.sub-section-title { font-size: 9px; letter-spacing: 2px; color: #475569; margin-bottom: 8px; }

/* Rebalancing */
.rebalancing-section { background: #0a0a0f; border: 1px solid #1c1400; border-radius: 8px; padding: 12px; margin-bottom: 4px; }
.rebal-list { display: flex; flex-direction: column; gap: 6px; }
.rebal-item { display: flex; align-items: center; gap: 10px; font-size: 11px; }
.rebal-ticker { font-weight: 700; color: #f97316; width: 60px; }
.rebal-direction { padding: 2px 7px; border-radius: 3px; font-size: 9px; letter-spacing: 1px; }
.rebal-direction.overweight  { background: #2d0000; color: #f87171; }
.rebal-direction.underweight { background: #052e16; color: #34d399; }
.rebal-detail { color: #64748b; }

/* Rec items */
.rec-list { display: flex; flex-direction: column; gap: 10px; }
.rec-item { padding: 14px; border-radius: 8px; border: 1px solid #1e1e2e; background: #0a0a0f; }
.rec-item.hold { border-left: 3px solid #475569; }
.rec-item.trim { border-left: 3px solid #f59e0b; }
.rec-item.add  { border-left: 3px solid #10b981; }
.rec-item.rebalance { border-left: 3px solid #6366f1; }
.rec-item.review    { border-left: 3px solid #0ea5e9; }
.rec-header { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; flex-wrap: wrap; }
.action-badge { font-size: 9px; padding: 2px 7px; border-radius: 3px; letter-spacing: 1px; font-weight: 700; }
.action-badge.hold     { background: #1e1e2e; color: #64748b; }
.action-badge.trim     { background: #451a00; color: #fcd34d; }
.action-badge.add      { background: #052e16; color: #34d399; }
.action-badge.rebalance { background: #1e1b4b; color: #a5b4fc; }
.action-badge.review   { background: #0c1a2e; color: #7dd3fc; }
.rec-ticker { font-size: 13px; font-weight: 700; color: #f97316; }
.rec-priority { font-size: 9px; padding: 2px 6px; border-radius: 3px; }
.rec-priority.high   { background: #450a0a; color: #f87171; }
.rec-priority.medium { background: #451a00; color: #fcd34d; }
.rec-priority.low    { background: #1e1e2e; color: #64748b; }
.rec-horizon { font-size: 9px; color: #334155; margin-left: auto; }
.rec-rationale { font-size: 11px; color: #94a3b8; line-height: 1.6; margin: 0 0 6px; }
.rec-adjustment { font-size: 11px; color: #64748b; }
.adj-label { color: #475569; font-size: 9px; letter-spacing: 1px; }

/* Watchlist */
.watchlist { display: flex; flex-direction: column; gap: 8px; }
.watch-item { padding: 10px 12px; background: #0a0a0f; border: 1px solid #1e1e2e; border-radius: 7px; }
.watch-header { display: flex; align-items: baseline; gap: 10px; margin-bottom: 4px; }
.watch-ticker { font-size: 12px; font-weight: 700; color: #f97316; flex-shrink: 0; }
.watch-reason { font-size: 11px; color: #94a3b8; }
.watch-trigger { font-size: 10px; color: #475569; }
.trigger-label { color: #334155; font-size: 9px; letter-spacing: 1px; }

/* Risks & Catalysts */
.risks-catalysts-row { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 16px; }
.bullet-list { margin: 0; padding-left: 16px; }
.bullet-list li { font-size: 11px; color: #64748b; line-height: 1.8; }
.bullet-list.positive li { color: #34d399; }

.next-review { display: flex; align-items: center; gap: 8px; margin-top: 20px; padding: 12px; background: #0a0a0f; border: 1px solid #1e2e45; border-radius: 8px; font-size: 12px; color: #64748b; }
.next-review-icon { font-size: 16px; color: #3b82f6; }

/* Supporting news */
.news-mini-list { display: flex; flex-direction: column; gap: 2px; }
.news-mini-item { display: grid; grid-template-columns: 80px 1fr 90px; gap: 10px; align-items: center; padding: 8px 10px; border-radius: 5px; text-decoration: none; transition: background 0.15s; }
.news-mini-item:hover { background: #111827; }
.news-mini-source { font-size: 9px; color: #475569; letter-spacing: 0.5px; }
.news-mini-title { font-size: 11px; color: #94a3b8; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.news-mini-date { font-size: 9px; color: #334155; text-align: right; }

.empty-section { font-size: 11px; color: #334155; padding: 12px 0; text-align: center; }

.btn-primary { background: #f97316; color: #fff; border: none; border-radius: 6px; padding: 8px 16px; font-size: 12px; cursor: pointer; font-family: inherit; transition: background 0.15s; }
.btn-primary:hover { background: #ea6a05; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-secondary { background: transparent; color: #94a3b8; border: 1px solid #334155; border-radius: 6px; padding: 8px 16px; font-size: 12px; cursor: pointer; font-family: inherit; text-decoration: none; }
.btn-sm { padding: 5px 10px; font-size: 10px; }

@media (max-width: 768px) {
  .portfolio-layout { flex-direction: column; }
  .sidebar { width: 100%; min-height: unset; border-right: none; border-bottom: 1px solid #1e1e2e; }
  .sidebar-filters { display: none; }
  .sidebar-nav { display: flex; flex-direction: row; padding: 0; overflow-x: auto; }
  .nav-item { padding: 12px 16px; white-space: nowrap; }
  .nav-item.active { border-bottom: 2px solid #f97316; background: transparent; }
  .main-content { padding: 16px; }
  .analysis-grid { grid-template-columns: 1fr; }
  .sentiment-banner { flex-direction: column; gap: 12px; }
  .risks-catalysts-row { grid-template-columns: 1fr; }
  .rec-header { flex-wrap: wrap; gap: 6px; }
  .news-mini-item { grid-template-columns: 70px 1fr; }
  .news-mini-date { display: none; }
  .page-header { flex-direction: column; gap: 12px; }
}
</style>
