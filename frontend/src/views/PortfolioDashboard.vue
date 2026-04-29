<template>
  <div class="portfolio-layout">
    <!-- Sidebar -->
    <aside class="sidebar">
      <div class="sidebar-brand" @click="$router.push('/')">MIROFISH</div>
      <nav class="sidebar-nav">
        <router-link to="/portfolio" class="nav-item active">
          <span class="nav-icon">◈</span> Portfolio
        </router-link>
        <router-link v-if="currentId" :to="`/portfolio/${currentId}/news`" class="nav-item">
          <span class="nav-icon">◎</span> News Feed
        </router-link>
        <router-link v-if="currentId" :to="`/portfolio/${currentId}/analysis`" class="nav-item">
          <span class="nav-icon">◐</span> Analysis
        </router-link>
      </nav>
      <div class="sidebar-portfolios">
        <div class="sidebar-section-title">MY PORTFOLIOS</div>
        <div
          v-for="p in portfolios"
          :key="p.portfolio_id"
          class="portfolio-item"
          :class="{ active: p.portfolio_id === currentId }"
          @click="selectPortfolio(p.portfolio_id)"
        >
          <span class="portfolio-name">{{ p.name }}</span>
          <span class="holding-count">{{ p.holdings.length }} holdings</span>
        </div>
        <button class="btn-new-portfolio" @click="showCreateModal = true">+ New Portfolio</button>
      </div>
    </aside>

    <!-- Main Content -->
    <main class="main-content">
      <!-- Empty state -->
      <div v-if="!currentPortfolio" class="empty-state">
        <div class="empty-icon">◈</div>
        <h2>Select or create a portfolio</h2>
        <p>Add your holdings to start receiving AI-powered analysis and recommendations.</p>
        <button class="btn-primary" @click="showCreateModal = true">Create Portfolio</button>
      </div>

      <!-- Portfolio loaded -->
      <template v-else>
        <!-- Header -->
        <div class="page-header">
          <div class="page-title-area">
            <h1 class="page-title">{{ currentPortfolio.name }}</h1>
            <span class="portfolio-id">{{ currentPortfolio.portfolio_id }}</span>
          </div>
          <div class="header-actions">
            <button class="btn-secondary" @click="showEditModal = true">Edit</button>
            <button class="btn-danger" @click="confirmDelete">Delete</button>
          </div>
        </div>

        <!-- Stats row -->
        <div class="stats-row">
          <div class="stat-card">
            <div class="stat-value">{{ currentPortfolio.holdings.length }}</div>
            <div class="stat-label">Holdings</div>
          </div>
          <div class="stat-card">
            <div class="stat-value">{{ formatCurrency(totalCost) }}</div>
            <div class="stat-label">Total Cost Basis</div>
          </div>
          <div class="stat-card">
            <div class="stat-value">{{ uniqueSectors.length }}</div>
            <div class="stat-label">Sectors</div>
          </div>
          <div class="stat-card">
            <div class="stat-value">{{ currentPortfolio.base_currency }}</div>
            <div class="stat-label">Base Currency</div>
          </div>
        </div>

        <!-- Two-column layout: holdings + allocation -->
        <div class="content-grid">
          <!-- Holdings Table -->
          <section class="card holdings-card">
            <div class="card-header">
              <h2>Holdings</h2>
              <button class="btn-primary btn-sm" @click="showHoldingModal = true">+ Add Holding</button>
            </div>

            <div v-if="currentPortfolio.holdings.length === 0" class="empty-holdings">
              <p>No holdings yet. Add your first position.</p>
            </div>

            <table v-else class="holdings-table">
              <thead>
                <tr>
                  <th>Ticker</th>
                  <th>Name</th>
                  <th>Type</th>
                  <th>Exchange</th>
                  <th>Sector</th>
                  <th>Shares</th>
                  <th>Cost Basis</th>
                  <th>Value</th>
                  <th>Weight</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="h in currentPortfolio.holdings" :key="h.ticker">
                  <td class="ticker-cell">{{ h.ticker }}</td>
                  <td class="name-cell">{{ h.name }}</td>
                  <td><span class="type-badge" :class="h.holding_type">{{ h.holding_type.toUpperCase() }}</span></td>
                  <td>{{ h.exchange }}</td>
                  <td class="sector-cell">{{ h.sector || '—' }}</td>
                  <td>{{ h.shares }}</td>
                  <td>{{ formatCurrency(h.cost_basis, h.currency) }}</td>
                  <td>{{ formatCurrency(h.shares * h.cost_basis, h.currency) }}</td>
                  <td>
                    <div class="weight-bar-wrap">
                      <div class="weight-bar" :style="{ width: holdingWeight(h) + '%' }"></div>
                      <span class="weight-label">{{ holdingWeight(h).toFixed(1) }}%</span>
                    </div>
                  </td>
                  <td>
                    <button class="btn-icon" @click="editHolding(h)">✎</button>
                    <button class="btn-icon danger" @click="removeHoldingConfirm(h.ticker)">✕</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </section>

          <!-- Allocation Breakdown -->
          <section class="card allocation-card">
            <div class="card-header"><h2>Sector Allocation</h2></div>
            <div v-if="sectorAllocation.length === 0" class="empty-holdings"><p>Add holdings to see allocation.</p></div>
            <div v-else class="sector-list">
              <div v-for="s in sectorAllocation" :key="s.sector" class="sector-row">
                <span class="sector-name">{{ s.sector }}</span>
                <div class="sector-bar-wrap">
                  <div class="sector-bar" :style="{ width: s.weight + '%', background: s.color }"></div>
                </div>
                <span class="sector-pct">{{ s.weight.toFixed(1) }}%</span>
              </div>
            </div>

            <div class="card-divider"></div>

            <!-- Quick action to launch analysis -->
            <div class="analysis-cta">
              <p class="cta-description">Get AI-powered analysis of your portfolio based on the latest news and filings.</p>
              <router-link :to="`/portfolio/${currentId}/analysis`" class="btn-primary btn-block">
                ◐ Run Analysis
              </router-link>
              <router-link :to="`/portfolio/${currentId}/news`" class="btn-secondary btn-block" style="margin-top:8px">
                ◎ View News Feed
              </router-link>
            </div>
          </section>
        </div>
      </template>
    </main>

    <!-- Create Portfolio Modal -->
    <div v-if="showCreateModal" class="modal-overlay" @click.self="showCreateModal = false">
      <div class="modal">
        <h3>New Portfolio</h3>
        <label>Name</label>
        <input v-model="newPortfolio.name" placeholder="e.g. Growth Portfolio" class="input" />
        <label>Base Currency</label>
        <select v-model="newPortfolio.base_currency" class="input">
          <option value="USD">USD</option>
          <option value="SGD">SGD</option>
          <option value="EUR">EUR</option>
          <option value="GBP">GBP</option>
        </select>
        <div class="modal-actions">
          <button class="btn-secondary" @click="showCreateModal = false">Cancel</button>
          <button class="btn-primary" @click="createPortfolio" :disabled="!newPortfolio.name">Create</button>
        </div>
      </div>
    </div>

    <!-- Edit Portfolio Modal -->
    <div v-if="showEditModal" class="modal-overlay" @click.self="showEditModal = false">
      <div class="modal">
        <h3>Edit Portfolio</h3>
        <label>Name</label>
        <input v-model="editPortfolioData.name" class="input" />
        <label>Notes</label>
        <textarea v-model="editPortfolioData.notes" class="input" rows="3" placeholder="Optional notes..."></textarea>
        <div class="modal-actions">
          <button class="btn-secondary" @click="showEditModal = false">Cancel</button>
          <button class="btn-primary" @click="savePortfolioEdit">Save</button>
        </div>
      </div>
    </div>

    <!-- Add/Edit Holding Modal -->
    <div v-if="showHoldingModal" class="modal-overlay" @click.self="closeHoldingModal">
      <div class="modal modal-wide">
        <h3>{{ editingHolding ? 'Edit' : 'Add' }} Holding</h3>
        <div class="form-grid">
          <div class="form-group">
            <label>Ticker Symbol *</label>
            <input v-model="holdingForm.ticker" placeholder="e.g. AAPL, SPY, D05" class="input" :disabled="editingHolding" />
          </div>
          <div class="form-group">
            <label>Company/Fund Name</label>
            <input v-model="holdingForm.name" placeholder="e.g. Apple Inc." class="input" />
          </div>
          <div class="form-group">
            <label>Type</label>
            <select v-model="holdingForm.holding_type" class="input">
              <option value="stock">Stock</option>
              <option value="etf">ETF</option>
            </select>
          </div>
          <div class="form-group">
            <label>Exchange</label>
            <select v-model="holdingForm.exchange" class="input">
              <option value="NYSE">NYSE</option>
              <option value="NASDAQ">NASDAQ</option>
              <option value="SGX">SGX</option>
              <option value="LSE">LSE</option>
              <option value="HKEX">HKEX</option>
              <option value="ASX">ASX</option>
              <option value="TSX">TSX</option>
              <option value="OTHER">Other</option>
            </select>
          </div>
          <div class="form-group">
            <label>Shares *</label>
            <input v-model.number="holdingForm.shares" type="number" step="0.001" min="0" class="input" />
          </div>
          <div class="form-group">
            <label>Cost Basis (per share) *</label>
            <input v-model.number="holdingForm.cost_basis" type="number" step="0.01" min="0" class="input" />
          </div>
          <div class="form-group">
            <label>Currency</label>
            <select v-model="holdingForm.currency" class="input">
              <option value="USD">USD</option>
              <option value="SGD">SGD</option>
              <option value="EUR">EUR</option>
              <option value="GBP">GBP</option>
              <option value="HKD">HKD</option>
              <option value="AUD">AUD</option>
            </select>
          </div>
          <div class="form-group">
            <label>Sector</label>
            <select v-model="holdingForm.sector" class="input">
              <option value="">— Select —</option>
              <option v-for="s in SECTORS" :key="s" :value="s">{{ s }}</option>
            </select>
          </div>
          <div class="form-group form-full">
            <label>Industry (optional)</label>
            <input v-model="holdingForm.industry" placeholder="e.g. Semiconductors, Cloud Computing" class="input" />
          </div>
        </div>
        <div class="modal-actions">
          <button class="btn-secondary" @click="closeHoldingModal">Cancel</button>
          <button class="btn-primary" @click="saveHolding" :disabled="!holdingForm.ticker || !holdingForm.shares">
            {{ editingHolding ? 'Update' : 'Add' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import {
  createPortfolio as apiCreate,
  listPortfolios as apiList,
  getPortfolio as apiGet,
  updatePortfolio as apiUpdate,
  deletePortfolio as apiDelete,
  addHolding as apiAddHolding,
  removeHolding as apiRemoveHolding,
} from '../api/portfolio'

const router = useRouter()
const route  = useRoute()

const SECTORS = [
  'Technology', 'Financials', 'Healthcare', 'Consumer Discretionary',
  'Consumer Staples', 'Industrials', 'Energy', 'Utilities', 'Materials',
  'Real Estate', 'Communication Services', 'ETF - Broad Market',
  'ETF - Sector', 'ETF - Bond', 'ETF - International',
]

const SECTOR_COLORS = [
  '#6366f1','#f59e0b','#10b981','#3b82f6','#ef4444',
  '#8b5cf6','#ec4899','#14b8a6','#f97316','#84cc16',
  '#0ea5e9','#a78bfa','#fb923c','#34d399','#60a5fa',
]

const portfolios      = ref([])
const currentPortfolio = ref(null)
const currentId        = computed(() => route.params.portfolioId || null)

const showCreateModal = ref(false)
const showEditModal   = ref(false)
const showHoldingModal = ref(false)
const editingHolding  = ref(false)

const newPortfolio = ref({ name: '', base_currency: 'USD' })
const editPortfolioData = ref({ name: '', notes: '' })
const holdingForm  = ref(emptyHoldingForm())

function emptyHoldingForm() {
  return { ticker: '', name: '', shares: '', cost_basis: '', currency: 'USD',
           exchange: 'NYSE', holding_type: 'stock', sector: '', industry: '' }
}

const totalCost = computed(() => {
  if (!currentPortfolio.value) return 0
  return currentPortfolio.value.holdings.reduce(
    (sum, h) => sum + h.shares * h.cost_basis, 0
  )
})

const uniqueSectors = computed(() => {
  if (!currentPortfolio.value) return []
  const s = new Set(currentPortfolio.value.holdings.map(h => h.sector).filter(Boolean))
  return [...s]
})

const sectorAllocation = computed(() => {
  if (!currentPortfolio.value || totalCost.value === 0) return []
  const map = {}
  for (const h of currentPortfolio.value.holdings) {
    const sector = h.sector || 'Other'
    const val    = h.shares * h.cost_basis
    map[sector]  = (map[sector] || 0) + val
  }
  return Object.entries(map)
    .map(([sector, val], i) => ({
      sector,
      weight: (val / totalCost.value) * 100,
      color:  SECTOR_COLORS[i % SECTOR_COLORS.length],
    }))
    .sort((a, b) => b.weight - a.weight)
})

function holdingWeight(h) {
  if (totalCost.value === 0) return 0
  return (h.shares * h.cost_basis / totalCost.value) * 100
}

function formatCurrency(val, currency = 'USD') {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency, maximumFractionDigits: 0 }).format(val)
}

