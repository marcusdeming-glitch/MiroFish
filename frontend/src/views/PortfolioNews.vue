<template>
  <div class="portfolio-layout">
    <!-- Sidebar -->
    <aside class="sidebar">
      <div class="sidebar-brand" @click="$router.push('/')">MIROFISH</div>
      <nav class="sidebar-nav">
        <router-link :to="`/portfolio/${portfolioId}`" class="nav-item">
          <span class="nav-icon">◈</span> Portfolio
        </router-link>
        <router-link :to="`/portfolio/${portfolioId}/news`" class="nav-item active">
          <span class="nav-icon">◎</span> News Feed
        </router-link>
        <router-link :to="`/portfolio/${portfolioId}/analysis`" class="nav-item">
          <span class="nav-icon">◐</span> Analysis
        </router-link>
      </nav>
      <!-- Filters -->
      <div class="sidebar-filters">
        <div class="sidebar-section-title">FILTERS</div>
        <div class="filter-group">
          <label>Time Range</label>
          <select v-model="daysBack" class="filter-select" @change="fetchNews">
            <option :value="3">Last 3 days</option>
            <option :value="7">Last 7 days</option>
            <option :value="14">Last 14 days</option>
            <option :value="30">Last 30 days</option>
          </select>
        </div>
        <div class="filter-group">
          <label>Source</label>
          <select v-model="sourceFilter" class="filter-select">
            <option value="">All Sources</option>
            <option v-for="s in availableSources" :key="s" :value="s">{{ s }}</option>
          </select>
        </div>
        <div class="filter-group">
          <label>Impact</label>
          <select v-model="impactFilter" class="filter-select">
            <option value="">All Articles</option>
            <option value="direct">Direct Impact</option>
            <option value="ripple">Cross-Industry</option>
          </select>
        </div>
        <div class="filter-group">
          <label>Ticker</label>
          <select v-model="tickerFilter" class="filter-select">
            <option value="">All Holdings</option>
            <option v-for="t in portfolioTickers" :key="t" :value="t">{{ t }}</option>
          </select>
        </div>
      </div>
    </aside>

    <!-- Main -->
    <main class="main-content">
      <div class="page-header">
        <div>
          <h1 class="page-title">News Feed</h1>
          <p class="page-subtitle">{{ portfolio?.name }} — AI-filtered news relevant to your holdings</p>
        </div>
        <button class="btn-primary" @click="fetchNews" :disabled="loading">
          {{ loading ? 'Fetching…' : '↺ Refresh' }}
        </button>
      </div>

      <!-- Stats bar -->
      <div class="news-stats" v-if="articles.length">
        <span class="stat-pill">{{ filteredArticles.length }} articles</span>
        <span class="stat-pill direct">{{ directCount }} direct impact</span>
        <span class="stat-pill ripple">{{ rippleCount }} cross-industry</span>
        <span class="stat-pill neutral">{{ neutralCount }} general</span>
      </div>

      <!-- Loading -->
      <div v-if="loading" class="loading-state">
        <div class="spinner"></div>
        <p>Scanning news sources for portfolio-relevant content…</p>
        <p class="loading-hint">Checking Reuters, CNBC, MarketWatch, Yahoo Finance, FT, Bloomberg…</p>
      </div>

      <!-- Empty -->
      <div v-else-if="!articles.length && !loading" class="empty-state">
        <div class="empty-icon">◎</div>
        <h2>No news fetched yet</h2>
        <p>Click Refresh to fetch the latest news for your portfolio holdings.</p>
        <button class="btn-primary" @click="fetchNews">Fetch News</button>
      </div>

      <!-- No results after filter -->
      <div v-else-if="filteredArticles.length === 0" class="empty-state">
        <p>No articles match the current filters.</p>
        <button class="btn-secondary" @click="clearFilters">Clear Filters</button>
      </div>

      <!-- Article list -->
      <div v-else class="article-list">
        <article
          v-for="art in filteredArticles"
          :key="art.id"
          class="article-card"
          :class="{ 'is-direct': art.direct_tickers?.length, 'is-ripple': art.ripple_tickers?.length && !art.direct_tickers?.length }"
        >
          <div class="article-meta">
            <span class="source-badge">{{ art.source }}</span>
            <span class="article-date">{{ formatDate(art.published_at) }}</span>
            <span v-if="art.direct_tickers?.length" class="impact-badge direct">Direct Impact</span>
            <span v-else-if="art.ripple_tickers?.length" class="impact-badge ripple">Cross-Industry</span>
          </div>

          <a :href="art.link" target="_blank" rel="noopener noreferrer" class="article-title">
            {{ art.title }}
          </a>

          <p class="article-summary">{{ art.summary }}</p>

          <div class="article-tickers" v-if="art.affected_tickers?.length">
            <span class="ticker-label">Affects:</span>
            <span
              v-for="t in art.affected_tickers"
              :key="t"
              class="ticker-tag"
              :class="{ direct: art.direct_tickers?.includes(t), ripple: art.ripple_tickers?.includes(t) && !art.direct_tickers?.includes(t) }"
            >{{ t }}</span>
          </div>

          <div class="cross-industry-note" v-if="art.ripple_tickers?.length">
            <span class="ci-icon">⟳</span>
            Cross-industry signal: news affecting a related sector may ripple into your holdings.
          </div>
        </article>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { getPortfolio, getPortfolioNews } from '../api/portfolio'

