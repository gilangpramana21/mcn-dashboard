import { ArrowUpDown, ArrowUp, ShoppingBag } from 'lucide-react'
import { formatCurrency } from '@/lib/formatters'

interface ProductItem {
  id: string
  name: string
  category: string
  price: number
  total_creators: number
  total_views: number
  total_gmv: number
  conversion_rate: number
  total_buyers: number
  shop_name: string
}

interface ProductTableProps {
  data: ProductItem[]
  sortBy: string
  onSort: (field: string) => void
  isLoading?: boolean
}

export function ProductTable({ data, sortBy, onSort, isLoading }: ProductTableProps) {
  const SortIcon = ({ field }: { field: string }) => {
    if (sortBy !== field) return <ArrowUpDown className="h-3.5 w-3.5 text-gray-600" />
    return <ArrowUp className="h-3.5 w-3.5 text-violet-400" />
  }

  if (isLoading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 10 }).map((_, i) => (
          <div key={i} className="h-14 animate-pulse rounded-lg bg-[#1a1a1a]" />
        ))}
      </div>
    )
  }

  if (data.length === 0) {
    return (
      <div className="rounded-xl border border-[#1f1f1f] bg-[#111111] p-12 text-center">
        <ShoppingBag className="h-12 w-12 text-gray-700 mx-auto mb-3" />
        <p className="text-gray-500">Belum ada data produk</p>
      </div>
    )
  }

  return (
    <div className="rounded-xl border border-[#1f1f1f] bg-[#111111] overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-[#1f1f1f] bg-[#0d0d0d]">
            <th className="px-5 py-3 text-left text-xs font-medium text-gray-500">Produk</th>
            <th className="px-5 py-3 text-left text-xs font-medium text-gray-500">Kategori</th>
            <th className="px-5 py-3 text-right text-xs font-medium text-gray-500">Harga</th>
            <th onClick={() => onSort('creators')} className="px-5 py-3 text-right text-xs font-medium text-gray-500 cursor-pointer hover:text-gray-300">
              <div className="flex items-center justify-end gap-1.5">Kreator <SortIcon field="creators" /></div>
            </th>
            <th onClick={() => onSort('views')} className="px-5 py-3 text-right text-xs font-medium text-gray-500 cursor-pointer hover:text-gray-300">
              <div className="flex items-center justify-end gap-1.5">Views <SortIcon field="views" /></div>
            </th>
            <th onClick={() => onSort('gmv')} className="px-5 py-3 text-right text-xs font-medium text-gray-500 cursor-pointer hover:text-gray-300">
              <div className="flex items-center justify-end gap-1.5">GMV <SortIcon field="gmv" /></div>
            </th>
            <th onClick={() => onSort('conversion')} className="px-5 py-3 text-right text-xs font-medium text-gray-500 cursor-pointer hover:text-gray-300">
              <div className="flex items-center justify-end gap-1.5">Conversion <SortIcon field="conversion" /></div>
            </th>
            <th className="px-5 py-3 text-right text-xs font-medium text-gray-500">Buyers</th>
          </tr>
        </thead>
        <tbody>
          {data.map((product, i) => (
            <tr key={product.id} className={`border-b border-[#1f1f1f] hover:bg-[#0d0d0d] transition-colors ${i % 2 === 0 ? 'bg-[#0a0a0a]' : 'bg-[#111111]'}`}>
              <td className="px-5 py-3">
                <div className="flex items-center gap-2">
                  <div className="h-7 w-7 rounded-lg bg-violet-600/20 flex items-center justify-center shrink-0">
                    <ShoppingBag className="h-3.5 w-3.5 text-violet-400" />
                  </div>
                  <span className="text-white font-medium">{product.name}</span>
                </div>
              </td>
              <td className="px-5 py-3">
                <span className="inline-flex items-center rounded-full bg-blue-600/20 border border-blue-600/30 px-2 py-0.5 text-xs text-blue-400">
                  {product.category}
                </span>
              </td>
              <td className="px-5 py-3 text-right text-gray-300 font-medium">
                {formatCurrency(product.price)}
              </td>
              <td className="px-5 py-3 text-right text-gray-400">{product.total_creators}</td>
              <td className="px-5 py-3 text-right text-violet-400 font-medium">
                {(() => { const v = product.total_views || 0; return v >= 1_000_000 ? `${(v/1_000_000).toFixed(1)}M` : `${(v/1_000).toFixed(0)}K` })()}
              </td>
              <td className="px-5 py-3 text-right text-yellow-400 font-semibold">
                {formatCurrency(product.total_gmv)}
              </td>
              <td className="px-5 py-3 text-right text-green-400">
                {product.conversion_rate?.toFixed(2) ?? '0.00'}%
              </td>
              <td className="px-5 py-3 text-right text-blue-400">{product.total_buyers?.toLocaleString('id-ID') ?? '0'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
