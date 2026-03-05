import { useState, useEffect } from 'react'
import axios from 'axios'

interface Product {
  code: string
  product_name: string
  brands: string
  categories_en: string
  ingredients_text: string
  nutriscore_grade: string
  labels_en: string
  image_url: string
  energy_100g: number
  fat_100g: number
  sugars_100g: number
  sodium_100g: number
  proteins_100g: number
  fiber_100g: number
  url: string
}

const NUTRI_COLORS: Record<string, string> = {
  a: '#1a7a3a', b: '#5aaa3a', c: '#f5c400', d: '#e07c2a', e: '#c1440e'
}

const NUTRI_LABELS: Record<string, string> = {
  a: 'Excellent nutritional quality',
  b: 'Good nutritional quality',
  c: 'Average nutritional quality',
  d: 'Poor nutritional quality',
  e: 'Bad nutritional quality'
}

export default function ProductPage({
  code,
  onBack
}: {
  code: string
  onBack: () => void
}) {
  const [product, setProduct] = useState<Product | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    const fetchProduct = async () => {
      try {
        const res = await axios.get(`http://localhost:8000/api/product/${code}`)
        setProduct(res.data)
      } catch (e) {
        console.log(e);
        setError('Product not found')
      }
      setLoading(false)
    }
    fetchProduct()
  }, [code])

  if (loading) return (
    <div style={{
      display: 'flex', alignItems: 'center',
      justifyContent: 'center', height: '100vh',
      fontFamily: 'DM Sans, sans-serif', color: '#8a8478'
    }}>
      Loading product...
    </div>
  )

  if (error || !product) return (
    <div style={{
      display: 'flex', alignItems: 'center',
      justifyContent: 'center', height: '100vh',
      fontFamily: 'DM Sans, sans-serif', color: '#c1440e'
    }}>
      {error}
    </div>
  )

  return (
    <div style={{ maxWidth: 900, margin: '0 auto', padding: '40px 24px', fontFamily: 'DM Sans, sans-serif' }}>

     
      <button
        onClick={onBack}
        style={{
          background: 'white', border: '1.5px solid #e8e4dc',
          borderRadius: 10, padding: '8px 16px',
          fontSize: 14, color: '#8a8478',
          cursor: 'pointer', marginBottom: 32,
          fontFamily: 'DM Sans, sans-serif',
          display: 'flex', alignItems: 'center', gap: 6
        }}
      >
        ← Back to search
      </button>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: 32 }}>

        
        <div>

          <div style={{
            background: 'white', border: '1.5px solid #e8e4dc',
            borderRadius: 16, padding: 24,
            display: 'flex', alignItems: 'center',
            justifyContent: 'center', marginBottom: 16,
            minHeight: 200
          }}>
            {product.image_url
              ? <img src={product.image_url} alt={product.product_name}
                  style={{ maxWidth: '100%', maxHeight: 180, objectFit: 'contain' }} />
              : <span style={{ fontSize: 64 }}>🥫</span>
            }
          </div>

          
          {product.nutriscore_grade && (
            <div style={{
              background: NUTRI_COLORS[product.nutriscore_grade],
              borderRadius: 16, padding: '16px 20px',
              color: 'white', marginBottom: 16
            }}>
              <div style={{ fontSize: 12, opacity: 0.85, marginBottom: 4 }}>NUTRI-SCORE</div>
              <div style={{ fontSize: 36, fontWeight: 700, fontFamily: 'Fraunces, serif' }}>
                {product.nutriscore_grade.toUpperCase()}
              </div>
              <div style={{ fontSize: 13, marginTop: 4, opacity: 0.9 }}>
                {NUTRI_LABELS[product.nutriscore_grade]}
              </div>
            </div>
          )}

          
          {product.labels_en && (
            <div style={{
              background: 'white', border: '1.5px solid #e8e4dc',
              borderRadius: 16, padding: '16px 20px'
            }}>
              <div style={{ fontSize: 12, color: '#8a8478', marginBottom: 8 }}>LABELS</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {product.labels_en.split(',').map((label, i) => (
                  <span key={i} style={{
                    background: '#e8f4ee', color: '#2d6a4f',
                    fontSize: 12, padding: '4px 10px',
                    borderRadius: 20, fontWeight: 500
                  }}>
                    {label.trim()}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        
        <div>
          
          <h1 style={{
            fontFamily: 'Fraunces, serif',
            fontSize: 28, fontWeight: 700,
            color: '#1a1814', marginBottom: 6
          }}>
            {product.product_name}
          </h1>
          <p style={{ color: '#8a8478', fontSize: 16, marginBottom: 8 }}>
            {product.brands}
          </p>
          {product.categories_en && (
            <p style={{ color: '#8a8478', fontSize: 13, marginBottom: 24 }}>
              {product.categories_en}
            </p>
          )}

          
          <div style={{
            background: 'white', border: '1.5px solid #e8e4dc',
            borderRadius: 16, padding: '20px 24px', marginBottom: 20
          }}>
            <div style={{
              fontSize: 13, fontWeight: 600,
              color: '#8a8478', marginBottom: 16,
              textTransform: 'uppercase', letterSpacing: 1
            }}>
              Nutrition per 100g
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              {[
                { label: 'Energy', value: product.energy_100g, unit: 'kcal' },
                { label: 'Fat', value: product.fat_100g, unit: 'g' },
                { label: 'Sugars', value: product.sugars_100g, unit: 'g' },
                { label: 'Sodium', value: product.sodium_100g, unit: 'g' },
                { label: 'Proteins', value: product.proteins_100g, unit: 'g' },
                { label: 'Fiber', value: product.fiber_100g, unit: 'g' },
              ].map((item, i) => (
                <div key={i} style={{
                  background: '#f7f5f0', borderRadius: 10,
                  padding: '12px 14px'
                }}>
                  <div style={{ fontSize: 12, color: '#8a8478', marginBottom: 4 }}>
                    {item.label}
                  </div>
                  <div style={{ fontSize: 18, fontWeight: 600, color: '#1a1814' }}>
                    {item.value != null ? `${Number(item.value).toFixed(2)}${item.unit}` : 'N/A'}
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
                fontSize: 13, fontWeight: 600,
                color: '#8a8478', marginBottom: 12,
                textTransform: 'uppercase', letterSpacing: 1
              }}>
                Ingredients
              </div>
              <p style={{ fontSize: 14, color: '#1a1814', lineHeight: 1.6 }}>
                {product.ingredients_text}
              </p>
            </div>
          )}
          {product.url && (
            <a
              href={product.url}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                display: 'inline-block',
                background: '#2d6a4f', color: 'white',
                padding: '12px 24px', borderRadius: 12,
                fontSize: 14, fontWeight: 500,
                textDecoration: 'none'
              }}
            >
              View on Open Food Facts →
            </a>
          )}
        </div>
      </div>
    </div>
  )
}