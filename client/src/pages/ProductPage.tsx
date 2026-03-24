import { useState, useEffect } from 'react'
import axios from 'axios'

function LoadingImage({ src, alt, style }: { src: string; alt?: string; style?: React.CSSProperties }) {
  const [loaded, setLoaded] = useState(false)
  const [error, setError] = useState(false)
  if (error) return <span style={{ fontSize: style?.maxHeight && Number(style.maxHeight) > 80 ? 72 : 28 }}>🥫</span>
  return (
    <>
      {!loaded && (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: '100%', height: '100%' }}>
          <div style={{
            width: 32, height: 32, border: '3px solid #e8e4dc', borderTop: '3px solid #c1440e',
            borderRadius: '50%', animation: 'spin 0.8s linear infinite'
          }} />
        </div>
      )}
      <img
        src={src} alt={alt || ''}
        style={{ ...style, display: loaded ? 'block' : 'none' }}
        onLoad={() => setLoaded(true)}
        onError={() => setError(true)}
      />
    </>
  )
}

interface Nutrition {
  energy_kcal: number | null
  fat: number | null
  saturated_fat: number | null
  carbohydrates: number | null
  sugars: number | null
  fiber: number | null
  proteins: number | null
  salt: number | null
  sodium: number | null
}

interface Product {
  code: string
  product_name: string
  product_name_en: string | null
  product_name_fr: string | null
  brands: string | null
  primary_country: string | null
  image_url: string | null
  nutriscore_grade: string | null
  nutriscore_score: number | null
  nova_group: number | null
  ecoscore_grade: string | null
  categories_tags: string | null
  labels_tags: string | null
  allergens_tags: string | null
  ingredients_text: string | null
  nutrition: Nutrition
  product_quantity: string | null
  serving_size: string | null
  link: string | null
  popularity_key: number | null
  unique_scans_n: number | null
}

const NUTRI_COLORS: Record<string, string> = {
  a: '#1a7a3a', b: '#5aaa3a', c: '#f5c400', d: '#e07c2a', e: '#c1440e'
}

const NUTRI_LABELS: Record<string, string> = {
  a: 'Excellent', b: 'Good', c: 'Average', d: 'Poor', e: 'Bad'
}

const NOVA_COLORS: Record<number, string> = {
  1: '#1a7a3a', 2: '#5aaa3a', 3: '#e07c2a', 4: '#c1440e'
}

const NOVA_LABELS: Record<number, string> = {
  1: 'Unprocessed / minimally processed',
  2: 'Processed culinary ingredients',
  3: 'Processed foods',
  4: 'Ultra-processed products'
}

