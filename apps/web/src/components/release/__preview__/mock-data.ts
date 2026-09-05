import type {
  ReleaseDashboardSummary,
  ReleaseGoal,
  ReleaseBudget,
  ReleaseTransaction,
  ReleaseCategory,
  ReleaseReport,
  ReleaseReportAnalytics,
  ReleaseProfile,
  ReleaseNavItem,
} from "@/components/release/types"

export const mockProfile: ReleaseProfile = {
  name: "João Silva",
  email: "joao.silva@email.com",
  avatarUrl: "",
  phone: "+55 (11) 98765-4321",
  tier: "Investidor Pro",
}

export const mockNavItems: ReleaseNavItem[] = [
  { label: "Início", icon: "home", href: "/app", isActive: true },
  { label: "Portfólio", icon: "portfolio", href: "/app/portfolio" },
  { label: "Transferir", icon: "transferir", href: "/app/transferir" },
  { label: "Mercado", icon: "mercado", href: "/app/mercado" },
  { label: "Ajustes", icon: "ajustes", href: "/app/configuracoes" },
]

export const mockDashboardSummary: ReleaseDashboardSummary = {
  totalBalance: 24562.0,
  income: 8450.0,
  expenses: 3240.0,
  recentTransactions: [
    {
      id: "1",
      name: "Supermercado",
      category: "alimentacao",
      categoryIcon: "🛒",
      amount: 124.5,
      date: "Hoje, 10:45",
      type: "despesa",
    },
    {
      id: "2",
      name: "Jantar",
      category: "alimentacao",
      categoryIcon: "🍽️",
      amount: 85.0,
      date: "Ontem, 20:00",
      type: "despesa",
    },
    {
      id: "3",
      name: "Depósito de Salário",
      category: "receita",
      categoryIcon: "💰",
      amount: 3200.0,
      date: "Ontem, 08:00",
      type: "receita",
    },
    {
      id: "4",
      name: "Amazon",
      category: "compras",
      categoryIcon: "🛍️",
      amount: 145.99,
      date: "12 Mai, 14:30",
      type: "despesa",
    },
  ],
  categoryBreakdown: [
    { name: "Moradia", percentage: 45, amount: 1200, color: "#7B1FA2", emoji: "🏠" },
    { name: "Alimentação", percentage: 25, amount: 680, color: "#FF6D00", emoji: "🍽️" },
    { name: "Transporte", percentage: 15, amount: 410, color: "#0057FF", emoji: "🚗" },
    { name: "Lazer", percentage: 15, amount: 390, color: "#D500F9", emoji: "🎬" },
  ],
  goals: [
    { name: "Reserva de Emergência", current: 4200, target: 5000, percentage: 84 },
    { name: "Mercado Mensal", current: 320, target: 600, percentage: 53 },
  ],
  budgets: [
    { name: "Alimentação", spent: 800, total: 1000, remaining: 200, percentage: 80 },
    { name: "Transporte", spent: 380, total: 400, remaining: 20, percentage: 95 },
  ],
}

export const mockGoals: ReleaseGoal[] = [
  {
    id: "1",
    name: "Viagem Japão",
    target: 5000,
    current: 4200,
    deadline: "2024-12",
    category: "viagem",
    color: "#1652f0",
  },
  {
    id: "2",
    name: "Reserva de Emergência",
    target: 15000,
    current: 10000,
    deadline: "2025-06",
    category: "outro",
  },
  {
    id: "3",
    name: "Novo Carro",
    target: 5000,
    current: 1200,
    deadline: "2025-12",
    category: "veiculo",
  },
]

