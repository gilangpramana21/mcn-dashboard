'use client'
import { useState, useRef } from 'react'
import { Upload, FileText, CheckCircle, AlertCircle, X, Download, MessageCircle, Phone, Loader2 } from 'lucide-react'
import { apiClient } from '@/lib/api-client'
import { features } from '@/lib/features'

interface ParsedRow {
  name: string
  tiktok_username: string
  follower_count: number
  engagement_rate: number
  content_categories: string[]
  location: string
  phone_number: string
  _valid: boolean
  _error?: string
}

interface ImportResult {
  imported: number
  skipped: number
  errors: string[]
  auto_sent_tiktok: number
}

// Kolom CSV yang dikenali
const COLUMN_ALIASES: Record<string, string> = {
  'nama': 'name', 'name': 'name', 'creator name': 'name', 'creator': 'name',
  'username': 'tiktok_username', 'tiktok': 'tiktok_username', 'tiktok username': 'tiktok_username',
  'followers': 'follower_count', 'follower': 'follower_count', 'jumlah followers': 'follower_count',
  'engagement': 'engagement_rate', 'engagement rate': 'engagement_rate', 'er': 'engagement_rate',
  'kategori': 'content_categories', 'category': 'content_categories', 'categories': 'content_categories',
  'lokasi': 'location', 'location': 'location', 'kota': 'location',
  'whatsapp': 'phone_number', 'nomor wa': 'phone_number', 'phone': 'phone_number', 'no wa': 'phone_number',
}

