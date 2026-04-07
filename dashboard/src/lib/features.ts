/**
 * Feature flags — kontrol fitur yang ditampilkan di UI.
 * Set NEXT_PUBLIC_HIDE_WHATSAPP=true di .env.local untuk menyembunyikan fitur WA.
 */
export const features = {
  showWhatsApp: process.env.NEXT_PUBLIC_HIDE_WHATSAPP !== 'true',
}