async function loadPortfolios() {
  try {
    const res = await apiList()
    portfolios.value = res.data || []
  } catch (e) {
    console.error('Failed to load portfolios', e)
  }
}

async function loadCurrentPortfolio(id) {
  if (!id) { currentPortfolio.value = null; return }
  try {
    const res = await apiGet(id)
    currentPortfolio.value = res.data
  } catch (e) {
    console.error('Failed to load portfolio', e)
    currentPortfolio.value = null
  }
}

function selectPortfolio(id) {
  router.push(`/portfolio/${id}`)
}

async function createPortfolio() {
  try {
    const res = await apiCreate(newPortfolio.value)
    await loadPortfolios()
    showCreateModal.value = false
    newPortfolio.value = { name: '', base_currency: 'USD' }
    router.push(`/portfolio/${res.data.portfolio_id}`)
  } catch (e) {
    console.error('Create failed', e)
  }
}

async function confirmDelete() {
  if (!confirm(`Delete "${currentPortfolio.value.name}"? This cannot be undone.`)) return
  try {
    await apiDelete(currentId.value)
    await loadPortfolios()
    currentPortfolio.value = null
    router.push('/portfolio')
  } catch (e) {
    console.error('Delete failed', e)
  }
}

function openEditModal() {
  editPortfolioData.value = { name: currentPortfolio.value.name, notes: currentPortfolio.value.notes || '' }
  showEditModal.value = true
}

