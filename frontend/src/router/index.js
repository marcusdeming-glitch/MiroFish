import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Process from '../views/MainView.vue'
import SimulationView from '../views/SimulationView.vue'
import SimulationRunView from '../views/SimulationRunView.vue'
import ReportView from '../views/ReportView.vue'
import InteractionView from '../views/InteractionView.vue'
import PortfolioDashboard from '../views/PortfolioDashboard.vue'
import PortfolioNews from '../views/PortfolioNews.vue'
import PortfolioAnalysis from '../views/PortfolioAnalysis.vue'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: Home
  },
  {
    path: '/process/:projectId',
    name: 'Process',
    component: Process,
    props: true
  },
  {
    path: '/simulation/:simulationId',
    name: 'Simulation',
    component: SimulationView,
    props: true
  },
  {
    path: '/simulation/:simulationId/start',
    name: 'SimulationRun',
    component: SimulationRunView,
    props: true
  },
  {
    path: '/report/:reportId',
    name: 'Report',
    component: ReportView,
    props: true
  },
  {
    path: '/interaction/:reportId',
    name: 'Interaction',
    component: InteractionView,
    props: true
  },
  // Portfolio Analysis Module
  {
    path: '/portfolio',
    name: 'Portfolio',
    component: PortfolioDashboard
  },
  {
    path: '/portfolio/:portfolioId',
    name: 'PortfolioDetail',
    component: PortfolioDashboard,
    props: true
  },
  {
    path: '/portfolio/:portfolioId/news',
    name: 'PortfolioNews',
    component: PortfolioNews,
    props: true
  },
  {
    path: '/portfolio/:portfolioId/analysis',
    name: 'PortfolioAnalysis',
    component: PortfolioAnalysis,
    props: true
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