export const mockBudgets: ReleaseBudget[] = [
  {
    id: "1",
    category: "Alimentação",
    categoryIcon: "🍽️",
    categoryColor: "blue",
    spent: 800,
    total: 1000,
    remaining: 200,
    percentage: 80,
    budgetDate: "2026-05-23",
  },
  {
    id: "2",
    category: "Transporte",
    categoryIcon: "🚗",
    categoryColor: "red",
    spent: 380,
    total: 400,
    remaining: 20,
    percentage: 95,
    budgetDate: "2026-05-23",
  },
  {
    id: "3",
    category: "Lazer",
    categoryIcon: "🎬",
    categoryColor: "green",
    spent: 200,
    total: 500,
    remaining: 300,
    percentage: 40,
    budgetDate: "2026-05-23",
  },
  {
    id: "4",
    category: "Saúde",
    categoryIcon: "❤️",
    categoryColor: "pink",
    spent: 350,
    total: 500,
    remaining: 150,
    percentage: 70,
    budgetDate: "2026-05-23",
  },
]

export const mockTransactions: ReleaseTransaction[] = [
  {
    id: "1",
    name: "Starbucks",
    category: "alimentacao",
    categoryIcon: "☕",
    amount: 12.5,
    date: "Hoje",
    type: "despesa",
  },
  {
    id: "2",
    name: "Uber",
    category: "transporte",
    categoryIcon: "🚕",
    amount: 24.0,
    date: "Hoje",
    type: "despesa",
  },
  {
    id: "3",
    name: "Depósito de Salário",
    category: "receita",
    categoryIcon: "💰",
    amount: 3200.0,
    date: "Ontem",
    type: "receita",
  },
  {
    id: "4",
    name: "Amazon",
    category: "compras",
    categoryIcon: "🛍️",
    amount: 145.99,
    date: "Ontem",
    type: "despesa",
  },
  {
    id: "5",
    name: "Netflix",
    category: "lazer",
    categoryIcon: "🎬",
    amount: 15.49,
    date: "Ontem",
    type: "despesa",
  },
]

export const mockCategories: ReleaseCategory[] = [
  { name: "Alimentação", icon: "🍽️", color: "#ef4444", allocated: 1200, percentage: 80, type: "despesa" },
  { name: "Moradia", icon: "🏠", color: "#3b82f6", allocated: 2500, isFixed: true, type: "despesa" },
  { name: "Transporte", icon: "🚗", color: "#22c55e", allocated: 400, percentage: 45, type: "despesa" },
  { name: "Lazer", icon: "🎬", color: "#f97316", allocated: 300, percentage: 90, type: "despesa" },
  { name: "Saúde", icon: "❤️", color: "#a855f7", allocated: 100, percentage: 20, type: "despesa" },
]

export const mockReports: ReleaseReport[] = [
  {
    id: "1",
    name: "Relatório Mensal - Abril",
    period: "Abril 2024",
    date: "01 Maio 2024",
    status: "concluido",
    type: "mensal",
  },
  {
    id: "2",
    name: "Declaração de IR 2023",
    period: "Anual 2023",
    date: "15 Abril 2024",
    status: "concluido",
    type: "imposto",
  },
  {
    id: "3",
    name: "Relatório Anual 2023",
    period: "Anual 2023",
    date: "10 Jan 2024",
    status: "arquivado",
    type: "anual",
  },
]

export const mockReportAnalytics: ReleaseReportAnalytics = {
  balance: 5210,
  income: 8450,
  expenses: 3240,
  categoryExpenses: [
    { name: "Moradia", amount: 1500, color: "#1652f0" },
    { name: "Alimentação", amount: 920, color: "#ff9500" },
    { name: "Transporte", amount: 480, color: "#3b82f6" },
  ],
  monthlyExpenses: [
    { label: "maio de 2026", amount: 3240 },
    { label: "abril de 2026", amount: 2870 },
    { label: "março de 2026", amount: 3010 },
  ],
  weeklyExpenses: [
    { label: "03 mai - 09 mai", amount: 1220 },
    { label: "26 abr - 02 mai", amount: 860 },
  ],
  dailyExpenses: [
    { label: "09 mai", amount: 420 },
    { label: "08 mai", amount: 180 },
    { label: "07 mai", amount: 620 },
  ],
}