const route = useRoute()
const portfolioId = computed(() => route.params.portfolioId)

const portfolio  = ref(null)
const articles   = ref([])
const loading    = ref(false)

const daysBack     = ref(7)
const sourceFilter = ref('')
const impactFilter = ref('')
const tickerFilter = ref('')

const portfolioTickers = computed(() =>
  (portfolio.value?.holdings || []).map(h => h.ticker)
)

const availableSources = computed(() => {
  const s = new Set(articles.value.map(a => a.source).filter(Boolean))
  return [...s].sort()
})

const filteredArticles = computed(() => {
  let list = articles.value
  if (sourceFilter.value)
    list = list.filter(a => a.source === sourceFilter.value)
  if (impactFilter.value === 'direct')
    list = list.filter(a => a.direct_tickers?.length > 0)
  if (impactFilter.value === 'ripple')
    list = list.filter(a => a.ripple_tickers?.length > 0 && !a.direct_tickers?.length)
  if (tickerFilter.value)
    list = list.filter(a => a.affected_tickers?.includes(tickerFilter.value))
  return list
})

const directCount  = computed(() => articles.value.filter(a => a.direct_tickers?.length).length)
const rippleCount  = computed(() => articles.value.filter(a => a.ripple_tickers?.length && !a.direct_tickers?.length).length)
const neutralCount = computed(() => articles.value.filter(a => !a.affected_tickers?.length).length)

