'use client'
import { useState, useEffect } from 'react'
import { Users, Plus, Pencil, Trash2, X, Check, Loader2, ShieldCheck } from 'lucide-react'
import { apiClient } from '@/lib/api-client'
import { useAuth } from '@/hooks/useAuth'

interface User {
  id: string
  username: string
  role: string
  is_active: boolean
  created_at: string | null
}

const ROLES = [
  { value: 'Administrator', label: 'Administrator', color: 'bg-red-900/30 text-red-400 border-red-900/30' },
  { value: 'Manajer_Kampanye', label: 'Manajer Kampanye', color: 'bg-violet-900/30 text-violet-400 border-violet-900/30' },
  { value: 'Peninjau', label: 'Peninjau', color: 'bg-gray-800 text-gray-400 border-gray-700/30' },
]

function RoleBadge({ role }: { role: string }) {
  const r = ROLES.find(r => r.value === role)
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs ${r?.color ?? 'bg-gray-800 text-gray-400'}`}>
      <ShieldCheck className="h-3 w-3" />
      {r?.label ?? role}
    </span>
  )
}

export default function UsersPage() {
  const { isAdmin } = useAuth()
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [editUser, setEditUser] = useState<User | null>(null)
  const [saving, setSaving] = useState(false)
  const [deleteId, setDeleteId] = useState<string | null>(null)

  // Form state
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState('Manajer_Kampanye')
  const [isActive, setIsActive] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => { loadUsers() }, [])

  async function loadUsers() {
    setLoading(true)
    try {
      const { data } = await apiClient.get('/auth/users')
      setUsers(Array.isArray(data) ? data : [])
    } catch { setUsers([]) }
    finally { setLoading(false) }
  }

  function openCreate() {
    setEditUser(null)
    setUsername(''); setPassword(''); setRole('Manajer_Kampanye'); setIsActive(true); setError('')
    setShowModal(true)
  }

  function openEdit(u: User) {
    setEditUser(u)
    setUsername(u.username); setPassword(''); setRole(u.role); setIsActive(u.is_active); setError('')
    setShowModal(true)
  }

  async function handleSave() {
    if (!editUser && (!username.trim() || !password.trim())) {
      setError('Username dan password wajib diisi'); return
    }
    setSaving(true); setError('')
    try {
      if (editUser) {
        const body: any = { role, is_active: isActive }
        if (password.trim()) body.password = password
        await apiClient.put(`/auth/users/${editUser.id}`, body)
      } else {
        await apiClient.post('/auth/users', { username: username.trim(), password, role })
      }
      setShowModal(false)
      await loadUsers()
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? 'Gagal menyimpan')
    } finally { setSaving(false) }
  }

  async function handleDelete(id: string) {
    try {
      await apiClient.delete(`/auth/users/${id}`)
      await loadUsers()
    } catch (e: any) {
      alert(e?.response?.data?.detail ?? 'Gagal menghapus')
    } finally { setDeleteId(null) }
  }

  if (!isAdmin) {
    return (
      <div className="p-6 text-center">
        <ShieldCheck className="h-12 w-12 text-gray-700 mx-auto mb-3" />
        <p className="text-gray-500">Hanya Administrator yang bisa mengakses halaman ini.</p>
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6 max-w-4xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-white">Manajemen Akun</h1>
          <p className="text-sm text-gray-500 mt-0.5">{users.length} akun terdaftar</p>
        </div>
        <button onClick={openCreate}
          className="flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-700 transition-colors">
          <Plus className="h-4 w-4" /> Buat Akun
        </button>
      </div>

      {loading ? (
        <div className="space-y-2">
          {Array.from({ length: 3 }).map((_, i) => <div key={i} className="h-16 animate-pulse rounded-xl bg-[#111111]" />)}
        </div>
      ) : (
        <div className="rounded-xl border border-[#1f1f1f] overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[#1f1f1f] bg-[#0d0d0d]">
                <th className="px-5 py-3 text-left text-xs font-medium text-gray-500">Username</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-gray-500">Role</th>
                <th className="px-5 py-3 text-center text-xs font-medium text-gray-500">Status</th>
                <th className="px-5 py-3 text-right text-xs font-medium text-gray-500">Dibuat</th>
                <th className="px-5 py-3 text-center text-xs font-medium text-gray-500">Aksi</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u, i) => (
                <tr key={u.id} className={`border-b border-[#1f1f1f] hover:bg-[#0d0d0d] transition-colors ${i % 2 === 0 ? 'bg-[#0a0a0a]' : 'bg-[#111111]'}`}>
                  <td className="px-5 py-3">
                    <div className="flex items-center gap-2">
                      <div className="h-8 w-8 rounded-full bg-violet-600/20 flex items-center justify-center text-xs font-bold text-violet-400">
                        {u.username.charAt(0).toUpperCase()}
                      </div>
                      <span className="text-white font-medium">{u.username}</span>
                    </div>
                  </td>
                  <td className="px-5 py-3"><RoleBadge role={u.role} /></td>
                  <td className="px-5 py-3 text-center">
                    <span className={`rounded-full px-2 py-0.5 text-xs ${u.is_active ? 'bg-green-900/20 text-green-400' : 'bg-gray-800 text-gray-500'}`}>
                      {u.is_active ? 'Aktif' : 'Nonaktif'}
                    </span>
                  </td>
                  <td className="px-5 py-3 text-right text-gray-500 text-xs">
                    {u.created_at ? new Date(u.created_at).toLocaleDateString('id-ID', { day: 'numeric', month: 'short', year: 'numeric' }) : '—'}
                  </td>
                  <td className="px-5 py-3 text-center">
                    <div className="flex items-center justify-center gap-1">
                      <button onClick={() => openEdit(u)}
                        className="rounded-lg p-1.5 text-gray-500 hover:bg-[#1a1a1a] hover:text-white transition-colors">
                        <Pencil className="h-3.5 w-3.5" />
                      </button>
                      {deleteId === u.id ? (
                        <div className="flex items-center gap-1">
                          <button onClick={() => handleDelete(u.id)} className="rounded-lg p-1.5 text-red-400 hover:bg-red-900/20">
                            <Check className="h-3.5 w-3.5" />
                          </button>
                          <button onClick={() => setDeleteId(null)} className="rounded-lg p-1.5 text-gray-500 hover:bg-[#1a1a1a]">
                            <X className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      ) : (
                        <button onClick={() => setDeleteId(u.id)}
                          className="rounded-lg p-1.5 text-gray-500 hover:bg-red-900/20 hover:text-red-400 transition-colors">
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="w-full max-w-md rounded-xl border border-[#1f1f1f] bg-[#111111] p-5 shadow-2xl">
            <div className="flex items-center justify-between mb-4">
              <p className="text-sm font-semibold text-white">
                {editUser ? `Edit Akun — ${editUser.username}` : 'Buat Akun Baru'}
              </p>
              <button onClick={() => setShowModal(false)} className="text-gray-500 hover:text-white">
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="space-y-3">
              {!editUser && (
                <div>
                  <label className="text-xs font-medium text-gray-400 mb-1 block">Username</label>
                  <input value={username} onChange={e => setUsername(e.target.value)}
                    placeholder="cth: budi_manager"
                    className="w-full rounded-lg border border-[#1f1f1f] bg-[#0a0a0a] px-3 py-2 text-sm text-white focus:border-violet-500 focus:outline-none" />
                </div>
              )}

              <div>
                <label className="text-xs font-medium text-gray-400 mb-1 block">
                  Password {editUser && <span className="text-gray-600 font-normal">(kosongkan jika tidak diubah)</span>}
                </label>
                <input type="password" value={password} onChange={e => setPassword(e.target.value)}
                  placeholder={editUser ? 'Password baru (opsional)' : 'Minimal 8 karakter'}
                  className="w-full rounded-lg border border-[#1f1f1f] bg-[#0a0a0a] px-3 py-2 text-sm text-white focus:border-violet-500 focus:outline-none" />
              </div>

              <div>
                <label className="text-xs font-medium text-gray-400 mb-2 block">Role</label>
                <div className="space-y-1.5">
                  {ROLES.map(r => (
                    <button key={r.value} type="button" onClick={() => setRole(r.value)}
                      className={`w-full flex items-center gap-2 rounded-lg border px-3 py-2 text-left text-sm transition-colors ${
                        role === r.value ? 'border-violet-500/60 bg-violet-500/10 text-violet-300' : 'border-[#1f1f1f] text-gray-400 hover:border-[#2f2f2f]'
                      }`}>
                      <ShieldCheck className="h-4 w-4 shrink-0" />
                      <div>
                        <p className="font-medium">{r.label}</p>
                        <p className="text-xs opacity-60">
                          {r.value === 'Administrator' ? 'Akses penuh ke semua fitur' :
                           r.value === 'Manajer_Kampanye' ? 'Kelola template, affiliasi, dan pesan' :
                           'Hanya bisa melihat data'}
                        </p>
                      </div>
                    </button>
                  ))}
                </div>
              </div>

              {editUser && (
                <div className="flex items-center gap-3">
                  <button onClick={() => setIsActive(!isActive)}
                    className={`h-5 w-5 rounded border-2 flex items-center justify-center shrink-0 transition-colors ${
                      isActive ? 'bg-green-600 border-green-600' : 'border-[#3f3f3f]'
                    }`}>
                    {isActive && <Check className="h-3 w-3 text-white" />}
                  </button>
                  <span className="text-sm text-gray-300">Akun aktif</span>
                </div>
              )}

              {error && <p className="text-xs text-red-400">{error}</p>}

              <button onClick={handleSave} disabled={saving}
                className="w-full rounded-lg bg-violet-600 py-2.5 text-sm font-medium text-white hover:bg-violet-700 disabled:opacity-40 flex items-center justify-center gap-2">
                {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                {saving ? 'Menyimpan...' : editUser ? 'Simpan Perubahan' : 'Buat Akun'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
