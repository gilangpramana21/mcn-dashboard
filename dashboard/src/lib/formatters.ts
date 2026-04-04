/**
 * Format follower count ke format singkat (K/M)
 * Contoh: 1200 → "1.2K", 1500000 → "1.5M"
 */
export function formatFollowerCount(n: number): string {
  if (n >= 1_000_000) {
    return `${(n / 1_000_000).toFixed(1)}M`
  }
  if (n >= 1_000) {
    return `${(n / 1_000).toFixed(1)}K`
  }
  return String(n)
}

/**
 * Format engagement rate ke persentase dengan 2 desimal
 * Contoh: 5.123 → "5.12%"
 */
export function formatEngagementRate(rate: number): string {
  return `${rate.toFixed(2)}%`
}

/**
 * Format angka ke format mata uang IDR
 * Contoh: 1500000 → "Rp 1.500.000"
 */
export function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('id-ID', {
    style: 'currency',
    currency: 'IDR',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount)
}

/**
 * Format angka ke format mata uang IDR singkat untuk KPI card
 * Contoh: 1.500.000 → "Rp 1,5 Jt", 2.000.000.000 → "Rp 2 M"
 */
export function formatCurrencyCompact(amount: number): string {
  if (amount >= 1_000_000_000_000) {
    return `Rp ${(amount / 1_000_000_000_000).toFixed(1)} T`
  }
  if (amount >= 1_000_000_000) {
    return `Rp ${(amount / 1_000_000_000).toFixed(1)} M`
  }
  if (amount >= 1_000_000) {
    return `Rp ${(amount / 1_000_000).toFixed(1)} Jt`
  }
  if (amount >= 1_000) {
    return `Rp ${(amount / 1_000).toFixed(0)} Rb`
  }
  return `Rp ${amount}`
}

/**
 * Format tanggal sesuai mode tampilan
 * mode 'daily'   → "12 Jan"
 * mode 'weekly'  → "W1 Jan"
 * mode 'monthly' → "Jan 2024"
 * default        → "12 Jan 2024"
 */
export function formatDate(
  dateStr: string,
  mode?: 'daily' | 'weekly' | 'monthly'
): string {
  const date = new Date(dateStr)

  if (mode === 'monthly') {
    return date.toLocaleDateString('id-ID', { month: 'short', year: 'numeric' })
  }

  if (mode === 'weekly') {
    const weekNum = getWeekNumber(date)
    const month = date.toLocaleDateString('id-ID', { month: 'short' })
    return `W${weekNum} ${month}`
  }

  if (mode === 'daily') {
    return date.toLocaleDateString('id-ID', { day: '2-digit', month: 'short' })
  }

  return date.toLocaleDateString('id-ID', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  })
}

function getWeekNumber(date: Date): number {
  const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()))
  const dayNum = d.getUTCDay() || 7
  d.setUTCDate(d.getUTCDate() + 4 - dayNum)
  const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1))
  return Math.ceil(((d.getTime() - yearStart.getTime()) / 86400000 + 1) / 7)
}
