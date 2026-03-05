import { useState } from 'react'
import axios from 'axios'

interface Product {
  code: string
  product_name: string
  brands: string
  nutriscore_grade: string
  sodium_100g: number
  sugars_100g: number
  fat_100g: number
  proteins_100g: number
  image_url: string
  labels_en: string
  url: string
  score: number
}

interface SearchResult {
  explanation: string
  total: number
  results: Product[]
}

const NUTRI_COLORS: Record<string, string> = {
  a: '#1a7a3a', b: '#5aaa3a', c: '#f5c400', d: '#e07c2a', e: '#c1440e'
}

export default function SearchPage({ onProductClick }: { onProductClick: (code: string) => void }) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSearch = async () => {
    if (!query.trim()) return
    setLoading(true)
    setError('')
    try {
      const res = await axios.post('http://localhost:8000/api/search', {
        query,
        limit: 20
      })
      setResults(res.data)
    } catch (e) {
        console.log(e);
      setError('Search failed. Make sure the backend is running.')
    }
    setLoading(false)
  }

  return (
    <div style={{ maxWidth: 900, margin: '0 auto', padding: '40px 24px' }}>


      <div style={{ marginBottom: 48 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
          <div style={{
            width: 36, height: 36, borderRadius: 10,
            background: '#2d6a4f', display: 'flex',
            alignItems: 'center', justifyContent: 'center'
          }}>
            <span style={{ color: 'white', fontSize: 18 }}>🍎</span>
          </div>
          <h1 style={{
            fontFamily: 'Fraunces, serif',
            fontSize: 24, fontWeight: 700,
            color: '#1a1814'
          }}>
            Open Food Facts Canada
          </h1>
        </div>
        <p style={{ color: '#8a8478', fontSize: 15 }}>
          AI-powered food search — ask in English or French
        </p>
      </div>

      <div style={{ marginBottom: 24 }}>
        <div style={{
          display: 'flex', gap: 12,
          background: 'white',
          border: '1.5px solid #e8e4dc',
          borderRadius: 16, padding: '6px 6px 6px 20px',
          boxShadow: '0 2px 12px rgba(0,0,0,0.06)'
        }}>
          <input
            style={{
              flex: 1, border: 'none', outline: 'none',
              fontSize: 16, background: 'transparent',
              fontFamily: 'DM Sans, sans-serif', color: '#1a1814'
            }}
            placeholder='Try "healthy low sodium snacks" or "céréales bio sans gluten"'
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSearch()}
          />
          <button
            onClick={handleSearch}
            disabled={loading}
            style={{
              background: '#2d6a4f', color: 'white',
              border: 'none', borderRadius: 12,
              padding: '12px 24px', fontSize: 15,
              fontFamily: 'DM Sans, sans-serif',
              fontWeight: 500, cursor: 'pointer',
              opacity: loading ? 0.7 : 1
            }}
          >
            {loading ? 'Searching...' : 'Search'}
          </button>
        </div>

        
        <div style={{ display: 'flex', gap: 8, marginTop: 12, flexWrap: 'wrap' }}>
          {[
            'healthy low sodium snacks',
            'food for diabetics',
            'high protein yogurt',
            'céréales bio sans gluten'
          ].map(q => (
            <button
              key={q}
              onClick={() => { setQuery(q); }}
              style={{
                background: 'white', border: '1px solid #e8e4dc',
                borderRadius: 20, padding: '6px 14px',
                fontSize: 13, color: '#8a8478',
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
          color: '#c1440e', marginBottom: 24, fontSize: 14
        }}>
          {error}
        </div>
      )}

      {results && (
        <div style={{
          background: '#e8f4ee', border: '1px solid #b7dfc8',
          borderRadius: 12, padding: '12px 16px',
          marginBottom: 24, fontSize: 14, color: '#2d6a4f',
          display: 'flex', alignItems: 'center', gap: 8
        }}>
          <span>🤖</span>
          <span>{results.explanation} — <strong>{results.total} products found</strong></span>
        </div>
      )}

      
      {results && (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))',
          gap: 16
        }}>
          {results.results.map((product, i) => (
            <div
              key={i}
              onClick={() => onProductClick(product.code)}
              style={{
                background: 'white',
                border: '1.5px solid #e8e4dc',
                borderRadius: 16, padding: 16,
                cursor: 'pointer',
                transition: 'all 0.2s',
                boxShadow: '0 1px 4px rgba(0,0,0,0.04)'
              }}
              onMouseEnter={e => {
                (e.currentTarget as HTMLDivElement).style.boxShadow = '0 4px 20px rgba(0,0,0,0.1)'
                ;(e.currentTarget as HTMLDivElement).style.transform = 'translateY(-2px)'
              }}
              onMouseLeave={e => {
                (e.currentTarget as HTMLDivElement).style.boxShadow = '0 1px 4px rgba(0,0,0,0.04)'
                ;(e.currentTarget as HTMLDivElement).style.transform = 'translateY(0)'
              }}
            >

              <div style={{
                width: '100%', height: 120,
                display: 'flex', alignItems: 'center',
                justifyContent: 'center', marginBottom: 12,
                background: '#f7f5f0', borderRadius: 10
              }}>
                {product.image_url
                  ? <img src={product.image_url} alt={product.product_name}
                      style={{ maxHeight: 100, maxWidth: '100%', objectFit: 'contain' }} />
                  : <span style={{ fontSize: 40 }}>🥫</span>
                }
              </div>

              
              <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 4, color: '#1a1814' }}>
                {product.product_name || 'Unknown Product'}
              </div>
              <div style={{ fontSize: 13, color: '#8a8478', marginBottom: 10 }}>
                {product.brands || ''}
              </div>

              
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                {product.nutriscore_grade && (
                  <span style={{
                    background: NUTRI_COLORS[product.nutriscore_grade] || '#ccc',
                    color: 'white', fontSize: 11, fontWeight: 600,
                    padding: '3px 8px', borderRadius: 6
                  }}>
                    Nutri-Score {product.nutriscore_grade.toUpperCase()}
                  </span>
                )}
                {product.sodium_100g !== null && (
                  <span style={{
                    background: '#f7f5f0', color: '#8a8478',
                    fontSize: 11, padding: '3px 8px', borderRadius: 6
                  }}>
                    Na {product.sodium_100g?.toFixed(2)}g
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}