function parseCSV(text: string): ParsedRow[] {
  const lines = text.trim().split('\n').filter(l => l.trim())
  if (lines.length < 2) return []

  const headers = lines[0].split(',').map(h => h.trim().toLowerCase().replace(/['"]/g, ''))
  const mappedHeaders = headers.map(h => COLUMN_ALIASES[h] || h)

  return lines.slice(1).map(line => {
    const values = line.split(',').map(v => v.trim().replace(/^["']|["']$/g, ''))
    const row: any = {}
    mappedHeaders.forEach((key, i) => {
      row[key] = values[i] ?? ''
    })

    const followerRaw = row.follower_count || '0'
    const followers = parseInt(followerRaw.replace(/[^0-9]/g, '')) || 0

    const engRaw = row.engagement_rate || '0'
    const engagement = parseFloat(engRaw.replace('%', '').replace(',', '.')) || 0
    const engNormalized = engagement > 1 ? engagement / 100 : engagement

    const cats = row.content_categories
      ? row.content_categories.split(';').map((c: string) => c.trim()).filter(Boolean)
      : []

    const valid = !!row.name?.trim()

    return {
      name: row.name?.trim() || '',
      tiktok_username: row.tiktok_username?.trim() || '',
      follower_count: followers,
      engagement_rate: engNormalized,
      content_categories: cats,
      location: row.location?.trim() || '',
      phone_number: row.phone_number?.trim() || '',
      _valid: valid,
      _error: valid ? undefined : 'Nama wajib diisi',
    } as ParsedRow
  })
}

function formatFollowers(n: number) {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`
  return String(n)
}

export default function ImportPage() {
  const [rows, setRows] = useState<ParsedRow[]>([])
  const [fileName, setFileName] = useState('')
  const [autoSend, setAutoSend] = useState(true)
  const [importing, setImporting] = useState(false)
  const [result, setResult] = useState<ImportResult | null>(null)
  const [dragOver, setDragOver] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)

  function handleFile(file: File) {
    if (!file) return
    setFileName(file.name)
    setResult(null)
    const reader = new FileReader()
    reader.onload = e => {
      const text = e.target?.result as string
      const parsed = parseCSV(text)
      setRows(parsed)
    }
    reader.readAsText(file)
  }

  async function handleImport() {
    const validRows = rows.filter(r => r._valid)
    if (validRows.length === 0) return
    setImporting(true)
    try {
      const payload = validRows.map(r => ({
        name: r.name,
        tiktok_username: r.tiktok_username || null,
        follower_count: r.follower_count,
        engagement_rate: r.engagement_rate,
        content_categories: r.content_categories,
        location: r.location,
        phone_number: r.phone_number || null,
      }))
      const { data } = await apiClient.post(
        `/affiliates/import?auto_send_tiktok=${autoSend}`,
        payload
      )
      setResult(data)
    } catch (e: any) {
      setResult({ imported: 0, skipped: 0, errors: [e?.response?.data?.detail ?? 'Gagal import'], auto_sent_tiktok: 0 })
    } finally {
      setImporting(false)
    }
  }

  function downloadTemplate() {
    const csv = [
      'nama,tiktok_username,followers,engagement_rate,kategori,lokasi,whatsapp',
      'Sari Cantika,@saricantika,125000,4.5%,Skincare;Kecantikan & Perawatan,Jakarta,',
      'Budi Santoso,@budisantoso,89000,3.2%,Makanan & Minuman,Surabaya,+6281234567890',
      'Dewi Fashion,@dewifashion,210000,5.1%,Fashion Wanita,Bandung,',
    ].join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = 'template-import-affiliator.csv'; a.click()
    URL.revokeObjectURL(url)
  }

  const validCount = rows.filter(r => r._valid).length
  const withWA = rows.filter(r => r._valid && r.phone_number).length
  const withoutWA = validCount - withWA

  return (
    <div className="p-6 space-y-6 max-w-5xl">
      <div>
        <h1 className="text-xl font-semibold text-white">Import Data Affiliator</h1>
        <p className="text-sm text-gray-500 mt-0.5">
          Upload CSV dari TikTok Seller Center. Sistem otomatis kirim pesan TikTok chat ke affiliator setelah import.
        </p>
      </div>

      {/* Alur kerja */}
      <div className={`grid gap-3 ${features.showWhatsApp ? 'grid-cols-4' : 'grid-cols-2'}`}>
        {(features.showWhatsApp ? [
          { step: '1', label: 'Export dari Seller Center', desc: 'Download data affiliator sebagai CSV', icon: '📥' },
          { step: '2', label: 'Upload CSV', desc: 'Import ke sistem ini', icon: '📤' },
          { step: '3', label: 'Auto TikTok Chat', desc: 'Sistem kirim pesan minta nomor WA', icon: '💬' },
          { step: '4', label: 'Auto WhatsApp', desc: 'Setelah nomor WA diisi, langsung kirim undangan', icon: '📱' },
        ] : [
          { step: '1', label: 'Export dari Seller Center', desc: 'Download data affiliator sebagai CSV', icon: '📥' },
          { step: '2', label: 'Upload CSV', desc: 'Import ke sistem ini', icon: '📤' },
        ]).map(s => (
          <div key={s.step} className="rounded-xl border border-[#1f1f1f] bg-[#111111] p-4">
            <div className="flex items-center gap-2 mb-2">
              <span className="h-5 w-5 rounded-full bg-violet-600/20 text-violet-400 text-xs flex items-center justify-center font-bold">{s.step}</span>
              <span className="text-lg">{s.icon}</span>
            </div>
            <p className="text-xs font-medium text-white">{s.label}</p>
            <p className="text-xs text-gray-600 mt-0.5">{s.desc}</p>
          </div>
        ))}
      </div>

      {/* Upload area */}
      {!result && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-gray-300">Upload File CSV</p>
            <button onClick={downloadTemplate}
              className="flex items-center gap-1.5 text-xs text-violet-400 hover:text-violet-300">
              <Download className="h-3.5 w-3.5" /> Download Template CSV
            </button>
          </div>

          <div
            onDragOver={e => { e.preventDefault(); setDragOver(true) }}
            onDragLeave={() => setDragOver(false)}
            onDrop={e => { e.preventDefault(); setDragOver(false); const f = e.dataTransfer.files[0]; if (f) handleFile(f) }}
            onClick={() => fileRef.current?.click()}
            className={`rounded-xl border-2 border-dashed p-10 text-center cursor-pointer transition-colors ${
              dragOver ? 'border-violet-500 bg-violet-500/5' : 'border-[#2f2f2f] hover:border-violet-500/50'
            }`}>
            <Upload className="h-8 w-8 text-gray-600 mx-auto mb-3" />
            <p className="text-sm text-gray-400">Drag & drop file CSV di sini, atau klik untuk pilih</p>
            <p className="text-xs text-gray-600 mt-1">Format: .csv (export dari TikTok Seller Center)</p>
            <input ref={fileRef} type="file" accept=".csv,.txt" className="hidden"
              onChange={e => { const f = e.target.files?.[0]; if (f) handleFile(f) }} />
          </div>

          {fileName && rows.length > 0 && (
            <>
              {/* Summary */}
              <div className="flex items-center gap-4 rounded-xl border border-[#1f1f1f] bg-[#111111] p-4">
                <FileText className="h-8 w-8 text-violet-400 shrink-0" />
                <div className="flex-1">
                  <p className="text-sm font-medium text-white">{fileName}</p>
                  <p className="text-xs text-gray-500 mt-0.5">{validCount} affiliator valid{features.showWhatsApp ? ` · ${withWA} sudah punya WA · ${withoutWA} belum punya WA` : ''}</p>
                </div>
                <button onClick={() => { setRows([]); setFileName('') }} className="text-gray-500 hover:text-white">
                  <X className="h-4 w-4" />
                </button>
              </div>

              {/* Auto-send option */}
              {features.showWhatsApp && (
              <div className="rounded-xl border border-[#1f1f1f] bg-[#111111] p-4">
                <div className="flex items-start gap-3">
                  <button onClick={() => setAutoSend(!autoSend)}
                    className={`mt-0.5 h-5 w-5 rounded border-2 flex items-center justify-center shrink-0 transition-colors ${
                      autoSend ? 'bg-violet-600 border-violet-600' : 'border-[#3f3f3f]'
                    }`}>
                    {autoSend && <CheckCircle className="h-3 w-3 text-white" />}
                  </button>
                  <div>
                    <p className="text-sm font-medium text-white">Auto-kirim pesan TikTok Chat</p>
                    <p className="text-xs text-gray-500 mt-0.5">
                      Untuk {withoutWA} affiliator yang belum punya nomor WA, sistem otomatis kirim pesan via TikTok chat untuk meminta nomor WhatsApp mereka.
                    </p>
                    {withWA > 0 && (
                      <p className="text-xs text-green-400 mt-1">
                        {withWA} affiliator sudah punya nomor WA — akan langsung dikirim undangan WhatsApp setelah import.
                      </p>
                    )}
                  </div>
                </div>
              </div>
              )}

              {/* Preview table */}
              <div className="rounded-xl border border-[#1f1f1f] overflow-hidden">
                <div className="px-4 py-3 border-b border-[#1f1f1f] bg-[#0d0d0d] flex items-center justify-between">
                  <p className="text-xs font-medium text-gray-400">Preview Data ({rows.length} baris)</p>
                </div>
                <div className="overflow-x-auto max-h-64 overflow-y-auto">
                  <table className="w-full text-xs">
                    <thead className="sticky top-0 bg-[#0d0d0d]">
                      <tr className="border-b border-[#1f1f1f]">
                        <th className="px-3 py-2 text-left text-gray-500">Nama</th>
                        <th className="px-3 py-2 text-left text-gray-500">TikTok</th>
                        <th className="px-3 py-2 text-right text-gray-500">Followers</th>
                        <th className="px-3 py-2 text-left text-gray-500">Kategori</th>
                        <th className="px-3 py-2 text-left text-gray-500">Lokasi</th>
                        {features.showWhatsApp && <th className="px-3 py-2 text-center text-gray-500">WA</th>}
                        <th className="px-3 py-2 text-center text-gray-500">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {rows.map((row, i) => (
                        <tr key={i} className={`border-b border-[#1f1f1f] ${row._valid ? '' : 'opacity-50'}`}>
                          <td className="px-3 py-2 text-white font-medium">{row.name || '—'}</td>
                          <td className="px-3 py-2 text-gray-400">{row.tiktok_username || '—'}</td>
                          <td className="px-3 py-2 text-right text-gray-300">{formatFollowers(row.follower_count)}</td>
                          <td className="px-3 py-2 text-gray-400">{row.content_categories.slice(0, 1).join(', ') || '—'}</td>
                          <td className="px-3 py-2 text-gray-400">{row.location || '—'}</td>
                          {features.showWhatsApp && (
                          <td className="px-3 py-2 text-center">
                            {row.phone_number ? (
                              <span className="text-green-400">✓</span>
                            ) : (
                              <span className="text-gray-600">—</span>
                            )}
                          </td>
                          )}
                          <td className="px-3 py-2 text-center">
                            {row._valid ? (
                              <span className="text-green-400">✓</span>
                            ) : (
                              <span className="text-red-400" title={row._error}>✗</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              <button onClick={handleImport} disabled={importing || validCount === 0}
                className="w-full rounded-lg bg-violet-600 py-3 text-sm font-medium text-white hover:bg-violet-700 disabled:opacity-40 flex items-center justify-center gap-2">
                {importing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
                {importing ? 'Mengimport...' : `Import ${validCount} Affiliator`}
              </button>
            </>
          )}
        </div>
      )}

      {/* Result */}
      {result && (
        <div className="space-y-4">
          <div className="grid grid-cols-4 gap-4">
            <div className="rounded-xl border border-green-900/30 bg-green-900/10 p-4 text-center">
              <CheckCircle className="h-6 w-6 text-green-400 mx-auto mb-1" />
              <p className="text-2xl font-bold text-green-400">{result.imported}</p>
              <p className="text-xs text-gray-500">Berhasil diimport</p>
            </div>
            <div className="rounded-xl border border-[#1f1f1f] bg-[#111111] p-4 text-center">
              <p className="text-2xl font-bold text-gray-400">{result.skipped}</p>
              <p className="text-xs text-gray-500">Dilewati (sudah ada)</p>
            </div>
            <div className="rounded-xl border border-blue-900/30 bg-blue-900/10 p-4 text-center">
              <MessageCircle className="h-6 w-6 text-blue-400 mx-auto mb-1" />
              <p className="text-2xl font-bold text-blue-400">{result.auto_sent_tiktok}</p>
              <p className="text-xs text-gray-500">Pesan TikTok terkirim</p>
            </div>
            <div className="rounded-xl border border-red-900/30 bg-red-900/10 p-4 text-center">
              <AlertCircle className="h-6 w-6 text-red-400 mx-auto mb-1" />
              <p className="text-2xl font-bold text-red-400">{result.errors.length}</p>
              <p className="text-xs text-gray-500">Error</p>
            </div>
          </div>

          {result.errors.length > 0 && (
            <div className="rounded-xl border border-red-900/30 bg-red-900/10 p-4">
              <p className="text-xs font-medium text-red-400 mb-2">Error detail:</p>
              {result.errors.map((e, i) => (
                <p key={i} className="text-xs text-red-300">{e}</p>
              ))}
            </div>
          )}

          <p className="text-sm text-gray-400">
            Import selesai. Pesan TikTok chat sudah tercatat di History Pesan. Setelah mendapat nomor WA dari affiliator, update di halaman Cari Affiliasi.
          </p>

          <div className="flex gap-3">
            <button onClick={() => { setResult(null); setRows([]); setFileName('') }}
              className="rounded-lg bg-violet-600 px-5 py-2 text-sm text-white hover:bg-violet-700">
              Import Lagi
            </button>
            <a href="/affiliates"
              className="rounded-lg border border-[#1f1f1f] px-5 py-2 text-sm text-gray-400 hover:text-white">
              Lihat Data Affiliator
            </a>
          </div>
        </div>
      )}
    </div>
  )
}