watch(showEditModal, (v) => {
  if (v && currentPortfolio.value) {
    editPortfolioData.value = { name: currentPortfolio.value.name, notes: currentPortfolio.value.notes || '' }
  }
})

async function savePortfolioEdit() {
  try {
    const res = await apiUpdate(currentId.value, editPortfolioData.value)
    currentPortfolio.value = res.data
    await loadPortfolios()
    showEditModal.value = false
  } catch (e) {
    console.error('Update failed', e)
  }
}

function editHolding(h) {
  holdingForm.value = { ...h }
  editingHolding.value = true
  showHoldingModal.value = true
}

function closeHoldingModal() {
  showHoldingModal.value = false
  editingHolding.value = false
  holdingForm.value = emptyHoldingForm()
}

async function saveHolding() {
  try {
    await apiAddHolding(currentId.value, holdingForm.value)
    const res = await apiGet(currentId.value)
    currentPortfolio.value = res.data
    closeHoldingModal()
  } catch (e) {
    console.error('Save holding failed', e)
  }
}

async function removeHoldingConfirm(ticker) {
  if (!confirm(`Remove ${ticker} from portfolio?`)) return
  try {
    await apiRemoveHolding(currentId.value, ticker)
    const res = await apiGet(currentId.value)
    currentPortfolio.value = res.data
  } catch (e) {
    console.error('Remove failed', e)
  }
}