function formatDate(isoStr) {
  if (!isoStr) return ''
  try {
    return new Date(isoStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
  } catch { return isoStr.slice(0, 10) }
}

function clearFilters() {
  sourceFilter.value = ''
  impactFilter.value = ''
  tickerFilter.value = ''
}

async function fetchNews() {
  if (!portfolioId.value) return
  loading.value = true
  try {
    const res = await getPortfolioNews(portfolioId.value, { days: daysBack.value, max: 80 })
    articles.value = res.data || []
  } catch (e) {
    console.error('News fetch failed', e)
  } finally {
    loading.value = false
  }
}

async function loadPortfolio() {
  try {
    const res = await getPortfolio(portfolioId.value)
    portfolio.value = res.data
  } catch (e) {
    console.error('Portfolio load failed', e)
  }
}

onMounted(async () => {
  await loadPortfolio()
  await fetchNews()
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

.sidebar-filters { padding: 16px 16px; }
.sidebar-section-title { font-size: 9px; letter-spacing: 2px; color: #334155; margin-bottom: 12px; }
.filter-group { margin-bottom: 12px; }
.filter-group label { display: block; font-size: 9px; letter-spacing: 1px; color: #475569; margin-bottom: 4px; }
.filter-select { width: 100%; background: #111827; border: 1px solid #1e2e45; border-radius: 5px; padding: 6px 8px; color: #e2e8f0; font-size: 11px; font-family: inherit; outline: none; }
.filter-select:focus { border-color: #f97316; }

.main-content { flex: 1; padding: 32px; overflow-y: auto; }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; }
.page-title { font-size: 22px; color: #f1f5f9; margin: 0; }
.page-subtitle { font-size: 11px; color: #475569; margin: 4px 0 0; }

.news-stats { display: flex; gap: 8px; margin-bottom: 20px; flex-wrap: wrap; }
.stat-pill { padding: 4px 10px; border-radius: 12px; font-size: 10px; background: #1e1e2e; color: #64748b; letter-spacing: 0.5px; }
.stat-pill.direct { background: #1e3a5f; color: #60a5fa; }
.stat-pill.ripple { background: #3b1a5f; color: #a78bfa; }
.stat-pill.neutral { background: #111827; color: #475569; }

.loading-state { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 60px; gap: 12px; color: #475569; text-align: center; }
.spinner { width: 32px; height: 32px; border: 2px solid #1e1e2e; border-top-color: #f97316; border-radius: 50%; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.loading-hint { font-size: 10px; color: #334155; }

.empty-state { display: flex; flex-direction: column; align-items: center; padding: 60px; gap: 12px; color: #475569; text-align: center; }
.empty-icon { font-size: 40px; color: #334155; }
.empty-state h2 { font-size: 18px; color: #94a3b8; margin: 0; }
.empty-state p { font-size: 12px; margin: 0; }

.article-list { display: flex; flex-direction: column; gap: 12px; }

.article-card {
  background: #0d0d15;
  border: 1px solid #1e1e2e;
  border-radius: 10px;
  padding: 16px 20px;
  transition: border-color 0.2s;
}
.article-card:hover { border-color: #334155; }
.article-card.is-direct { border-left: 3px solid #3b82f6; }
.article-card.is-ripple { border-left: 3px solid #8b5cf6; }

.article-meta { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; flex-wrap: wrap; }
.source-badge { font-size: 9px; letter-spacing: 1px; padding: 2px 7px; border-radius: 3px; background: #1e1e2e; color: #64748b; }
.article-date { font-size: 10px; color: #334155; }
.impact-badge { font-size: 9px; padding: 2px 7px; border-radius: 3px; letter-spacing: 0.5px; }
.impact-badge.direct { background: #1e3a5f; color: #60a5fa; }
.impact-badge.ripple { background: #3b1a5f; color: #a78bfa; }

.article-title { display: block; font-size: 13px; color: #e2e8f0; text-decoration: none; font-weight: 600; margin-bottom: 8px; line-height: 1.4; transition: color 0.15s; }
.article-title:hover { color: #f97316; }
.article-summary { font-size: 11px; color: #64748b; line-height: 1.6; margin: 0 0 10px; }

.article-tickers { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.ticker-label { font-size: 9px; color: #475569; letter-spacing: 1px; }
.ticker-tag { font-size: 10px; padding: 2px 7px; border-radius: 4px; font-weight: 600; }
.ticker-tag.direct { background: #1e3a5f; color: #93c5fd; }
.ticker-tag.ripple { background: #2e1a5f; color: #c4b5fd; }

.cross-industry-note { margin-top: 8px; font-size: 10px; color: #4c1d95; background: #1e0a3a; padding: 6px 10px; border-radius: 5px; display: flex; align-items: center; gap: 6px; }
.ci-icon { font-size: 13px; color: #7c3aed; }

.btn-primary { background: #f97316; color: #fff; border: none; border-radius: 6px; padding: 8px 16px; font-size: 12px; cursor: pointer; font-family: inherit; transition: background 0.15s; }
.btn-primary:hover { background: #ea6a05; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-secondary { background: transparent; color: #94a3b8; border: 1px solid #334155; border-radius: 6px; padding: 8px 16px; font-size: 12px; cursor: pointer; font-family: inherit; }
.btn-secondary:hover { border-color: #94a3b8; color: #e2e8f0; }
</style>
