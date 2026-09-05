import type { Transaction, Account, Card, Budget, Goal, Report } from "@/types"

export const MOCK_TRANSACTIONS: Transaction[] = [
  { id: "1", name: "Supermercado Pão de Açúcar", category: "Alimentação", type: "despesa", amount: 287.50, date: "30 Abr", source: "whatsapp", status: "confirmed" },
  { id: "2", name: "Salário — Empresa X", category: "Salário", type: "receita", amount: 8500.00, date: "28 Abr", source: "auto", status: "confirmed" },
  { id: "3", name: "Uber — Centro → Vila Madalena", category: "Transporte", type: "despesa", amount: 34.90, date: "28 Abr", source: "whatsapp", status: "pending" },
  { id: "4", name: "Netflix mensal", category: "Lazer", type: "despesa", amount: 55.90, date: "27 Abr", source: "auto", status: "confirmed" },
  { id: "5", name: "Farmácia Drogasil", category: "Saúde", type: "despesa", amount: 89.40, date: "27 Abr", source: "whatsapp", status: "pending" },
  { id: "6", name: "Aluguel — Abril", category: "Moradia", type: "despesa", amount: 2200.00, date: "25 Abr", source: "auto", status: "confirmed" },
  { id: "7", name: "Curso de Python — Udemy", category: "Educação", type: "despesa", amount: 49.90, date: "24 Abr", source: "manual", status: "confirmed" },
  { id: "8", name: "iFood — Restaurante Sukiya", category: "Alimentação", type: "despesa", amount: 62.80, date: "23 Abr", source: "whatsapp", status: "confirmed" },
  { id: "9", name: "Uber — Pinheiros → Moema", category: "Transporte", type: "despesa", amount: 42.30, date: "22 Abr", source: "whatsapp", status: "confirmed" },
  { id: "10", name: "Spotify Premium", category: "Lazer", type: "despesa", amount: 21.90, date: "20 Abr", source: "auto", status: "confirmed" },
  { id: "11", name: "Freelance — Projeto Design", category: "Salário", type: "receita", amount: 3200.00, date: "18 Abr", source: "manual", status: "confirmed" },
  { id: "12", name: "Academia SmartFit", category: "Saúde", type: "despesa", amount: 99.90, date: "15 Abr", source: "auto", status: "confirmed" },
]

export const MOCK_ACCOUNTS: Account[] = [
  { id: "1", name: "Conta Corrente", bank: "Nubank", balance: 4847.60, icon: "🏦" },
  { id: "2", name: "Poupança", bank: "Nubank", balance: 14200.00, icon: "🐷" },
  { id: "3", name: "Investimentos", bank: "XP Investimentos", balance: 23500.00, icon: "📈" },
  { id: "4", name: "Dinheiro", bank: "Carteira", balance: 120.00, icon: "💵" },
]

export const MOCK_CARDS: Card[] = [
  { id: "1", name: "Nubank Platinum", last4: "4821", limit: 8000, used: 2340, closingDay: 15, dueDay: 22, color: "#820ad1" },
  { id: "2", name: "Inter Gold", last4: "7392", limit: 5000, used: 1870, closingDay: 10, dueDay: 18, color: "#ff6600" },
  { id: "3", name: "Itaú Uniclass", last4: "1055", limit: 12000, used: 4200, closingDay: 20, dueDay: 28, color: "#003399" },
]

export const MOCK_BUDGETS: Budget[] = [
  { category: "Alimentação", budget: 1500, spent: 1150, color: "#ff6b35" },
  { category: "Transporte", budget: 600, spent: 380, color: "#0052ff" },
  { category: "Lazer", budget: 400, spent: 356, color: "#ffab00" },
  { category: "Moradia", budget: 2200, spent: 2200, color: "#7c3aed" },
  { category: "Saúde", budget: 300, spent: 89, color: "#00c853" },
  { category: "Educação", budget: 200, spent: 149, color: "#2196f3" },
]

export const MOCK_GOALS: Goal[] = [
  { id: "1", name: "Viagem para Portugal", target: 12000, current: 4800, deadline: "Dez 2026", color: "#0052ff" },
  { id: "2", name: "Reserva de emergência", target: 20000, current: 14200, deadline: "Mar 2027", color: "#00c853" },
  { id: "3", name: "MacBook Pro", target: 15000, current: 3200, deadline: "Jun 2026", color: "#7c3aed" },
]

export const MOCK_REPORTS: Report[] = [
  { id: "1", name: "Relatório Mensal — Abril 2026", period: "Abr 2026", date: "30 Abr 2026", size: "2.4 MB", type: "full" },
  { id: "2", name: "Despesas por Categoria — Mar 2026", period: "Mar 2026", date: "31 Mar 2026", size: "1.1 MB", type: "expenses" },
  { id: "3", name: "Resumo Financeiro — Q1 2026", period: "Jan–Mar 2026", date: "01 Abr 2026", size: "3.8 MB", type: "quarterly" },
  { id: "4", name: "Relatório Mensal — Fevereiro 2026", period: "Fev 2026", date: "28 Fev 2026", size: "2.1 MB", type: "full" },
  { id: "5", name: "Comparativo 2025 vs 2026", period: "2025–2026", date: "15 Fev 2026", size: "4.2 MB", type: "comparison" },
  { id: "6", name: "Relatório Mensal — Janeiro 2026", period: "Jan 2026", date: "31 Jan 2026", size: "1.9 MB", type: "full" },
]

export const BALANCE_HISTORY = [6200, 6500, 6100, 5900, 6300, 6800, 7200, 7100, 7500, 7800, 8200, 8347]

export const MONTHLY_DATA = [
  { label: "Jan", value: 6200, color: "#0052ff" },
  { label: "Fev", value: 5100, color: "#0052ff" },
  { label: "Mar", value: 7300, color: "#0052ff" },
  { label: "Abr", value: 8500, color: "#0052ff" },
]
