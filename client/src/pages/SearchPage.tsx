import { useState, useRef } from 'react'
import axios from 'axios'

function LoadingImage({ src, alt, style }: { src: string; alt?: string; style?: React.CSSProperties }) {
  const [loaded, setLoaded] = useState(false)
  const [error, setError] = useState(false)
  if (error) return <span style={{ fontSize: style?.maxHeight && Number(style.maxHeight) > 80 ? 40 : 36 }}>🥫</span>
  return (
    <>
      {!loaded && (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: '100%', height: '100%' }}>
          <div style={{
            width: 28, height: 28, border: '3px solid #e8e4dc', borderTop: '3px solid #c1440e',
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
  score?: number
}

interface SearchResult {
  type: string
  explanation: string
  total: number
  returned?: number
  offset?: number
  results: Product[]
}

const NUTRI_COLORS: Record<string, string> = {
  a: '#1a7a3a', b: '#5aaa3a', c: '#f5c400', d: '#e07c2a', e: '#c1440e'
}

const NOVA_COLORS: Record<number, string> = {
  1: '#1a7a3a', 2: '#5aaa3a', 3: '#e07c2a', 4: '#c1440e'
}

const COUNTRY_OPTIONS = [
  { value: '', label: 'All countries' },
  { value: 'canada', label: '🇨🇦 Canada' },
  { value: 'united-states', label: '🇺🇸 United States' },
  { value: 'united-kingdom', label: '🇬🇧 United Kingdom' },
  { value: 'india', label: '🇮🇳 India' },
]

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


  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [country, setCountry] = useState('')
  const [offset, setOffset] = useState(0)
  const [sessionContext, setSessionContext] = useState<any>({})
  const sessionId = useRef<string>(`${Math.random().toString(36).slice(2)}`)
  const LIMIT = 20

  const doSearch = async (q: string, append = false) => {
    if (!q.trim()) return
    const currentOffset = append ? offset : 0
    setLoading(true)
    setError('')
    if (!append) setResults(null)
    try {
      const res = await axios.post('http://localhost:8000/api/search', {
        query: q,
        limit: LIMIT,
        offset: currentOffset,
        country: country || undefined
      }, {
        headers: { 'x-session-id': sessionId.current }
      })
      if (append) {
        setResults(prev => prev ? {
          ...res.data,
          results: [...prev.results, ...res.data.results]
        } : res.data)
      } else {
        setResults(res.data)
      }
      setOffset(currentOffset + LIMIT)
      // Fetch session context after search
      const ctxRes = await axios.get('http://localhost:8000/api/session/context', {
        headers: { 'x-session-id': sessionId.current }
      })
      setSessionContext(ctxRes.data)
    } catch (e) {
      console.log(e)
      setError('Search failed. Make sure the backend is running.')
    }
    setLoading(false)
  }
  const updateSessionContext = async (context: any) => {
    try {
      await axios.post('http://localhost:8000/api/session/context', { context }, {
        headers: { 'x-session-id': sessionId.current }
      })
      const ctxRes = await axios.get('http://localhost:8000/api/session/context', {
        headers: { 'x-session-id': sessionId.current }
      })
      setSessionContext(ctxRes.data)
    } catch {}
  }
  // Example: add vegan filter button
  // <button onClick={() => updateSessionContext({ vegan: true })}>Only Vegan</button>

  return (
    <div style={{ maxWidth: 960, margin: '0 auto', padding: '32px 24px', fontFamily: 'DM Sans, sans-serif' }}>

      <div style={{ marginBottom: 32, display: 'flex', alignItems: 'center', gap: 16 }}>
        <img
          src="https://static.openfoodfacts.org/images/logos/off-logo-horizontal-light.svg"
          alt="Open Food Facts"
          style={{ height: 40 }}
          onError={e => { (e.target as HTMLImageElement).style.display = 'none' }}
        />
        <div>
          <h1 style={{
            fontFamily: 'Fraunces, serif',
            fontSize: 22, fontWeight: 700,
            color: '#1a1814', margin: 0
          }}>
            Food Search
          </h1>
          <p style={{ color: '#8a8478', fontSize: 13, margin: 0 }}>
            Smart Search · English & French · Nutri-Score · NOVA
          </p>
        </div>
      </div>

      <div style={{ marginBottom: 20 }}>
        <div style={{ marginBottom: 10 }}>
          <button
            onClick={() => updateSessionContext({ vegan: true })}
            style={{
              background: sessionContext?.filters?.vegan ? '#2d6a4f' : 'white',
              color: sessionContext?.filters?.vegan ? 'white' : '#2d6a4f',
              border: '1.5px solid #2d6a4f', borderRadius: 10,
              padding: '6px 16px', fontSize: 13, fontWeight: 600,
              marginRight: 8, cursor: 'pointer'
            }}
          >
            Only Vegan
          </button>
        </div>
        <div style={{
          display: 'flex', gap: 10,
          background: 'white',
          border: '1.5px solid #e8e4dc',
          borderRadius: 16, padding: '6px 6px 6px 18px',
          boxShadow: '0 2px 12px rgba(0,0,0,0.06)',
          alignItems: 'center'
        }}>
          <span style={{ fontSize: 18 }}>🔍</span>
          <input
            style={{
              flex: 1, border: 'none', outline: 'none',
              fontSize: 15, background: 'transparent',
              fontFamily: 'DM Sans, sans-serif', color: '#1a1814'
            }}
            placeholder='Try "healthy snacks", "compare coke and pepsi", or scan a barcode like "8992760221028"'
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && doSearch(query)}
          />
          <select
            value={country}
            onChange={e => setCountry(e.target.value)}
            style={{
              border: '1px solid #e8e4dc', borderRadius: 10,
              padding: '8px 10px', fontSize: 13,
              color: '#1a1814', background: '#f7f5f0',
              fontFamily: 'DM Sans, sans-serif',
              cursor: 'pointer', outline: 'none'
            }}
          >
            {COUNTRY_OPTIONS.map(c => (
              <option key={c.value} value={c.value}>{c.label}</option>
            ))}
          </select>
          <button
            onClick={() => doSearch(query)}
            disabled={loading}
            style={{
              background: '#2d6a4f', color: 'white',
              border: 'none', borderRadius: 12,
              padding: '10px 22px', fontSize: 14,
              fontFamily: 'DM Sans, sans-serif',
              fontWeight: 600, cursor: 'pointer',
              opacity: loading ? 0.7 : 1,
              whiteSpace: 'nowrap'
            }}
          >
            {loading ? 'Searching…' : 'Search'}
          </button>
        </div>

        <div style={{ display: 'flex', gap: 8, marginTop: 10, flexWrap: 'wrap' }}>
          {[
            'healthy low sodium snacks',
            'high protein yogurt',
            'compare coke and pepsi',
            '8992760221028',
            'organic vegan cereals',
            'food for diabetics',
          ].map(q => (
            <button
              key={q}
              onClick={() => { setQuery(q); doSearch(q) }}
              style={{
                background: 'white', border: '1px solid #e8e4dc',
                borderRadius: 20, padding: '5px 13px',
                fontSize: 12, color: '#8a8478',
                cursor: 'pointer', fontFamily: 'DM Sans, sans-serif'
              }}
            >
              {q}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div style={{
          background: '#fef2f2', border: '1px solid #fecaca',
          borderRadius: 12, padding: '12px 16px',
          color: '#c1440e', marginBottom: 20, fontSize: 14
        }}>
          {error}
        </div>
      )}

      {results && (
        <div style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          background: '#e8f4ee', border: '1px solid #b7dfc8',
          borderRadius: 12, padding: '10px 16px',
          marginBottom: 20, fontSize: 13, color: '#2d6a4f',
          flexWrap: 'wrap', gap: 8
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <img src="https://static.openfoodfacts.org/images/logos/off-logo-horizontal-light.svg" alt="Open Food Facts" style={{ height: 20 }} />
            <span>{results.explanation}</span>
          </div>
          <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
            {results.type && (
              <span style={{
                background: '#2d6a4f', color: 'white',
                padding: '2px 10px', borderRadius: 10,
                fontSize: 11, fontWeight: 600, textTransform: 'uppercase'
              }}>
                {results.type}
              </span>
            )}
            <strong>{results.total} found</strong>
          </div>
        </div>
      )}

      {loading && !results && (
        <div style={{ display: 'flex', justifyContent: 'center', padding: '60px 0' }}>
          <div style={{
            width: 40, height: 40, border: '4px solid #e8e4dc', borderTop: '4px solid #2d6a4f',
            borderRadius: '50%', animation: 'spin 0.8s linear infinite'
          }} />
        </div>
      )}

      {results && results.results.length > 0 && (
        <>
          {results.type === 'compare' ? (
            /* Compare layout */
            <div style={{
              display: 'grid',
              gridTemplateColumns: `repeat(${Math.min(results.results.length, 4)}, 1fr)`,
              gap: 16, marginBottom: 24
            }}>
              {results.results.map((product, i) => (
                <div key={i} onClick={() => onProductClick(product.code)} style={{
                  background: 'white', border: '1.5px solid #e8e4dc',
                  borderRadius: 16, padding: 20, cursor: 'pointer',
                  transition: 'box-shadow 0.2s, transform 0.2s',
                  boxShadow: '0 1px 4px rgba(0,0,0,0.04)'
                }}
                  onMouseEnter={e => { e.currentTarget.style.boxShadow = '0 4px 20px rgba(0,0,0,0.1)'; e.currentTarget.style.transform = 'translateY(-2px)' }}
                  onMouseLeave={e => { e.currentTarget.style.boxShadow = '0 1px 4px rgba(0,0,0,0.04)'; e.currentTarget.style.transform = 'translateY(0)' }}
                >
                  <div style={{
                    width: '100%', height: 100, display: 'flex',
                    alignItems: 'center', justifyContent: 'center',
                    background: '#f7f5f0', borderRadius: 10, marginBottom: 12
                  }}>
                    {product.image_url
                      ? <LoadingImage src={product.image_url} style={{ maxHeight: 80, maxWidth: '100%', objectFit: 'contain' }} />
                      : <span style={{ fontSize: 36 }}>🥫</span>}
                  </div>
                  <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 4 }}>{product.product_name || 'Unknown'}</div>
                  <div style={{ fontSize: 12, color: '#8a8478', marginBottom: 12 }}>{product.brands}</div>
                  {[
                    { label: 'Calories', val: product.nutrition?.energy_kcal, unit: 'kcal' },
                    { label: 'Fat', val: product.nutrition?.fat, unit: 'g' },
                    { label: 'Sugars', val: product.nutrition?.sugars, unit: 'g' },
                    { label: 'Protein', val: product.nutrition?.proteins, unit: 'g' },
                    { label: 'Sodium', val: product.nutrition?.sodium, unit: 'g' },
                  ].map((item, j) => (
                    <div key={j} style={{
                      display: 'flex', justifyContent: 'space-between',
                      padding: '5px 0', borderBottom: '1px solid #f0ede8', fontSize: 12
                    }}>
                      <span style={{ color: '#8a8478' }}>{item.label}</span>
                      <span style={{ fontWeight: 600 }}>
                        {item.val != null ? `${Number(item.val).toFixed(1)}${item.unit}` : '—'}
                      </span>
                    </div>
                  ))}
                  <div style={{ display: 'flex', gap: 4, marginTop: 10, flexWrap: 'wrap' }}>
                    {product.nutriscore_grade && product.nutriscore_grade !== 'unknown' && (
                      <span style={{
                        background: NUTRI_COLORS[product.nutriscore_grade] || '#aaa',
                        color: 'white', fontSize: 10, fontWeight: 700,
                        padding: '2px 7px', borderRadius: 4
                      }}>
                        {product.nutriscore_grade.toUpperCase()}
                      </span>
                    )}
                    {product.nova_group != null && (
                      <span style={{
                        background: NOVA_COLORS[product.nova_group] || '#aaa',
                        color: 'white', fontSize: 10, fontWeight: 700,
                        padding: '2px 7px', borderRadius: 4
                      }}>
                        NOVA {product.nova_group}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            /* Normal search grid */
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
              gap: 16, marginBottom: 24
            }}>
              {results.results.map((product, i) => (
                <div key={i} onClick={() => onProductClick(product.code)} style={{
                  background: 'white', border: '1.5px solid #e8e4dc',
                  borderRadius: 16, padding: 16, cursor: 'pointer',
                  transition: 'box-shadow 0.2s, transform 0.2s',
                  boxShadow: '0 1px 4px rgba(0,0,0,0.04)',
                  display: 'flex', flexDirection: 'column' as const
                }}
                  onMouseEnter={e => { e.currentTarget.style.boxShadow = '0 4px 20px rgba(0,0,0,0.1)'; e.currentTarget.style.transform = 'translateY(-2px)' }}
                  onMouseLeave={e => { e.currentTarget.style.boxShadow = '0 1px 4px rgba(0,0,0,0.04)'; e.currentTarget.style.transform = 'translateY(0)' }}
                >
                  <div style={{
                    width: '100%', height: 120,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    background: '#f7f5f0', borderRadius: 10, marginBottom: 12
                  }}>
                    {product.image_url
                      ? <LoadingImage src={product.image_url} style={{ maxHeight: 100, maxWidth: '100%', objectFit: 'contain' }} />
                      : <span style={{ fontSize: 40 }}>🥫</span>}
                  </div>

                  <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 2, color: '#1a1814', lineHeight: 1.3 }}>
                    {product.product_name || 'Unknown Product'}
                  </div>
                  <div style={{ fontSize: 12, color: '#8a8478', marginBottom: 8 }}>
                    {product.brands || ''}
                    {product.primary_country && (
                      <span style={{ marginLeft: 6, fontSize: 11 }}>· {product.primary_country}</span>
                    )}
                  </div>

                  <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap', marginBottom: 10 }}>
                    {product.nutriscore_grade && product.nutriscore_grade !== 'unknown' && (
                      <span style={{
                        background: NUTRI_COLORS[product.nutriscore_grade] || '#aaa',
                        color: 'white', fontSize: 10, fontWeight: 700,
                        padding: '2px 8px', borderRadius: 5
                      }}>
                        Nutri-Score {product.nutriscore_grade.toUpperCase()}
                      </span>
                    )}
                    {product.nova_group != null && (
                      <span style={{
                        background: NOVA_COLORS[product.nova_group] || '#aaa',
                        color: 'white', fontSize: 10, fontWeight: 700,
                        padding: '2px 8px', borderRadius: 5
                      }}>
                        NOVA {product.nova_group}
                      </span>
                    )}
                    {product.ecoscore_grade && product.ecoscore_grade !== 'unknown' && (
                      <span style={{
                        background: '#f7f5f0', color: '#8a8478',
                        fontSize: 10, fontWeight: 600,
                        padding: '2px 8px', borderRadius: 5,
                        border: '1px solid #e8e4dc'
                      }}>
                        Eco {product.ecoscore_grade.toUpperCase()}
                      </span>
                    )}
                  </div>

                  <div style={{
                    display: 'flex', gap: 8, marginTop: 'auto',
                    paddingTop: 8, borderTop: '1px solid #f0ede8'
                  }}>
                    {product.nutrition?.energy_kcal != null && (
                      <span style={{ fontSize: 11, color: '#8a8478' }}>
                        {Math.round(product.nutrition.energy_kcal)} kcal
                      </span>
                    )}
                    {product.nutrition?.proteins != null && (
                      <span style={{ fontSize: 11, color: '#8a8478' }}>
                        P {Number(product.nutrition.proteins).toFixed(1)}g
                      </span>
                    )}
                    {product.nutrition?.sodium != null && (
                      <span style={{ fontSize: 11, color: '#8a8478' }}>
                        Na {Number(product.nutrition.sodium).toFixed(3)}g
                      </span>
                    )}
                  </div>

                  {product.labels_tags && parseTags(product.labels_tags).length > 0 && (
                    <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginTop: 8 }}>
                      {parseTags(product.labels_tags).slice(0, 3).map((label, j) => (
                        <span key={j} style={{
                          background: '#f0f7f3', color: '#2d6a4f',
                          fontSize: 10, padding: '1px 6px', borderRadius: 4
                        }}>
                          {label}
                        </span>
                      ))}
                      {parseTags(product.labels_tags).length > 3 && (
                        <span style={{ fontSize: 10, color: '#8a8478' }}>
                          +{parseTags(product.labels_tags).length - 3}
                        </span>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {results.type === 'search' && results.results.length < results.total && (
            <div style={{ textAlign: 'center', marginBottom: 32 }}>
              <button
                onClick={() => doSearch(query, true)}
                disabled={loading}
                style={{
                  background: 'white', border: '1.5px solid #2d6a4f',
                  borderRadius: 12, padding: '10px 32px',
                  fontSize: 14, color: '#2d6a4f',
                  cursor: 'pointer', fontFamily: 'DM Sans, sans-serif',
                  fontWeight: 600
                }}
              >
                {loading ? 'Loading…' : `Load More (${results.results.length} of ${results.total})`}
              </button>
            </div>
          )}
        </>
      )}

      {results && results.results.length === 0 && (
        <div style={{
          textAlign: 'center', padding: '48px 0',
          color: '#8a8478', fontSize: 15
        }}>
          <div style={{ fontSize: 48, marginBottom: 12 }}>🔍</div>
          <div>No products found. Try a different search query.</div>
        </div>
      )}
    </div>
  )
}