function parseTags(tags: string | null): string[] {
  if (!tags) return []
  try {
    return tags.replace(/[['\]]/g, '').split(',').map(t => {
      const clean = t.trim()
      return clean.includes(':') ? clean.split(':').slice(1).join(':') : clean
    }).filter(Boolean)
  } catch {
    return []
  }
}

export default function ProductPage({
  code,
  onBack,
  onProductClick
}: {
  code: string
  onBack: () => void
  onProductClick: (code: string) => void
}) {
  const [product, setProduct] = useState<Product | null>(null)
  const [similar, setSimilar] = useState<Product[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    const fetchProduct = async () => {
      setLoading(true)
      try {
        const res = await axios.get(`http://localhost:8000/api/product/${code}`)
        setProduct(res.data)
        try {
          const simRes = await axios.get(`http://localhost:8000/api/product/${code}/similar?limit=6`)
          setSimilar(simRes.data.results || [])
        } catch { /* ignore */ }
      } catch {
        setError('Product not found')
      }
      setLoading(false)
    }
    fetchProduct()
  }, [code])

  if (loading) return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      height: '60vh', fontFamily: 'DM Sans, sans-serif', color: '#8a8478'
    }}>
      Loading product…
    </div>
  )

  if (error || !product) return (
    <div style={{
      display: 'flex', flexDirection: 'column' as const, alignItems: 'center',
      justifyContent: 'center', height: '60vh', fontFamily: 'DM Sans, sans-serif'
    }}>
      <div style={{ fontSize: 48, marginBottom: 12 }}>😕</div>
      <div style={{ color: '#c1440e', marginBottom: 16 }}>{error || 'Product not found'}</div>
      <button onClick={onBack} style={{
        background: '#2d6a4f', color: 'white', border: 'none',
        borderRadius: 10, padding: '8px 20px', cursor: 'pointer',
        fontFamily: 'DM Sans, sans-serif'
      }}>
        ← Back to search
      </button>
    </div>
  )

  const labels = parseTags(product.labels_tags)
  const allergens = parseTags(product.allergens_tags)
  const categories = parseTags(product.categories_tags)
  const n = product.nutrition

  return (
    <div style={{ maxWidth: 960, margin: '0 auto', padding: '32px 24px', fontFamily: 'DM Sans, sans-serif' }}>

      <button onClick={onBack} style={{
        background: 'white', border: '1.5px solid #e8e4dc',
        borderRadius: 10, padding: '8px 16px', fontSize: 13,
        color: '#8a8478', cursor: 'pointer', marginBottom: 24,
        fontFamily: 'DM Sans, sans-serif',
        display: 'flex', alignItems: 'center', gap: 6
      }}>
        ← Back to search
      </button>

      <div style={{ display: 'grid', gridTemplateColumns: '300px 1fr', gap: 32 }}>

        <div>
          <div style={{
            background: 'white', border: '1.5px solid #e8e4dc',
            borderRadius: 16, padding: 24,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            marginBottom: 16, minHeight: 200
          }}>
            {product.image_url
              ? <LoadingImage src={product.image_url} alt={product.product_name}
                  style={{ maxWidth: '100%', maxHeight: 200, objectFit: 'contain' }} />
              : <span style={{ fontSize: 72 }}>🥫</span>}
          </div>

          <div style={{ display: 'flex', gap: 10, marginBottom: 16 }}>
            {product.nutriscore_grade && product.nutriscore_grade !== 'unknown' && (
              <div style={{
                flex: 1, background: NUTRI_COLORS[product.nutriscore_grade] || '#aaa',
                borderRadius: 14, padding: '14px 16px', color: 'white'
              }}>
                <div style={{ fontSize: 10, opacity: 0.85, marginBottom: 2 }}>NUTRI-SCORE</div>
                <div style={{ fontSize: 32, fontWeight: 700, fontFamily: 'Fraunces, serif' }}>
                  {product.nutriscore_grade.toUpperCase()}
                </div>
                <div style={{ fontSize: 11, opacity: 0.9 }}>
                  {NUTRI_LABELS[product.nutriscore_grade]}
                  {product.nutriscore_score != null && ` (${product.nutriscore_score})`}
                </div>
              </div>
            )}
            {product.nova_group != null && (
              <div style={{
                flex: 1, background: NOVA_COLORS[product.nova_group] || '#aaa',
                borderRadius: 14, padding: '14px 16px', color: 'white'
              }}>
                <div style={{ fontSize: 10, opacity: 0.85, marginBottom: 2 }}>NOVA GROUP</div>
                <div style={{ fontSize: 32, fontWeight: 700, fontFamily: 'Fraunces, serif' }}>
                  {product.nova_group}
                </div>
                <div style={{ fontSize: 11, opacity: 0.9 }}>
                  {NOVA_LABELS[product.nova_group]}
                </div>
              </div>
            )}
          </div>

          {product.ecoscore_grade && product.ecoscore_grade !== 'unknown' && (
            <div style={{
              background: '#f7f5f0', border: '1.5px solid #e8e4dc',
              borderRadius: 14, padding: '12px 16px', marginBottom: 16,
              display: 'flex', alignItems: 'center', gap: 10
            }}>
              <span style={{ fontSize: 24 }}>🌍</span>
              <div>
                <div style={{ fontSize: 10, color: '#8a8478' }}>ECO-SCORE</div>
                <div style={{ fontSize: 20, fontWeight: 700 }}>
                  {product.ecoscore_grade.toUpperCase()}
                </div>
              </div>
            </div>
          )}

          {labels.length > 0 && (
            <div style={{
              background: 'white', border: '1.5px solid #e8e4dc',
              borderRadius: 14, padding: '14px 16px', marginBottom: 16
            }}>
              <div style={{ fontSize: 11, color: '#8a8478', marginBottom: 8, fontWeight: 600 }}>LABELS</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {labels.map((label, i) => (
                  <span key={i} style={{
                    background: '#e8f4ee', color: '#2d6a4f',
                    fontSize: 11, padding: '3px 10px',
                    borderRadius: 20, fontWeight: 500
                  }}>
                    {label}
                  </span>
                ))}
              </div>
            </div>
          )}

          {allergens.length > 0 && allergens[0] !== 'none' && (
            <div style={{
              background: '#fef8f0', border: '1.5px solid #f5deb3',
              borderRadius: 14, padding: '14px 16px'
            }}>
              <div style={{ fontSize: 11, color: '#c1440e', marginBottom: 8, fontWeight: 600 }}>⚠️ ALLERGENS</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {allergens.filter(a => a !== 'none').map((a, i) => (
                  <span key={i} style={{
                    background: '#fde8d0', color: '#c1440e',
                    fontSize: 11, padding: '3px 10px',
                    borderRadius: 20, fontWeight: 500
                  }}>
                    {a}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        <div>
          <h1 style={{
            fontFamily: 'Fraunces, serif', fontSize: 26, fontWeight: 700,
            color: '#1a1814', margin: '0 0 4px 0'
          }}>
            {product.product_name || 'Unknown Product'}
          </h1>
          {product.product_name_fr && product.product_name_fr !== product.product_name && (
            <div style={{ fontSize: 14, color: '#8a8478', marginBottom: 4, fontStyle: 'italic' }}>
              {product.product_name_fr}
            </div>
          )}
          <div style={{ fontSize: 15, color: '#8a8478', marginBottom: 4 }}>
            {product.brands}
          </div>
          <div style={{ fontSize: 13, color: '#b0a898', marginBottom: 16, display: 'flex', gap: 12, flexWrap: 'wrap' }}>
            {product.primary_country && <span>📍 {product.primary_country}</span>}
            {product.product_quantity && <span>📦 {product.product_quantity}</span>}
            {product.serving_size && <span>🍽️ Serving: {product.serving_size}</span>}
            <span style={{ fontFamily: 'monospace', fontSize: 11, color: '#ccc' }}>#{product.code}</span>
          </div>

          {categories.length > 0 && (
            <div style={{ marginBottom: 20, display: 'flex', gap: 6, flexWrap: 'wrap' }}>
              {categories.slice(0, 5).map((c, i) => (
                <span key={i} style={{
                  background: '#f7f5f0', color: '#8a8478',
                  fontSize: 11, padding: '3px 10px',
                  borderRadius: 20, border: '1px solid #e8e4dc'
                }}>
                  {c}
                </span>
              ))}
            </div>
          )}

          <div style={{
            background: 'white', border: '1.5px solid #e8e4dc',
            borderRadius: 16, padding: '20px 24px', marginBottom: 20
          }}>
            <div style={{
              fontSize: 12, fontWeight: 600, color: '#8a8478',
              marginBottom: 14, textTransform: 'uppercase', letterSpacing: 1
            }}>
              Nutrition per 100g
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10 }}>
              {[
                { label: 'Energy', value: n?.energy_kcal, unit: 'kcal', icon: '🔥' },
                { label: 'Fat', value: n?.fat, unit: 'g', icon: '🧈' },
                { label: 'Sat. Fat', value: n?.saturated_fat, unit: 'g', icon: '' },
                { label: 'Carbs', value: n?.carbohydrates, unit: 'g', icon: '🍞' },
                { label: 'Sugars', value: n?.sugars, unit: 'g', icon: '🍬' },
                { label: 'Fiber', value: n?.fiber, unit: 'g', icon: '🌾' },
                { label: 'Proteins', value: n?.proteins, unit: 'g', icon: '💪' },
                { label: 'Salt', value: n?.salt, unit: 'g', icon: '🧂' },
                { label: 'Sodium', value: n?.sodium, unit: 'g', icon: '' },
              ].map((item, i) => (
                <div key={i} style={{
                  background: '#f7f5f0', borderRadius: 10, padding: '10px 12px'
                }}>
                  <div style={{ fontSize: 11, color: '#8a8478', marginBottom: 3 }}>
                    {item.icon} {item.label}
                  </div>
                  <div style={{ fontSize: 17, fontWeight: 600, color: '#1a1814' }}>
                    {item.value != null ? `${Number(item.value).toFixed(item.unit === 'kcal' ? 0 : 2)} ${item.unit}` : '—'}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {product.ingredients_text && (
            <div style={{
              background: 'white', border: '1.5px solid #e8e4dc',
              borderRadius: 16, padding: '20px 24px', marginBottom: 20
            }}>
                <div style={{
                  fontSize: 12, fontWeight: 600, color: '#8a8478',
                  marginBottom: 10, textTransform: 'uppercase', letterSpacing: 1
                }}>
                  Ingredients
                </div>
                <p style={{ fontSize: 13, color: '#1a1814', lineHeight: 1.7, margin: 0 }}>
                  {product.ingredients_text}
                </p>
                {dietProfile && (
                  <div style={{
                    background: '#e8f4ee', border: '1.5px solid #b7dfc8',
                    borderRadius: 14, padding: '14px 16px', marginBottom: 16
                  }}>
                    <div style={{ fontSize: 13, color: '#2d6a4f', fontWeight: 600, marginBottom: 6 }}>
                      Diet Profile & Usage
                    </div>
                    {dietProfile.compare && <div style={{ fontSize: 14, marginBottom: 6 }}>{dietProfile.compare}</div>}
                    {dietProfile.usage && dietProfile.usage.length > 0 && (
                      <ul style={{ margin: 0, paddingLeft: 18, color: '#1a1814', fontSize: 13 }}>
                        {dietProfile.usage.map((u: string, i: number) => <li key={i}>{u}</li>)}
                      </ul>
                    )}
                  </div>
                )}
            </div>
          )}

          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            <a
              href={`https://world.openfoodfacts.org/product/${product.code}`}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                display: 'inline-flex', alignItems: 'center', gap: 6,
                background: '#2d6a4f', color: 'white',
                padding: '10px 20px', borderRadius: 12,
                fontSize: 13, fontWeight: 500, textDecoration: 'none'
              }}
            >
              View on Open Food Facts →
            </a>
            {product.link && (
              <a
                href={product.link}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  display: 'inline-flex', alignItems: 'center', gap: 6,
                  background: 'white', color: '#2d6a4f',
                  border: '1.5px solid #2d6a4f',
                  padding: '10px 20px', borderRadius: 12,
                  fontSize: 13, fontWeight: 500, textDecoration: 'none'
                }}
              >
                Product Website →
              </a>
            )}
          </div>
        </div>
      </div>

      {similar.length > 0 && (
        <div style={{ marginTop: 40 }}>
          <h2 style={{
            fontFamily: 'Fraunces, serif', fontSize: 20,
            fontWeight: 700, color: '#1a1814', marginBottom: 16
          }}>
            Similar Products
          </h2>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
            gap: 14
          }}>
            {similar.map((p, i) => (
              <div key={i} onClick={() => onProductClick(p.code)} style={{
                background: 'white', border: '1.5px solid #e8e4dc',
                borderRadius: 14, padding: 14, cursor: 'pointer',
                transition: 'box-shadow 0.2s, transform 0.2s',
                boxShadow: '0 1px 4px rgba(0,0,0,0.04)'
              }}
                onMouseEnter={e => { e.currentTarget.style.boxShadow = '0 4px 16px rgba(0,0,0,0.1)'; e.currentTarget.style.transform = 'translateY(-2px)' }}
                onMouseLeave={e => { e.currentTarget.style.boxShadow = '0 1px 4px rgba(0,0,0,0.04)'; e.currentTarget.style.transform = 'translateY(0)' }}
              >
                <div style={{
                  height: 80, display: 'flex', alignItems: 'center',
                  justifyContent: 'center', background: '#f7f5f0',
                  borderRadius: 8, marginBottom: 10
                }}>
                  {p.image_url
                    ? <LoadingImage src={p.image_url} style={{ maxHeight: 60, maxWidth: '100%', objectFit: 'contain' }} />
                    : <span style={{ fontSize: 28 }}>🥫</span>}
                </div>
                <div style={{ fontWeight: 600, fontSize: 12, marginBottom: 2, lineHeight: 1.3 }}>
                  {p.product_name || 'Unknown'}
                </div>
                <div style={{ fontSize: 11, color: '#8a8478', marginBottom: 6 }}>{p.brands}</div>
                <div style={{ display: 'flex', gap: 4 }}>
                  {p.nutriscore_grade && p.nutriscore_grade !== 'unknown' && (
                    <span style={{
                      background: NUTRI_COLORS[p.nutriscore_grade] || '#aaa',
                      color: 'white', fontSize: 9, fontWeight: 700,
                      padding: '1px 6px', borderRadius: 4
                    }}>
                      {p.nutriscore_grade.toUpperCase()}
                    </span>
                  )}
                  {p.nova_group != null && (
                    <span style={{
                      background: NOVA_COLORS[p.nova_group] || '#aaa',
                      color: 'white', fontSize: 9, fontWeight: 700,
                      padding: '1px 6px', borderRadius: 4
                    }}>
                      N{p.nova_group}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}