watch(() => route.params.portfolioId, (id) => loadCurrentPortfolio(id), { immediate: true })

onMounted(loadPortfolios)
</script>

<style scoped>
.portfolio-layout {
  display: flex;
  min-height: 100vh;
  background: #0a0a0f;
  color: #e2e8f0;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
}

/* Sidebar */
.sidebar {
  width: 240px;
  min-height: 100vh;
  background: #0d0d15;
  border-right: 1px solid #1e1e2e;
  display: flex;
  flex-direction: column;
  padding: 0;
  flex-shrink: 0;
}
.sidebar-brand {
  padding: 20px 20px 16px;
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 3px;
  color: #f97316;
  cursor: pointer;
  border-bottom: 1px solid #1e1e2e;
}
.sidebar-nav {
  padding: 12px 0;
  border-bottom: 1px solid #1e1e2e;
}
.nav-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 20px;
  color: #64748b;
  text-decoration: none;
  font-size: 12px;
  transition: all 0.15s;
}
.nav-item:hover, .nav-item.active { color: #e2e8f0; background: #1a1a2e; }
.nav-icon { font-size: 14px; }
.sidebar-portfolios { padding: 16px 0; flex: 1; }
.sidebar-section-title {
  padding: 4px 20px 8px;
  font-size: 9px;
  letter-spacing: 2px;
  color: #334155;
}
.portfolio-item {
  padding: 8px 20px;
  cursor: pointer;
  transition: background 0.15s;
}
.portfolio-item:hover { background: #1a1a2e; }
.portfolio-item.active { background: #1a1a2e; border-left: 2px solid #f97316; }
.portfolio-name { display: block; font-size: 12px; color: #e2e8f0; }
.holding-count { font-size: 10px; color: #475569; }
.btn-new-portfolio {
  display: block;
  margin: 12px 16px 0;
  padding: 8px;
  background: transparent;
  border: 1px solid #334155;
  border-radius: 6px;
  color: #64748b;
  font-size: 11px;
  cursor: pointer;
  text-align: center;
  font-family: inherit;
  transition: all 0.15s;
}
.btn-new-portfolio:hover { border-color: #f97316; color: #f97316; }

/* Main */
.main-content { flex: 1; padding: 32px; overflow-y: auto; }

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 60vh;
  gap: 16px;
  color: #475569;
}
.empty-icon { font-size: 48px; color: #334155; }
.empty-state h2 { font-size: 20px; color: #94a3b8; margin: 0; }
.empty-state p { font-size: 13px; text-align: center; margin: 0; }

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}
.page-title { font-size: 22px; margin: 0; color: #f1f5f9; }
.portfolio-id { font-size: 10px; color: #334155; display: block; margin-top: 2px; }
.header-actions { display: flex; gap: 8px; }

/* Stats row */
.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 24px;
}
.stat-card {
  background: #0d0d15;
  border: 1px solid #1e1e2e;
  border-radius: 8px;
  padding: 16px;
  text-align: center;
}
.stat-value { font-size: 20px; font-weight: 700; color: #f97316; }
.stat-label { font-size: 10px; color: #475569; margin-top: 4px; letter-spacing: 1px; }

/* Content grid */
.content-grid {
  display: grid;
  grid-template-columns: 1fr 300px;
  gap: 20px;
}

.card {
  background: #0d0d15;
  border: 1px solid #1e1e2e;
  border-radius: 10px;
  padding: 20px;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.card-header h2 { font-size: 13px; letter-spacing: 1px; color: #94a3b8; margin: 0; }

/* Holdings table */
.holdings-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}
.holdings-table th {
  text-align: left;
  color: #475569;
  font-size: 10px;
  letter-spacing: 1px;
  padding: 8px 6px;
  border-bottom: 1px solid #1e1e2e;
}
.holdings-table td {
  padding: 10px 6px;
  border-bottom: 1px solid #111827;
  color: #cbd5e1;
}
.holdings-table tr:last-child td { border-bottom: none; }
.ticker-cell { font-weight: 700; color: #f97316; font-size: 13px; }
.name-cell { color: #94a3b8; max-width: 140px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.sector-cell { color: #64748b; }

.type-badge {
  font-size: 9px;
  padding: 2px 6px;
  border-radius: 3px;
  letter-spacing: 1px;
}
.type-badge.stock { background: #1e3a5f; color: #60a5fa; }
.type-badge.etf   { background: #3b1a5f; color: #a78bfa; }

.weight-bar-wrap {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 90px;
}
.weight-bar {
  height: 4px;
  background: #f97316;
  border-radius: 2px;
  min-width: 2px;
  max-width: 60px;
  transition: width 0.3s;
}
.weight-label { font-size: 10px; color: #64748b; }

.btn-icon {
  background: none;
  border: none;
  color: #475569;
  cursor: pointer;
  font-size: 13px;
  padding: 2px 6px;
  border-radius: 3px;
  font-family: inherit;
  transition: color 0.15s;
}
.btn-icon:hover { color: #94a3b8; }
.btn-icon.danger:hover { color: #ef4444; }

.empty-holdings { padding: 24px; text-align: center; color: #334155; font-size: 12px; }

/* Allocation */
.sector-list { display: flex; flex-direction: column; gap: 10px; }
.sector-row { display: flex; align-items: center; gap: 8px; }
.sector-name { font-size: 11px; color: #94a3b8; width: 110px; flex-shrink: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.sector-bar-wrap { flex: 1; height: 6px; background: #1e1e2e; border-radius: 3px; overflow: hidden; }
.sector-bar { height: 100%; border-radius: 3px; transition: width 0.4s; }
.sector-pct { font-size: 10px; color: #475569; width: 36px; text-align: right; }
.card-divider { border: none; border-top: 1px solid #1e1e2e; margin: 20px 0; }

.analysis-cta { }
.cta-description { font-size: 11px; color: #475569; margin: 0 0 12px; line-height: 1.5; }
.btn-block { display: block; width: 100%; text-align: center; text-decoration: none; }

/* Buttons */
.btn-primary {
  background: #f97316;
  color: #fff;
  border: none;
  border-radius: 6px;
  padding: 8px 16px;
  font-size: 12px;
  cursor: pointer;
  font-family: inherit;
  transition: background 0.15s;
}
.btn-primary:hover { background: #ea6a05; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-secondary {
  background: transparent;
  color: #94a3b8;
  border: 1px solid #334155;
  border-radius: 6px;
  padding: 8px 16px;
  font-size: 12px;
  cursor: pointer;
  font-family: inherit;
  transition: all 0.15s;
}
.btn-secondary:hover { border-color: #94a3b8; color: #e2e8f0; }
.btn-danger {
  background: transparent;
  color: #ef4444;
  border: 1px solid #450a0a;
  border-radius: 6px;
  padding: 8px 16px;
  font-size: 12px;
  cursor: pointer;
  font-family: inherit;
  transition: all 0.15s;
}
.btn-danger:hover { background: #450a0a; }
.btn-sm { padding: 5px 10px; font-size: 11px; }

/* Modal */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
.modal {
  background: #0d0d15;
  border: 1px solid #1e1e2e;
  border-radius: 12px;
  padding: 28px;
  min-width: 360px;
  max-width: 90vw;
}
.modal-wide { min-width: 560px; }
.modal h3 { font-size: 15px; color: #f1f5f9; margin: 0 0 20px; }
.modal label { display: block; font-size: 10px; color: #64748b; letter-spacing: 1px; margin: 12px 0 4px; }
.input {
  width: 100%;
  background: #111827;
  border: 1px solid #1e2e45;
  border-radius: 6px;
  padding: 8px 10px;
  color: #e2e8f0;
  font-size: 12px;
  font-family: inherit;
  box-sizing: border-box;
  outline: none;
}
.input:focus { border-color: #f97316; }
.modal-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 20px; }

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0 16px;
}
.form-group { }
.form-full { grid-column: 1 / -1; }
</style>
